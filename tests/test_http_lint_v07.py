"""The browser warning path checks source without executing it."""
import http.client
import json
import threading
import unittest
from http.server import ThreadingHTTPServer

from zensigil.server import Handler


class Quiet(Handler):
    def log_message(self, *args):
        pass


class HTTPLintTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), Quiet)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=3)

    def post(self, source, **extra):
        body = dict(source=source, data={}, **extra)
        connection = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=5)
        connection.request('POST', '/api/lint', json.dumps(body), {'Content-Type': 'application/json'})
        response = connection.getresponse()
        result = json.loads(response.read())
        connection.close()
        self.assertEqual(response.status, 200, result)
        self.assertEqual(result['mode'], 'lint')
        return result

    def test_warning_is_advisory_and_no_effects_execute(self):
        result = self.post('let spare = 7\nsay "Do not execute"\nwhile true:\n    continue\n')
        self.assertTrue(result['ok'], result)
        self.assertIn('W_UNUSED', [w['code'] for w in result['warnings']])
        for key in ('proposals', 'notes', 'values'):
            self.assertFalse(result.get(key), result)

    def test_invalid_source_remains_an_error(self):
        result = self.post('emit [1,\n')
        self.assertFalse(result['ok'])
        self.assertTrue(result['diagnostics'])
        self.assertEqual(result['warnings'], [])

    def test_warning_points_to_module_source(self):
        result = self.post('use "lib/count.zs" as count\nemit count.value()\n', modules={
            'lib/count.zs': 'export fn value():\n    let spare = 3\n    return 2\n'})
        warning = next(w for w in result['warnings'] if w['code'] == 'W_UNUSED')
        self.assertEqual(warning['source_name'], 'lib/count.zs')
        self.assertEqual(warning['line'], 2)
        self.assertEqual(warning['source_line'], '    let spare = 3')

    def test_invalid_contract_has_lint_shape(self):
        result = self.post('emit 1\n', contract_text='{')
        self.assertFalse(result['ok'])
        self.assertEqual(result['diagnostics'][0]['code'], 'E_CONTRACT')
        self.assertEqual(result['warnings'], [])


if __name__ == '__main__':
    unittest.main()
