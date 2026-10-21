import http.client
import json
from pathlib import Path
import subprocess
import sys
import threading
import unittest
from http.server import ThreadingHTTPServer
from zensigil.server import Handler

ROOT = Path(__file__).resolve().parents[1]


class QuietHandler(Handler):
    def log_message(self, *args):
        pass


class CLITests(unittest.TestCase):
    def cli(self, *args):
        return subprocess.run([sys.executable, '-m', 'zensigil', *args], cwd=ROOT,
                              capture_output=True, text=True)

    def test_run_and_json(self):
        result = self.cli('run', 'examples/restock.zs', '--data', 'examples/restock.json', '--json')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)['proposals'][0]['fields']['quantity'], 105)

    def test_failure_exit_and_no_traceback(self):
        result = self.cli('run', 'examples/error.zs', '--data', 'examples/error.json')
        self.assertEqual(result.returncode, 1)
        self.assertIn('E_FIELD', result.stderr)
        self.assertIn('No proposals', result.stderr)
        self.assertNotIn('Traceback', result.stderr)

    def test_missing_file(self):
        result = self.cli('run', 'does-not-exist.zs', '--json')
        self.assertEqual(result.returncode, 1)
        self.assertEqual(json.loads(result.stdout)['diagnostics'][0]['code'], 'E_INPUT')

    def test_check_without_data_is_explicit(self):
        result = self.cli('check', 'examples/restock.zs')
        self.assertEqual(result.returncode, 0)
        self.assertIn('Input names were not verified', result.stdout)


class HTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), QuietHandler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.port = cls.server.server_port

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=3)

    def request(self, method='GET', path='/', body=None, headers=None):
        connection = http.client.HTTPConnection('127.0.0.1', self.port, timeout=5)
        connection.request(method, path, body=body, headers=headers or {})
        response = connection.getresponse()
        result = (response.status, response.read(), dict(response.getheaders()))
        connection.close()
        return result

    def post(self, body, extra=None):
        return self.request('POST', '/api/run', json.dumps(body), dict({'Content-Type': 'application/json'}, **(extra or {})))

    def test_built_ui_is_served(self):
        status, body, headers = self.request()
        self.assertEqual(status, 200)
        self.assertIn(b'ZenSigil', body)
        self.assertIn("frame-ancestors 'none'", headers['Content-Security-Policy'])
        self.assertEqual(headers['Cache-Control'], 'no-store')

    def test_examples_are_complete(self):
        status, raw, _ = self.request(path='/api/examples')
        self.assertEqual(status, 200)
        self.assertEqual(len(json.loads(raw)), 23)

    def test_same_origin_preview(self):
        status, raw, _ = self.post({'source': 'say "hello"', 'data': {}}, {'Origin': f'http://127.0.0.1:{self.port}'})
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(raw)['notes'][0]['message'], 'hello')

    def test_text_data_and_duplicates(self):
        status, raw, _ = self.post({'source': 'say text(stock)', 'data_text': '{"stock":42}'})
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(raw)['notes'][0]['message'], '42')
        for data in ('{"stock":42,"stock":43}', '{},"extra":1', 'null', '[]', '{'):
            with self.subTest(data=data):
                status, raw, _ = self.post({'source': 'say "hello"', 'data_text': data})
                self.assertEqual(status, 400, raw)

    def test_invalid_envelope(self):
        for body in ({}, {'source': 3, 'data': {}}, {'source': '', 'data': None},
                     {'source': '', 'data': {}, 'data_text': '{}'}):
            with self.subTest(body=body):
                self.assertEqual(self.post(body)[0], 400)

    def test_external_origin_and_host_rejected(self):
        self.assertEqual(self.post({'source': '', 'data': {}}, {'Origin': 'https://example.test'})[0], 403)
        self.assertEqual(self.request(headers={'Host': 'example.test'})[0], 403)

    def test_no_arbitrary_files(self):
        self.assertEqual(self.request(path='/../docs/language.md')[0], 404)
        self.assertEqual(self.request(path='/%2e%2e/pyproject.toml')[0], 404)
        self.assertEqual(self.request(path='/%00')[0], 400)

    def test_input_size_type_and_content_type(self):
        self.assertEqual(self.request('POST', '/api/run', '{}')[0], 415)
        self.assertEqual(self.request('POST', '/api/run', '', {'Content-Type': 'application/json', 'Content-Length': '2097153'})[0], 413)
        self.assertEqual(self.post({'source': '#'*65537, 'data': {}})[0], 200)
        self.assertFalse(json.loads(self.post({'source': '#'*65537, 'data': {}})[1])['ok'])

    def test_language_error_discards_proposals(self):
        status, raw, _ = self.post({'source': 'propose x(a: 1)\nlet x = 1 / 0', 'data': {}})
        body = json.loads(raw)
        self.assertEqual(status, 200)
        self.assertFalse(body['ok'])
        self.assertEqual(body['proposals'], [])


if __name__ == '__main__':
    unittest.main()
