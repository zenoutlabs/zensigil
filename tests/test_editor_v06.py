"""Namespace-aware editor behavior against the real parser/compiler/checker."""
import json
from pathlib import Path, PurePosixPath, PureWindowsPath
import tempfile
import unittest
from unittest.mock import patch

from zensigil.language_tools import LanguageService, _file_uri_path, builtin_signature, file_path, utf16
from zensigil.lsp import Server


class FileUriTests(unittest.TestCase):
    def test_windows_drive_uri_conversion_on_every_host(self):
        cases = {
            'file:///C:/Users/Nikko/project/main.zs': 'C:/Users/Nikko/project/main.zs',
            'file:///c%3A/Program%20Files/ZenSigil/main.zs': 'c:/Program Files/ZenSigil/main.zs',
            'file://localhost/D:/project/%E6%96%87.zs': 'D:/project/文.zs',
            'file:///Z:/': 'Z:/',
        }
        for uri, expected in cases.items():
            with self.subTest(uri=uri):
                found = _file_uri_path(uri, windows=True)
                self.assertEqual(found, PureWindowsPath(expected))
                self.assertTrue(found.is_absolute())
                self.assertEqual(_file_uri_path(found.as_uri(), windows=True), found)
        for uri in ['file:///tmp/project/main.zs', 'file:///C:relative.zs',
                    'file:C:/project/main.zs', 'file:///C:/main.zs:stream',
                    'file:///C:/folder/D:/main.zs', 'file:///C|/project/main.zs']:
            with self.subTest(uri=uri):
                self.assertIsNone(_file_uri_path(uri, windows=True))

    def test_posix_uri_conversion_preserves_absolute_names(self):
        cases = {
            'file:///tmp/Zen%20Sigil/main.zs': '/tmp/Zen Sigil/main.zs',
            'file://localhost/tmp/%E6%96%87.zs': '/tmp/文.zs',
            'file:///tmp/percent%252Fname.zs': '/tmp/percent%2Fname.zs',
            'file:///tmp/hash%23and%3F.zs': '/tmp/hash#and?.zs',
            'file:///C:/a.zs': '/C:/a.zs',
        }
        for uri, expected in cases.items():
            with self.subTest(uri=uri):
                found = _file_uri_path(uri, windows=False)
                self.assertEqual(found, PurePosixPath(expected))
                self.assertEqual(_file_uri_path(found.as_uri(), windows=False), found)

    def test_remote_relative_unc_and_encoded_separators_are_rejected_before_io(self):
        rejected = ['https://example.com/main.zs', 'untitled:main.zs', 'file:main.zs',
                    'file://server/share/main.zs', 'file://localhost:80/C:/main.zs',
                    'file://user@localhost/C:/main.zs', 'file:////server/share/main.zs',
                    'file:////?/C:/main.zs', 'file:///C:/folder\\main.zs',
                    'file:///C:/folder%2f..%2fmain.zs', 'file:///C:/folder%5Cmain.zs',
                    'file://localhost/%2Fserver/share/main.zs',
                    'file:///C:/main.zs?download=1', 'file:///C:/main.zs#fragment',
                    'file:///C:/bad%00name.zs', 'file:///C:/bad%FFname.zs',
                    'file:///C:/bad%name.zs', 'file:///C:/bad%2name.zs',
                    'file:///C:/bad\nname.zs', 'file:///C:/bad%09name.zs', 'file://[', None]
        for uri in rejected:
            for windows in (False, True):
                with self.subTest(uri=uri, windows=windows):
                    self.assertIsNone(_file_uri_path(uri, windows=windows))
            with self.subTest(uri=uri), patch('pathlib.Path.resolve', side_effect=AssertionError('Invalid URI reached filesystem')):
                self.assertIsNone(file_path(uri))

    def test_native_roundtrip_declared_workspace_and_unsaved_import(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = (Path(temporary) / 'Zen Sigil 文').resolve()
            root.mkdir()
            main, module = root / 'main.zs', root / 'math.zs'
            self.assertEqual(file_path(root.as_uri()), root)
            self.assertEqual(file_path(module.as_uri()), module)
            service = LanguageService([root.as_uri()])
            self.assertEqual(service.roots, (root,))
            service.open(main.as_uri(), 'use "math.zs" as math\nemit math.double(2)\n', 1)
            service.open(module.as_uri(), 'export fn double(value):\n    return value * 2\n', 1)
            self.assertEqual(service.root(main.as_uri()), root)
            self.assertEqual(service.diagnostics(main.as_uri())[main.as_uri()], [])
            definition = service.definition(main.as_uri(), {'line': 1, 'character': 12})
            self.assertEqual(definition['uri'], module.as_uri())


class NamespaceEditorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.service = LanguageService([self.root.as_uri()])
        self.uri = (self.root / 'main.zs').as_uri()
        self.module = self.root / 'math.zs'
        self.module.write_text('fn helper(value):\n    return value * 2\n'
                               'export fn double(value: number) -> number:\n    return helper(value)\n')

    def source(self, text, version=1):
        self.service.open(self.uri, text, version)

    def labels(self, line, character, uri=None):
        return {item['label'] for item in self.service.completion(uri or self.uri, {'line': line, 'character': character})}

    def test_incomplete_dot_and_prefix_completion_expose_only_public_functions(self):
        for version, expression in enumerate(['math.', 'emit math.', 'emit math.d',
                                               'emit map([1], math.', '    return math.'], 1):
            prefix = 'use "math.zs" as math\n'
            if expression.startswith('    '):
                prefix += 'fn apply(value):\n'
            source = prefix + expression + '\n'
            self.source(source, version)
            line = len(prefix.splitlines())
            self.assertEqual(self.labels(line, len(expression)), {'double'})
            self.assertEqual(self.service.documents[self.uri].source, source)

    def test_qualified_hover_definition_and_alias_symbol_keep_original_sources(self):
        self.source('use "math.zs" as math\nemit math.double(3)\n')
        where = {'line': 1, 'character': 13}
        self.assertEqual(self.service.definition(self.uri, where), {
            'uri': self.module.as_uri(),
            'range': {'start': {'line': 2, 'character': 10}, 'end': {'line': 2, 'character': 16}}})
        self.assertEqual(self.service.hover(self.uri, where)['contents']['value'], 'fn double(value: number) -> number')
        self.assertEqual(self.service.definition(self.uri, {'line': 1, 'character': 7})['range']['start'],
                         {'line': 0, 'character': 17})
        self.assertEqual(self.service.hover(self.uri, {'line': 1, 'character': 7})['contents']['value'],
                         'namespace math from "math.zs"')
        symbols = self.service.symbols(self.uri)
        self.assertEqual([(item['name'], item['kind']) for item in symbols], [('math', 3)])
        self.assertNotIn('double', self.labels(2, 0))
        self.assertNotIn('helper', self.labels(2, 0))
        self.assertIn('math', self.labels(2, 0))

    def test_private_or_missing_member_has_diagnostic_but_no_false_navigation(self):
        for version, name in enumerate(['helper', 'map'], 1):
            self.source('use "math.zs" as math\nemit math.' + name + '(3)\n', version)
            self.assertEqual(self.service.diagnostics(self.uri)[self.uri][0]['code'], 'E_IMPORT')
            self.assertIsNone(self.service.definition(self.uri, {'line': 1, 'character': 11}))
            self.assertIsNone(self.service.hover(self.uri, {'line': 1, 'character': 11}))

    def test_same_named_functions_resolve_by_canonical_source_identity(self):
        other = self.root / 'other.zs'
        other.write_text('fn helper(value):\n    return value + 1\n'
                         'export fn double(value):\n    return helper(value) + helper(value)\n')
        self.source('use "math.zs" as first\nuse "other.zs" as second\n'
                    'fn helper(value):\n    return 99\n'
                    'emit [first.double(3), second.double(3), helper(3)]\n')
        first = self.service.definition(self.uri, {'line': 4, 'character': 13})
        second = self.service.definition(self.uri, {'line': 4, 'character': 31})
        local = self.service.definition(self.uri, {'line': 4, 'character': 41})
        self.assertEqual([first['uri'], second['uri'], local['uri']],
                         [self.module.as_uri(), other.as_uri(), self.uri])
        index = self.service.index(self.uri)
        for module in [self.module, other]:
            reference = index.reference(module.as_uri(), (4, 13))
            self.assertEqual(reference[1]['uri'], module.as_uri())
            self.assertEqual(reference[1]['range']['start']['line'], 0)

    def test_source_local_aliases_and_module_functions_do_not_leak(self):
        second = self.root / 'second.zs'
        second.write_text('export fn triple(value):\n    return value * 3\n')
        wrapper = self.root / 'wrapper.zs'
        wrapper.write_text('use "math.zs" as shared\nexport fn apply(value):\n    return shared.double(value)\n')
        self.source('use "second.zs" as shared\nuse "wrapper.zs" as wrapper\n'
                    'fn root_only():\n    return 1\nemit wrapper.apply(3)\n')
        index = self.service.index(self.uri)
        reference = index.reference(wrapper.as_uri(), (3, 21))
        self.assertEqual(reference[1]['uri'], self.module.as_uri())
        self.assertEqual([entry['name'] for entry in index.members(wrapper.as_uri(), 'shared')], ['double'])
        self.assertEqual([entry['name'] for entry in index.members(self.uri, 'shared')], ['triple'])
        visible = {entry['name'] for entry in index.visible(wrapper.as_uri(), (3, 25))}
        self.assertTrue({'shared', 'apply', 'value'} <= visible)
        self.assertTrue({'root_only', 'triple', 'helper', 'wrapper'}.isdisjoint(visible))
        self.assertEqual(index.members(self.uri, 'wrapper')[0]['name'], 'apply')

    def test_bare_imports_preserve_public_reexports_and_private_helpers_are_local(self):
        facade = self.root / 'facade.zs'
        facade.write_text('use "math.zs"\n')
        self.source('use "facade.zs"\nemit double(3)\n')
        self.assertEqual(self.service.definition(self.uri, {'line': 1, 'character': 8})['uri'], self.module.as_uri())
        self.assertIn('double', self.labels(2, 0))
        self.assertNotIn('helper', self.labels(2, 0))
        self.service.open(self.module.as_uri(), self.module.read_text(), 1)
        self.assertIn('helper', self.labels(4, 0, self.module.as_uri()))

    def test_open_overlay_changes_public_surface_and_stale_change_cannot_restore_it(self):
        self.source('use "math.zs" as math\nemit math.\n')
        self.assertEqual(self.labels(1, 10), {'double'})
        overlay = '# changed only in the editor\nexport fn triple(value):\n    return value * 3\n'
        self.service.open(self.module.as_uri(), overlay, 8)
        self.assertEqual(self.labels(1, 10), {'triple'})
        self.assertFalse(self.service.change(self.module.as_uri(), self.module.read_text(), 7))
        self.assertEqual(self.labels(1, 10), {'triple'})
        self.source('use "math.zs" as math\nemit math.triple(3)\n', 2)
        self.assertEqual(self.service.definition(self.uri, {'line': 1, 'character': 12})['range']['start']['line'], 1)
        self.assertEqual(self.service.diagnostics(self.uri)[self.uri], [])
        self.service.close(self.module.as_uri())
        self.assertEqual(self.service.diagnostics(self.uri)[self.uri][0]['code'], 'E_IMPORT')
        self.assertIn('double', self.module.read_text())

    def test_utf16_qualified_member_ranges_and_formatter_preserve_namespace_syntax(self):
        source = 'use "math.zs" as math\nemit ["🌱",math . double(3)]'
        self.source(source)
        start = utf16('emit ["🌱",math . ')
        hover = self.service.hover(self.uri, {'line': 1, 'character': start + 1})
        self.assertEqual(hover['range']['start'], {'line': 1, 'character': start})
        self.assertEqual(hover['range']['end']['character'], start + 6)
        self.assertEqual(self.service.formatting(self.uri)[0]['newText'],
                         'use "math.zs" as math\nemit ["🌱", math.double(3)]\n')

    def test_completion_does_not_treat_strings_comments_records_or_nested_fields_as_aliases(self):
        for version, line in enumerate(['say "math."', '# math.', 'emit {math: 1}.math.', 'emit other . math.'], 1):
            self.source('use "math.zs" as math\n' + line + '\n', version)
            cursor = len(line) - 1 if line.startswith('say ') else len(line)
            self.assertNotIn('double', self.labels(1, cursor))
        standalone = LanguageService()
        standalone.open(self.uri, 'use "math.zs" as math\nemit math.\n', 1)
        with patch('pathlib.Path.open', side_effect=AssertionError('Undeclared workspace read')):
            self.assertEqual(standalone.completion(self.uri, {'line': 1, 'character': 10}), [])

    def test_alias_completion_at_eof_does_not_keep_inner_locals_or_lambda_parameters(self):
        self.source('use "math.zs" as math\nwhen true:\n    let inside = 1\n'
                    '    emit map([], fn (parameter) => math.double(parameter))\n\n')
        labels = self.labels(5, 0)
        self.assertIn('math', labels)
        self.assertTrue({'inside', 'parameter', 'helper', 'double'}.isdisjoint(labels))

    def test_lsp_advertises_dot_and_queries_unsaved_namespace_overlays(self):
        sent = []
        server = Server(sent.append, lambda message: self.fail(message))
        def send(method, identity=None, **params):
            message = dict(jsonrpc='2.0', method=method, params=params)
            if identity is not None:
                message['id'] = identity
            server.handle(message)
        send('initialize', 1, rootUri=self.root.as_uri())
        self.assertEqual(sent[-1]['result']['capabilities']['completionProvider']['triggerCharacters'], ['.'])
        send('textDocument/didOpen', textDocument={'uri': self.uri, 'version': 1,
                                                  'text': 'use "math.zs" as math\nemit math.\n'})
        send('textDocument/completion', 2, textDocument={'uri': self.uri}, position={'line': 1, 'character': 10})
        self.assertEqual([item['label'] for item in sent[-1]['result']], ['double'])
        send('textDocument/didOpen', textDocument={'uri': self.module.as_uri(), 'version': 1,
                                                  'text': 'export fn changed():\n    return 1\n'})
        send('textDocument/completion', 3, textDocument={'uri': self.uri}, position={'line': 1, 'character': 10})
        self.assertEqual([item['label'] for item in sent[-1]['result']], ['changed'])

    def test_v06_highlighting_snippets_and_builtin_signatures(self):
        root = Path(__file__).resolve().parents[1] / 'editors' / 'vscode'
        grammar = json.loads((root / 'syntaxes' / 'zensigil.tmLanguage.json').read_text())
        self.assertIn('|as|export|', next(item['match'] for item in grammar['patterns'] if item['name'] == 'keyword.control.zensigil'))
        self.assertIn('|namespace|', next(item['match'] for item in grammar['patterns'] if item['name'] == 'support.type.zensigil'))
        snippets = json.loads((root / 'snippets' / 'zensigil.json').read_text())
        self.assertEqual(snippets['Namespaced import']['prefix'], 'useas')
        self.assertEqual(snippets['Exported function']['prefix'], 'exportfn')
        self.assertEqual(builtin_signature('scan'), 'scan(items, initial, combine)')
        self.assertEqual(builtin_signature('record_from_entries'), 'record_from_entries(entries)')


if __name__ == '__main__':
    unittest.main()
