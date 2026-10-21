"""Behavioral editor/transport contracts; no editor process or network required."""
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from zensigil.language_tools import LanguageService, end_position, file_path, utf16
from zensigil.lsp import FramingError, Server, main, read_message, write_message

ROOT = Path(__file__).resolve().parents[1]


def frame(message):
    stream = io.BytesIO()
    write_message(stream, message)
    return stream.getvalue()


def request(method, identity=1, **params):
    return dict(jsonrpc='2.0', id=identity, method=method, params=params)


def notice(method, **params):
    return dict(jsonrpc='2.0', method=method, params=params)


def decode_frames(raw):
    stream, messages = io.BytesIO(raw), []
    while True:
        body = read_message(stream)
        if body is None:
            return messages
        messages.append(json.loads(body))


class ProtocolTests(unittest.TestCase):
    def setUp(self):
        self.sent, self.logs = [], []
        self.server = Server(self.sent.append, self.logs.append)

    def initialize(self):
        self.server.handle(request('initialize', workspaceFolders=[]))
        self.assertEqual(self.sent[-1]['result']['capabilities']['positionEncoding'], 'utf-16')

    def test_lifecycle_and_request_errors(self):
        self.server.handle(request('textDocument/hover'))
        self.assertEqual(self.sent[-1]['error']['code'], -32002)
        self.initialize()
        self.server.handle(request('initialize', identity=2))
        self.assertEqual(self.sent[-1]['error']['code'], -32600)
        self.server.handle(request('unknown/request', identity=3))
        self.assertEqual(self.sent[-1]['error']['code'], -32601)
        self.server.handle(request('textDocument/hover', identity=4, textDocument=[]))
        self.assertEqual(self.sent[-1]['error']['code'], -32602)
        self.server.handle(request('shutdown', identity=5))
        self.assertIsNone(self.sent[-1]['result'])
        self.server.handle(request('textDocument/hover', identity=6))
        self.assertEqual(self.sent[-1]['error']['code'], -32600)
        self.server.handle(notice('exit'))
        self.assertTrue(self.server.exited)

    def test_full_text_versions_and_close_clear_diagnostics(self):
        self.initialize()
        uri = 'untitled:version-test'
        self.server.handle(notice('textDocument/didOpen', textDocument={'uri': uri, 'version': 2, 'text': 'when true\n'}))
        self.assertTrue(self.sent[-1]['params']['diagnostics'])
        self.server.handle(notice('textDocument/didChange', textDocument={'uri': uri, 'version': 3}, contentChanges=[{'text': 'emit 1\n'}]))
        self.assertEqual(self.sent[-1]['params']['diagnostics'], [])
        count = len(self.sent)
        self.server.handle(notice('textDocument/didChange', textDocument={'uri': uri, 'version': 2}, contentChanges=[{'text': 'bad\n'}]))
        self.assertEqual(len(self.sent), count)
        self.assertEqual(self.server.service.documents[uri].source, 'emit 1\n')
        self.server.handle(notice('textDocument/didChange', textDocument={'uri': uri, 'version': 4}, contentChanges=[{'range': {}, 'text': 'bad'}]))
        self.assertTrue(self.logs)
        self.assertEqual(self.server.service.documents[uri].version, 3)
        self.server.handle(notice('textDocument/didClose', textDocument={'uri': uri}))
        self.assertEqual(self.sent[-1]['params']['diagnostics'], [])
        self.assertNotIn(uri, self.server.service.documents)

    def test_utf8_frame_roundtrip_and_invalid_frames_terminate(self):
        message = request('initialize', text='🌱')
        self.assertEqual(json.loads(read_message(io.BytesIO(frame(message)))), message)
        self.assertIsNone(read_message(io.BytesIO()))
        malformed = [b'Content-Length: -1\r\n\r\n', b'Content-Length: 1048577\r\n\r\n',
                     b'Content-Length: 2\r\nContent-Length: 2\r\n\r\n{}',
                     b'Content-Length: 2\n\n{}', b'Content-Length: 4\r\n\r\n{}',
                     b'Content-Type: application/json; charset=latin1\r\nContent-Length: 2\r\n\r\n{}',
                     b'x' * 8200, b'Content-Length: 2\r\n']
        for raw in malformed:
            with self.subTest(raw=raw[:60]), self.assertRaises(FramingError):
                read_message(io.BytesIO(raw))

    def test_stdio_real_subprocess_has_only_framed_stdout(self):
        messages = [request('initialize'), notice('textDocument/didOpen', textDocument={'uri': 'untitled:real', 'version': 1,
                     'text': 'while true:\n    continue\nemit 1 / 0\n'}),
                    request('textDocument/completion', 2, textDocument={'uri': 'untitled:real'}, position={'line': 2, 'character': 0}),
                    request('shutdown', 3), notice('exit')]
        result = subprocess.run([sys.executable, '-m', 'zensigil.lsp'], input=b''.join(frame(item) for item in messages),
                                cwd=ROOT, capture_output=True, timeout=5)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, b'')
        output = decode_frames(result.stdout)
        self.assertEqual(output[1]['params']['diagnostics'], [])  # Program was checked, never executed.
        self.assertIn('map', [item['label'] for item in output[2]['result']])

    def test_bad_json_recovers_and_bad_framing_logs_only_stderr(self):
        out, err = io.BytesIO(), io.StringIO()
        raw = b'Content-Length: 1\r\n\r\n{' + frame(request('initialize')) + frame(request('shutdown', 2)) + frame(notice('exit'))
        self.assertEqual(main(io.BytesIO(raw), out, err), 0)
        self.assertEqual(decode_frames(out.getvalue())[0]['error']['code'], -32700)
        self.assertEqual(err.getvalue(), '')
        out, err = io.BytesIO(), io.StringIO()
        self.assertEqual(main(io.BytesIO(b'Content-Length: 999999999\r\n\r\n'), out, err), 1)
        self.assertEqual(out.getvalue(), b'')
        self.assertIn('Content-Length', err.getvalue())
        self.assertNotIn('Traceback', err.getvalue())

    def test_invalid_initialize_uri_and_malformed_notifications_are_bounded(self):
        self.server.handle(request('initialize', workspaceFolders=[{'uri': 'file://['}, {'uri': 'https://example.com'}]))
        self.assertEqual(self.server.service.roots, ())
        for message in [[], {'id': 1}, request('textDocument/hover', textDocument={'uri': 7}),
                        notice('textDocument/didOpen', textDocument={'uri': 'untitled:x', 'version': True, 'text': ''})]:
            self.server.handle(message)
        self.assertFalse(self.server.service.documents)


class LanguageServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name).resolve()
        self.service = LanguageService([self.root.as_uri()])
        self.uri = (self.root / 'main.zs').as_uri()

    def tearDown(self):
        self.temp.cleanup()

    def source(self, source):
        self.service.open(self.uri, source, 1)

    def test_definition_hover_and_completion_respect_shadowing_and_pure_scope(self):
        self.source('let outer = 1\nfn double(x: number) -> number:\n    let local = x\n    return local * 2\nwhen true:\n    let outer = 4\n    emit outer\nemit outer\nemit double(2)\n')
        local = self.service.definition(self.uri, {'line': 3, 'character': 12})
        self.assertEqual(local['range']['start'], {'line': 2, 'character': 8})
        inner = self.service.definition(self.uri, {'line': 6, 'character': 11})
        outer = self.service.definition(self.uri, {'line': 7, 'character': 8})
        self.assertEqual((inner['range']['start']['line'], outer['range']['start']['line']), (5, 0))
        hover = self.service.hover(self.uri, {'line': 8, 'character': 8})
        self.assertEqual(hover['contents']['value'], 'fn double(x: number) -> number')
        labels = {item['label'] for item in self.service.completion(self.uri, {'line': 3, 'character': 12})}
        self.assertTrue({'x', 'local', 'double', 'map', 'while'} <= labels)
        self.assertNotIn('outer', labels)
        symbols = self.service.symbols(self.uri)
        self.assertEqual(next(s for s in symbols if s['name'] == 'local')['containerName'], 'double')

    def test_lambda_references_capture_local_and_parameter_annotations(self):
        self.source('let offset = 2\nlet shift = fn(value: number) -> number => value + offset\nemit shift(3)\n')
        self.assertFalse(self.service.diagnostics(self.uri)[self.uri])
        captured = self.service.definition(self.uri, {'line': 1, 'character': 51})
        parameter = self.service.definition(self.uri, {'line': 1, 'character': 43})
        self.assertEqual(captured['range']['start']['line'], 0)
        self.assertEqual(parameter['range']['start'], {'line': 1, 'character': 15})

    def test_utf16_positions_after_emoji_and_full_document_formatting(self):
        source = 'let item=3\nemit ["🌱",item]'
        self.source(source)
        location = self.service.definition(self.uri, {'line': 1, 'character': 13})
        self.assertEqual(location['range']['start'], {'line': 0, 'character': 4})
        edits = self.service.formatting(self.uri)
        self.assertEqual(edits[0]['range']['end'], {'line': 1, 'character': 16})
        self.assertEqual(edits[0]['newText'], 'let item = 3\nemit ["🌱", item]\n')
        self.assertEqual(utf16('🌱'), 2)
        self.assertEqual(end_position('🌱\n'), {'line': 1, 'character': 0})

    def test_explicit_module_definitions_diagnostics_and_unsaved_overlay(self):
        lib = self.root / 'lib'
        lib.mkdir()
        module = lib / 'math.zs'
        module.write_text('fn double(x):\n    return x * 2\n')
        self.source('use "lib/math.zs"\nemit double(3)\n')
        self.assertEqual(self.service.diagnostics(self.uri)[self.uri], [])
        definition = self.service.definition(self.uri, {'line': 1, 'character': 7})
        self.assertEqual(definition['uri'], module.as_uri())
        self.service.open(module.as_uri(), 'fn double(x):\n    return missing\n', 8)
        diagnostics = self.service.diagnostics(self.uri)
        self.assertEqual(diagnostics[module.as_uri()][0]['code'], 'E_NAME')
        self.assertEqual(diagnostics[module.as_uri()][0]['range']['start']['line'], 1)
        self.service.change(module.as_uri(), 'fn double(x):\n    return x + x\n', 9)
        self.assertEqual(self.service.diagnostics(self.uri)[self.uri], [])
        self.assertIn('x * 2', module.read_text())  # Overlay never writes files.

    def test_overlay_can_supply_unsaved_new_module_and_closing_restores_disk(self):
        module = self.root / 'new.zs'
        self.source('use "new.zs"\nemit helper()\n')
        self.service.open(module.as_uri(), 'fn helper():\n    return 1\n', 1)
        self.assertEqual(self.service.diagnostics(self.uri)[self.uri], [])
        self.service.close(module.as_uri())
        self.assertEqual(self.service.diagnostics(self.uri)[self.uri][0]['code'], 'E_IMPORT')

    def test_no_workspace_no_implicit_reads_and_symlink_escape_rejected(self):
        external = self.root.parent / (self.root.name + '-external.zs')
        try:
            external.write_text('fn secret():\n    return 1\n')
            (self.root / 'escape.zs').symlink_to(external)
            self.source('use "escape.zs"\nemit secret()\n')
            with patch('pathlib.Path.open', side_effect=AssertionError('Read escaped file')):
                self.assertEqual(self.service.diagnostics(self.uri)[self.uri][0]['code'], 'E_IMPORT')
            service = LanguageService()
            service.open(self.uri, 'use "escape.zs"\n', 1)
            with patch('pathlib.Path.open', side_effect=AssertionError('Undeclared workspace read')):
                self.assertEqual(service.diagnostics(self.uri)[self.uri][0]['code'], 'E_IMPORT')
        finally:
            external.unlink(missing_ok=True)
        for uri in ['https://example.com/a.zs', 'file://remote/a.zs', 'file:///a.zs?query', 'file:///a%00.zs']:
            self.assertIsNone(file_path(uri))

    def test_cycles_path_traversal_and_only_reachable_imports(self):
        (self.root / 'a.zs').write_text('use "b.zs"\n')
        (self.root / 'b.zs').write_text('use "a.zs"\n')
        self.source('use "a.zs"\n')
        found = self.service.diagnostics(self.uri)
        self.assertTrue(any(item['code'] == 'E_IMPORT' for items in found.values() for item in items))
        self.service.change(self.uri, 'use "../outside.zs"\n', 2)
        self.assertEqual(self.service.diagnostics(self.uri)[self.uri][0]['code'], 'E_IMPORT')
        self.service.change(self.uri, 'emit 1\n', 3)
        with patch('pathlib.Path.open', side_effect=AssertionError('Unreachable file was read')):
            self.assertEqual(self.service.diagnostics(self.uri)[self.uri], [])

    def test_completed_block_names_do_not_leak_into_completion(self):
        self.source('let outside = 1\nwhen true:\n    let inside = 2\n    say text(inside)\n\n')
        labels = {item['label'] for item in self.service.completion(self.uri, {'line': 5, 'character': 0})}
        self.assertIn('outside', labels)
        self.assertNotIn('inside', labels)
        self.service.change(self.uri, 'let fresh = 1\n', 2)
        self.assertIn('fresh', {item['label'] for item in self.service.completion(self.uri, {'line': 1, 'character': 0})})
        self.service.change(self.uri, 'emit map([], fn(parameter) => parameter)\n\n', 3)
        self.assertNotIn('parameter', {item['label'] for item in self.service.completion(self.uri, {'line': 2, 'character': 0})})
        self.service.change(self.uri, 'when any([], fn(hidden) => true):\n    emit 1\n\n', 4)
        self.assertNotIn('hidden', {item['label'] for item in self.service.completion(self.uri, {'line': 3, 'character': 0})})

    def test_symlink_cycles_are_diagnostics_and_never_crash_initialize(self):
        loop = self.root / 'loop.zs'
        loop.symlink_to(loop)
        self.assertIsNone(file_path(loop.as_uri()))
        self.source('use "loop.zs"\n')
        self.assertEqual(self.service.diagnostics(self.uri)[self.uri][0]['code'], 'E_IMPORT')
        messages = []
        server = Server(messages.append)
        server.handle(request('initialize', rootUri=loop.as_uri()))
        self.assertIn('result', messages[-1])

    def test_source_document_and_module_limits_and_invalid_format_preserve_source(self):
        self.source('x' * 65537)
        self.assertEqual(self.service.diagnostics(self.uri)[self.uri][0]['code'], 'E_LIMIT')
        self.assertEqual(self.service.formatting(self.uri), [])
        self.service.change(self.uri, 'when true\n', 2)
        from zensigil.errors import SigilError
        with self.assertRaises(SigilError):
            self.service.formatting(self.uri)
        self.assertEqual(self.service.documents[self.uri].source, 'when true\n')
        for i in range(63):
            self.assertTrue(self.service.open('untitled:' + str(i), '', 1))
        self.assertFalse(self.service.open('untitled:overflow', '', 1))
        self.assertEqual(len(self.service.documents), 64)
        self.assertIn('map', [item['label'] for item in self.service.completion(self.uri, {'line': 0, 'character': 2})])


if __name__ == '__main__':
    unittest.main()
