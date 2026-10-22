"""Navigation and workspace changes preserve source boundaries and lifecycle."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from zensigil.errors import SigilError
from zensigil.language_tools import LanguageService, at_position
from zensigil.lsp import Server


def request(method, identity=1, **params):
    return dict(jsonrpc='2.0', id=identity, method=method, params=params)


def notice(method, **params):
    return dict(jsonrpc='2.0', method=method, params=params)


class ReferenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name).resolve()
        self.service = LanguageService([self.root.as_uri()])
        self.uri = (self.root / 'main.zs').as_uri()

    def tearDown(self):
        self.temp.cleanup()

    def test_references_distinguish_shadowed_mutable_and_captured_bindings(self):
        source = ('var value = 1\nset value = 2\n'
                  'let reader = fn() => value\n'
                  'when true:\n    let value = 4\n    emit value\n'
                  'emit value\nemit reader()\n')
        self.service.open(self.uri, source, 1)
        where = {'line': 0, 'character': 5}
        result = self.service.references(self.uri, where)
        self.assertEqual([item['range']['start']['line'] for item in result], [1, 2, 6])
        result = self.service.references(self.uri, where, True)
        self.assertEqual([item['range']['start']['line'] for item in result], [0, 1, 2, 6])
        inner = self.service.references(self.uri, {'line': 5, 'character': 10}, True)
        self.assertEqual([item['range']['start']['line'] for item in inner], [4, 5])

    def test_module_identity_and_open_importers_are_distinct_and_deduplicated(self):
        library = self.root / 'math.zs'
        library.write_text('export fn double(x):\n    return x * 2\n')
        other = self.root / 'other.zs'
        other.write_text('export fn double(x):\n    return x + 1\n')
        self.service.open(self.uri, 'use "math.zs" as math\nuse "other.zs" as other\nemit math.double(1)\nemit other.double(1)\n', 1)
        importer = (self.root / 'second.zs').as_uri()
        self.service.open(importer, 'use "math.zs"\nemit double(2)\n', 1)
        self.service.open(library.as_uri(), library.read_text(), 1)
        result = self.service.references(library.as_uri(), {'line': 0, 'character': 11}, True)
        self.assertEqual([(Path(item['uri']).name, item['range']['start']['line']) for item in result],
                         [('main.zs', 2), ('math.zs', 0), ('second.zs', 1)])
        alias = self.service.references(self.uri, {'line': 0, 'character': 18}, True)
        self.assertEqual([item['range']['start']['line'] for item in alias], [0, 2])
        self.service.close(importer)
        self.assertEqual(len(self.service.references(library.as_uri(), {'line': 0, 'character': 11}, True)), 2)

    def test_references_never_scan_unopened_programs_or_unreachable_modules(self):
        self.service.open(self.uri, 'let value = 1\nemit value\n', 1)
        (self.root / 'unopened.zs').write_text('emit value\n')
        with patch('pathlib.Path.open', side_effect=AssertionError('Unexpected disk read')):
            self.assertEqual(len(self.service.references(self.uri, {'line': 0, 'character': 5})), 1)

    def test_rule_and_test_labels_are_symbols_not_lexical_references(self):
        self.service.open(self.uri, 'rule "review":\n    emit 1\ntest "expectation":\n    require true, "ok"\n', 1)
        self.assertEqual({item['name'] for item in self.service.symbols(self.uri)}, {'review', 'expectation'})
        for line in (0, 2):
            for character in (1, 6, 8):
                where = {'line': line, 'character': character}
                self.assertEqual(self.service.references(self.uri, where, True), [])
                self.assertIsNone(self.service.definition(self.uri, where))

    def test_unresolved_inputs_and_builtins_have_no_false_declaration(self):
        self.service.open(self.uri, 'emit text(input)\n', 1)
        self.assertEqual(self.service.references(self.uri, {'line': 0, 'character': 7}), [])
        self.assertEqual(self.service.references(self.uri, {'line': 0, 'character': 12}), [])

    def test_invalid_positions_do_not_move_to_another_token(self):
        source = 'let value = 1\nemit ["🌱", value]\n'
        self.service.open(self.uri, source, 1)
        for where in ({'line': 1, 'character': 8}, {'line': 1, 'character': 999},
                      {'line': -1, 'character': 0}, {'line': 0, 'character': True}, {}):
            self.assertIsNone(at_position(source, where))
            self.assertIsNone(self.service.definition(self.uri, where))
            self.assertIsNone(self.service.hover(self.uri, where))
            self.assertEqual(self.service.completion(self.uri, where), [])
            self.assertEqual(self.service.references(self.uri, where), [])
        self.assertEqual(at_position('🌱', {'line': 0, 'character': 2}), (1, 2))

    def test_references_do_not_build_completion_contexts_or_index_unrelated_locals(self):
        source = ''.join(f'let value_{index} = {index}\n' for index in range(1000)) + 'emit value_0\n'
        for index in range(20):
            self.service.open((self.root / f'program{index}.zs').as_uri(), source, 1)
        uri = (self.root / 'program0.zs').as_uri()
        with patch('zensigil.language_tools.Index.remember', side_effect=AssertionError('Built completion context')):
            with patch.object(self.service, 'bundle', wraps=self.service.bundle) as bundled:
                result = self.service.references(uri, {'line': 0, 'character': 5})
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['range']['start']['line'], 1000)
        self.assertEqual(bundled.call_count, 1)

    def test_reference_results_fail_explicitly_at_count_and_byte_limits(self):
        self.service.open(self.uri, 'let value = 1\n' + 'emit value\n' * 1001, 1)
        with self.assertRaisesRegex(SigilError, '1000-location'):
            self.service.references(self.uri, {'line': 0, 'character': 5})
        self.service.change(self.uri, 'let value = 1\nemit value\n', 2)
        with patch('zensigil.language_tools.MAX_REFERENCE_BYTES', 2):
            with self.assertRaisesRegex(SigilError, '512 KiB'):
                self.service.references(self.uri, {'line': 0, 'character': 5})


class WorkspaceLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name).resolve()
        self.sent, self.logs = [], []
        self.server = Server(self.sent.append, self.logs.append)
        self.uri = (self.root / 'main.zs').as_uri()
        self.module = self.root / 'math.zs'
        self.module.write_text('fn double(x):\n    return x * 2\n')

    def tearDown(self):
        self.temp.cleanup()

    def initialize(self, roots=()):
        self.server.handle(request('initialize', workspaceFolders=[{'uri': uri} for uri in roots]))
        return self.sent[-1]['result']['capabilities']

    def open(self):
        self.server.handle(notice('textDocument/didOpen', textDocument={
            'uri': self.uri, 'version': 1, 'text': 'use "math.zs"\nemit double(3)\n'}))

    def changes(self, added=(), removed=()):
        self.server.handle(notice('workspace/didChangeWorkspaceFolders', event={
            'added': [{'uri': uri} for uri in added], 'removed': [{'uri': uri} for uri in removed]}))

    def test_dynamic_roots_recheck_imports_and_clear_old_module_diagnostics(self):
        caps = self.initialize()
        self.assertTrue(caps['referencesProvider'])
        self.assertTrue(caps['workspace']['workspaceFolders']['changeNotifications'])
        self.open()
        self.assertEqual(self.sent[-1]['params']['diagnostics'][0]['code'], 'E_IMPORT')
        self.changes(added=[self.root.as_uri()])
        self.assertEqual(self.sent[-1]['params']['diagnostics'], [])
        self.module.write_text('fn double(x):\n    return missing\n')
        self.server.handle(notice('workspace/didChangeWatchedFiles', changes=[{'uri': self.module.as_uri(), 'type': 2}]))
        self.assertEqual(self.sent[-1]['params']['uri'], self.module.as_uri())
        self.assertEqual(self.sent[-1]['params']['diagnostics'][0]['code'], 'E_NAME')
        self.changes(removed=[self.root.as_uri()])
        self.assertEqual(self.sent[-1]['params']['uri'], self.module.as_uri())
        self.assertEqual(self.sent[-1]['params']['diagnostics'], [])
        self.assertEqual(self.sent[-2]['params']['diagnostics'][0]['code'], 'E_IMPORT')

    def test_watch_events_follow_explicit_imports_and_unsaved_overlay(self):
        self.initialize([self.root.as_uri()]); self.open()
        self.server.handle(notice('textDocument/didOpen', textDocument={
            'uri': self.module.as_uri(), 'version': 1, 'text': 'fn double(x):\n    return x * 3\n'}))
        self.module.write_text('fn double(x):\n    return missing\n')
        self.server.handle(notice('workspace/didChangeWatchedFiles', changes=[{'uri': self.module.as_uri(), 'type': 2}]))
        self.assertTrue(all(not item['params']['diagnostics'] for item in self.sent[-2:]))
        self.server.handle(notice('textDocument/didClose', textDocument={'uri': self.module.as_uri()}))
        self.assertEqual(self.sent[-1]['params']['diagnostics'][0]['code'], 'E_NAME')
        self.module.unlink()
        self.server.handle(notice('workspace/didChangeWatchedFiles', changes=[{'uri': self.module.as_uri(), 'type': 3}]))
        self.assertEqual(self.sent[-2]['params']['diagnostics'][0]['code'], 'E_IMPORT')
        self.assertEqual(self.sent[-1]['params']['diagnostics'], [])
        self.module.write_text('fn double(x):\n    return x * 4\n')
        self.server.handle(notice('workspace/didChangeWatchedFiles', changes=[{'uri': self.module.as_uri(), 'type': 1}]))
        self.assertEqual(self.sent[-1]['params']['diagnostics'], [])

    def test_outside_events_and_invalid_changes_do_not_read_source(self):
        self.initialize([self.root.as_uri()]); self.open()
        count = len(self.sent)
        with patch('pathlib.Path.open', side_effect=AssertionError('Unrelated event read source')):
            for changes in ([{'uri': (self.root.parent / 'outside.zs').as_uri(), 'type': 2}],
                            [{'uri': self.module.as_uri(), 'type': True}],
                            [{'uri': self.module.as_uri(), 'type': 4}], [], None):
                self.server.handle(notice('workspace/didChangeWatchedFiles', changes=changes))
            self.server.handle(notice('workspace/didChangeWorkspaceFolders', event={'added': 'wrong', 'removed': []}))
        self.assertEqual(len(self.sent), count)
        self.assertTrue(self.logs)
        self.assertEqual(self.server.service.roots, (self.root,))

    def test_root_limit_is_atomic_and_most_specific_root_wins(self):
        paths = []
        for index in range(33):
            path = self.root / str(index); path.mkdir(); paths.append(path)
        service = LanguageService([path.as_uri() for path in paths[:32]])
        prior = service.roots
        with self.assertRaisesRegex(SigilError, '32 workspace'):
            service.update_roots([paths[32].as_uri()], [])
        self.assertEqual(service.roots, prior)
        service.set_roots([self.root.as_uri(), paths[0].as_uri()])
        self.assertEqual(service.root((paths[0] / 'x.zs').as_uri()), paths[0])
        service.update_roots([], [paths[0].as_uri()])
        self.assertEqual(service.root((paths[0] / 'x.zs').as_uri()), self.root)

    def test_protocol_reference_request_preserves_include_declaration(self):
        self.initialize([self.root.as_uri()]); self.open()
        for include, count in [(False, 1), (True, 2)]:
            self.server.handle(request('textDocument/references', 9, textDocument={'uri': self.uri},
                                       position={'line': 1, 'character': 7}, context={'includeDeclaration': include}))
            self.assertEqual(self.sent[-1]['id'], 9)
            self.assertEqual(len(self.sent[-1]['result']), count)


if __name__ == '__main__':
    unittest.main()
