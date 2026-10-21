"""Editor diagnostics preserve the difference between errors and advice."""
from pathlib import Path
import io
import json
import tempfile
import unittest

from zensigil.language_tools import LanguageService
from zensigil.lsp import (Server, diagnostic_message, read_message, write_message,
                          MAX_DIAGNOSTICS, MAX_DIAGNOSTIC_MESSAGE_BYTES, MAX_MESSAGE_BYTES)


class AdvisoryEditorTests(unittest.TestCase):
    def test_known_type_conflict_is_advice(self):
        service = LanguageService()
        uri = 'untitled:typed.zs'
        service.open(uri, 'let count: integer = "three"\nemit count\n', 1)
        items = service.diagnostics(uri)[uri]
        self.assertEqual([(item['code'], item['severity']) for item in items], [('W_TYPE', 2)])
        self.assertIn('integer', items[0]['message'])

    def test_unused_binding_is_an_advisory_diagnostic(self):
        service = LanguageService()
        uri = 'untitled:review.zs'
        service.open(uri, 'let unused = 2\nemit "🌱"\n', 1)
        items = service.diagnostics(uri)[uri]
        self.assertEqual([(item['code'], item['severity']) for item in items], [('W_UNUSED', 2)])
        self.assertEqual(items[0]['range']['start'], {'line': 0, 'character': 4})

    def test_invalid_source_stays_an_error_and_is_not_linted(self):
        service = LanguageService()
        uri = 'untitled:broken.zs'
        service.open(uri, 'let unused = 2\nfn fail():\n    return missing\n', 1)
        items = service.diagnostics(uri)[uri]
        self.assertTrue(items)
        self.assertEqual({item['severity'] for item in items}, {1})
        self.assertNotIn('W_UNUSED', [item['code'] for item in items])

    def test_imported_advice_keeps_its_source_uri(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            uri, library = (root / 'main.zs').as_uri(), (root / 'math.zs').as_uri()
            service = LanguageService([root.as_uri()])
            service.open(uri, 'use "math.zs" as math\nemit math.answer()\n', 1)
            service.open(library, 'export fn answer():\n    let unused = 2\n    return 42\n', 1)
            diagnostics = service.diagnostics(uri)
            self.assertEqual(diagnostics[uri], [])
            self.assertEqual([(item['code'], item['severity']) for item in diagnostics[library]], [('W_UNUSED', 2)])
            self.assertEqual(diagnostics[library][0]['range']['start'], {'line': 1, 'character': 8})

    def test_server_publishes_and_clears_versioned_advice(self):
        sent = []
        server = Server(sent.append)
        server.handle({'jsonrpc': '2.0', 'id': 1, 'method': 'initialize', 'params': {}})
        uri = 'untitled:review.zs'
        server.handle({'jsonrpc': '2.0', 'method': 'textDocument/didOpen', 'params': {
            'textDocument': {'uri': uri, 'version': 1, 'text': 'let unused = 2\n'}}})
        self.assertEqual(sent[-1]['params']['version'], 1)
        self.assertEqual(sent[-1]['params']['diagnostics'][0]['severity'], 2)
        server.handle({'jsonrpc': '2.0', 'method': 'textDocument/didChange', 'params': {
            'textDocument': {'uri': uri, 'version': 2},
            'contentChanges': [{'text': 'let value = 2\nemit value\n'}]}})
        self.assertEqual(sent[-1]['params']['version'], 2)
        self.assertEqual(sent[-1]['params']['diagnostics'], [])

    def test_advice_never_requires_execution(self):
        service = LanguageService()
        uri = 'untitled:loop.zs'
        service.open(uri, 'var count = 0\nwhile true:\n    set count = count + 1\n', 1)
        self.assertEqual(service.diagnostics(uri)[uri], [])


class DiagnosticPublicationTests(unittest.TestCase):
    def diagnostic(self, message, severity=2):
        return {'range': {'start': {'line': 1, 'character': 3}, 'end': {'line': 1, 'character': 4}},
                'severity': severity, 'source': 'ZenSigil',
                'code': 'E_NAME' if severity == 1 else 'W_UNUSED', 'message': message}

    def framed(self, message):
        stream = io.BytesIO()
        write_message(stream, message)
        stream.seek(0)
        body = read_message(stream)
        self.assertLessEqual(len(body), MAX_DIAGNOSTIC_MESSAGE_BYTES)
        self.assertLess(len(body), MAX_MESSAGE_BYTES)
        return json.loads(body)

    def test_small_diagnostics_keep_their_order_and_version(self):
        params = {'uri': 'untitled:test.zs', 'version': 7,
                  'diagnostics': [self.diagnostic('Advice'), self.diagnostic('Error', 1)]}
        self.assertEqual(self.framed(diagnostic_message(params))['params'], params)

    def test_count_limit_keeps_errors_first_and_reports_omissions(self):
        items = [self.diagnostic('Warning ' + str(index)) for index in range(MAX_DIAGNOSTICS + 10)]
        error = self.diagnostic('An important binding error.', 1)
        params = {'uri': 'untitled:test.zs', 'version': 7, 'diagnostics': items + [error]}
        shown = self.framed(diagnostic_message(params))['params']['diagnostics']
        self.assertEqual(len(shown), MAX_DIAGNOSTICS)
        self.assertEqual(shown[0], error)
        self.assertEqual(shown[-1]['code'], 'W_EDITOR_LIMIT')
        self.assertIn('omitted', shown[-1]['message'])
        self.assertEqual(len(params['diagnostics']), MAX_DIAGNOSTICS + 11)

    def test_byte_limit_uses_escaped_unicode_and_keeps_an_omitted_error_visible(self):
        params = {'uri': 'untitled:' + '🌱' * 100, 'version': 7,
                  'diagnostics': [self.diagnostic('🌱' * 100000, 1), self.diagnostic('Short advice')]}
        shown = self.framed(diagnostic_message(params))['params']['diagnostics']
        self.assertEqual(shown[0]['message'], 'Short advice')
        self.assertEqual(shown[-1]['code'], 'E_EDITOR_LIMIT')
        self.assertEqual(shown[-1]['severity'], 1)

    def test_large_valid_source_does_not_disconnect_the_editor(self):
        # This source produced a 1,090,968-byte frame before publication bounds.
        source = 'let a=0\nlet b=0\nlet c=0\n' + (
            'when true:\n    let a=0\n    let b=0\n    let c=0\n' * 900)
        self.assertLess(len(source.encode()), 65536)
        sent = []
        server = Server(sent.append)
        server.handle({'jsonrpc': '2.0', 'id': 1, 'method': 'initialize', 'params': {}})
        server.handle({'jsonrpc': '2.0', 'method': 'textDocument/didOpen', 'params': {
            'textDocument': {'uri': 'untitled:large.zs', 'version': 1, 'text': source}}})
        shown = self.framed(sent[-1])['params']['diagnostics']
        self.assertEqual(len(shown), MAX_DIAGNOSTICS)
        self.assertEqual(shown[-1]['code'], 'W_EDITOR_LIMIT')
        self.assertFalse(any(item['severity'] == 1 for item in shown))


if __name__ == '__main__':
    unittest.main()
