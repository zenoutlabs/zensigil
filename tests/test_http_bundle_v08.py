"""Browser test requests execute the same explicit bundle that the CLI receives."""
import http.client
import json
import threading
import unittest
from http.server import ThreadingHTTPServer

from zensigil.server import Handler


class Quiet(Handler):
    def log_message(self, *args):
        pass


class HTTPBundleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), Quiet)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown(); cls.server.server_close(); cls.thread.join(timeout=3)

    def post(self, route='/api/test', **extra):
        payload = dict(source='say "Main must not execute during tests"\n', **extra)
        connection = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=10)
        connection.request('POST', route, json.dumps(payload), {'Content-Type': 'application/json'})
        response = connection.getresponse()
        result = json.loads(response.read()); connection.close()
        self.assertEqual(response.status, 200, result)
        return result

    def test_separate_sources_and_shared_import_tests_execute_once(self):
        modules = {'lib/math.zs': 'export fn double(n):\n    return n * 2\ntest "Library":\n    require double(2) == 4, "Expected four"\n'}
        tests = {f'tests/{name}.zs': 'use "lib/math.zs" as math\ntest "Separate":\n    require math.double(3) == 6, "Expected six"\n' for name in ('one', 'two')}
        result = self.post(modules=modules, tests=tests)
        self.assertTrue(result['ok'], result)
        self.assertEqual((result['total'], result['passed']), (3, 3))
        self.assertEqual({case['source_name'] for case in result['tests']}, {'lib/math.zs', 'tests/one.zs', 'tests/two.zs'})
        self.assertEqual(result['notes'], [])

    def test_failing_separate_test_has_its_own_source_location(self):
        result = self.post(tests={'tests/bad.zs': 'test "Fail":\n    require false, "Fix this test"\n'})
        self.assertFalse(result['ok'])
        error = result['diagnostics'][0]
        self.assertEqual((error['source_name'], error['line']), ('tests/bad.zs', 2))
        self.assertEqual(error['source_line'], '    require false, "Fix this test"')
        self.assertEqual((result['total'], result['failed']), (1, 1))

    def test_invalid_test_map_returns_structured_error(self):
        for tests in (None, [], {'../outside.zs': ''}, {'a.zs': 42}):
            result = self.post(tests=tests)
            self.assertFalse(result['ok'])
            self.assertEqual(result['mode'], 'test')
            self.assertTrue(result['diagnostics'])
            self.assertEqual(result['total'], 0)

    def test_all_sources_checked_before_any_test_run(self):
        result = self.post(tests={'tests/one.zs': 'test "One":\n    require true, "ok"\n',
                                  'tests/two.zs': 'test "Broken":\n    require ('})
        self.assertFalse(result['ok'])
        self.assertEqual(result['tests'], [])
        self.assertEqual(result['diagnostics'][0]['source_name'], 'tests/two.zs')

    def test_run_preview_does_not_execute_separate_test_sources(self):
        result = self.post('/api/run', data={}, tests={'tests/unfinished.zs': 'test "Later":\n    require ('})
        self.assertTrue(result['ok'], result)
        self.assertEqual([n['message'] for n in result['notes']], ['Main must not execute during tests'])


if __name__ == '__main__':
    unittest.main()
