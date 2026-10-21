"""Tooling preserves meaning, comments, source files and project boundaries."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from zensigil import run
from zensigil.astio import ast_document
from zensigil.errors import SigilError
from zensigil.formatter import format_source
from zensigil.projects import init_project, load_project

ROOT = Path(__file__).resolve().parents[1]


class FormatterTests(unittest.TestCase):
    def test_preserves_comments_string_spelling_and_evaluation(self):
        source = '# Keep this # comment\nlet text_value="a # string\\n\\u0041"# inline\nlet result=2*-3+10\nemit {text:text_value,result:result}\n'
        formatted = format_source(source)
        self.assertIn('# Keep this # comment\n', formatted)
        self.assertIn('"a # string\\n\\u0041"  # inline', formatted)
        self.assertEqual(run(source)['values'], run(formatted)['values'])
        self.assertEqual(format_source(formatted), formatted)
        unicode_source = 'emit \"line\u2028separator\u0085kept\"\n'
        self.assertEqual(format_source(unicode_source), unicode_source)

    def test_indents_multiline_collections_and_handles_extended_grammar(self):
        source = 'fn f(x:number)->number:\n    return choose x>0 then x otherwise -x\nvar values=[\n1,\n2, # second\n]\nwhile len(values)>0:\n    emit f(values[0])??0\n    break\ntest "Membership":\n    require 1 in values and 3 not in values,"membership"\n'
        formatted = format_source(source)
        self.assertIn('    2,  # second', formatted)
        self.assertIn('fn f(x: number) -> number:', formatted)
        self.assertEqual(format_source(formatted), formatted)
        self.assertEqual(run(source)['values'], run(formatted)['values'])

    def test_rejects_invalid_source_instead_of_guessing(self):
        with self.assertRaises(SigilError):
            format_source('when true\n say "broken"\n')

    def test_bundled_examples_are_semantically_preserved_and_idempotent(self):
        for source_file in (ROOT / 'examples').glob('*.zs'):
            with self.subTest(source_file=source_file.name):
                text = format_source(source_file.read_text(encoding='utf-8'))
                self.assertEqual(format_source(text), text)

    def test_ast_is_json_only_with_locations_and_does_not_load_modules(self):
        tree = ast_document('use "missing.zs"\nlet x = 42\n')
        self.assertEqual(tree['format_version'], 1)
        self.assertEqual(tree['body'][0]['kind'], 'use')
        self.assertEqual(tree['body'][1]['line'], 2)
        self.assertEqual(json.loads(json.dumps(tree)), tree)


class ToolingCLITests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.directory = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def cli(self, *arguments):
        return subprocess.run([sys.executable, '-m', 'zensigil', *map(str, arguments)], cwd=ROOT,
                              capture_output=True, text=True, timeout=10)

    def test_fmt_default_check_and_atomic_write_preserve_permissions(self):
        source = self.directory / 'source.zs'
        source.write_text('emit 1+2# keep\n')
        source.chmod(0o640)
        # Windows exposes its supported permission bits, not POSIX group modes.
        original_mode = source.stat().st_mode & 0o777
        expected = 'emit 1 + 2  # keep\n'
        self.assertEqual(self.cli('fmt', source).stdout, expected)
        self.assertEqual(source.read_text(), 'emit 1+2# keep\n')
        self.assertEqual(self.cli('fmt', source, '--check').returncode, 1)
        self.assertEqual(self.cli('fmt', source, '--write').returncode, 0)
        self.assertEqual(source.read_text(), expected)
        self.assertEqual(source.stat().st_mode & 0o777, original_mode)
        self.assertEqual(self.cli('fmt', source, '--check').returncode, 0)
        self.assertFalse(list(self.directory.glob('.zensigil-format-*')))

    def test_bad_file_and_invalid_source_do_not_get_overwritten(self):
        source = self.directory / 'broken.zs'
        source.write_text('when true\n')
        result = self.cli('fmt', source, '--write')
        self.assertEqual(result.returncode, 1)
        self.assertIn('E_SYNTAX', result.stderr)
        self.assertEqual(source.read_text(), 'when true\n')
        for name in ('missing.zs', 'other.txt'):
            result = self.cli('fmt', self.directory / name)
            self.assertEqual(result.returncode, 1)
            self.assertNotIn('Traceback', result.stderr)
        link = self.directory / 'link.zs'
        link.symlink_to(source)
        self.assertEqual(self.cli('fmt', link, '--write').returncode, 1)

    def test_ast_json_and_parse_failure_are_structured(self):
        source = self.directory / 'source.zs'
        source.write_text('emit 42\n')
        result = self.cli('ast', source, '--json')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)['body'][0]['kind'], 'emit')
        source.write_text('emit [\n')
        result = self.cli('ast', source, '--json')
        self.assertEqual(result.returncode, 1)
        self.assertFalse(json.loads(result.stdout)['ok'])

    def test_init_run_check_and_test_project(self):
        project = self.directory / 'sample'
        result = self.cli('init', project)
        self.assertEqual(result.returncode, 0, result.stderr)
        manifest = load_project(project)
        self.assertEqual(manifest['entry'], (project / 'main.zs').resolve())
        for command in ('run', 'check', 'test'):
            result = self.cli(command, project, '--json')
            self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
            parsed = json.loads(result.stdout)
            if command == 'run':
                self.assertEqual(parsed['values'], [{'greeting': 'Hello from ZenSigil', 'answer': 42}])
            elif command == 'test':
                self.assertEqual((parsed['total'], parsed['passed'], parsed['failed']), (2, 2, 0))
                self.assertEqual(len(parsed['tests']), 2)
        existing = (project / 'main.zs').read_text()
        self.assertEqual(self.cli('init', project).returncode, 1)
        self.assertEqual((project / 'main.zs').read_text(), existing)

    def test_test_failure_and_run_do_not_execute_test_blocks(self):
        source = self.directory / 'suite.zs'
        source.write_text('emit 99\ntest "Failure":\n    require false, "Expected failure"\ntest "Independent":\n    require true, "pass"\n')
        self.assertEqual(json.loads(self.cli('run', source, '--json').stdout)['values'], [99])
        tested = self.cli('test', source, '--json')
        self.assertEqual(tested.returncode, 1)
        result = json.loads(tested.stdout)
        self.assertEqual((result['total'], result['passed'], result['failed']), (2, 1, 1))
        self.assertEqual(result['values'], [])

    def test_pack_modules_and_run_without_original_files(self):
        project = self.directory / 'sample'
        init_project(project)
        portable = self.directory / 'program.sigil.json'
        packed = self.cli('pack', project / 'main.zs', '--name', 'Portable modules', '--output', portable)
        self.assertEqual(packed.returncode, 0, packed.stderr or packed.stdout)
        self.assertIn('lib/math.zs', json.loads(portable.read_text())['modules'])
        (project / 'lib/math.zs').unlink()
        result = self.cli('run', portable, '--json')
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        self.assertEqual(json.loads(result.stdout)['values'][0]['answer'], 42)

    def test_output_cannot_replace_module_manifest_or_project_entry(self):
        project = self.directory / 'sample'
        init_project(project)
        for command, target in (('pack', project / 'lib/math.zs'), ('run', project / 'lib/math.zs'), ('run', project / 'zensigil.json'), ('run', project / 'main.zs')):
            before = target.read_bytes()
            arguments = ['pack', project / 'main.zs', '--name', 'Protected'] if command == 'pack' else ['run', project]
            result = self.cli(*arguments, '--output', target, '--force')
            self.assertEqual(result.returncode, 1, result.stdout)
            self.assertEqual(target.read_bytes(), before)

    def test_early_input_failure_cannot_overwrite_a_module(self):
        project = self.directory / 'sample'
        init_project(project)
        invalid = project / 'input.json'
        invalid.write_text('{broken')
        target = project / 'lib/math.zs'
        before = target.read_bytes()
        result = self.cli('run', project, '--data', invalid, '--output', target, '--force')
        self.assertEqual(result.returncode, 1)
        self.assertEqual(target.read_bytes(), before)

    def test_manifest_rejects_path_escape_unknown_fields_and_bad_versions(self):
        project = self.directory / 'sample'
        init_project(project)
        manifest_path = project / 'zensigil.json'
        original = json.loads(manifest_path.read_text())
        for changes in ({'entry': '../outside.zs'}, {'entry': '/tmp/outside.zs'}, {'entry': 'lib\\bad.zs'},
                        {'entry': './main.zs'}, {'entry': 'main.txt'}, {'format_version': True},
                        {'language_version': '9.0.0'}, {'tests': ['tests.zs', 'tests.zs']}, {'unknown': True}):
            with self.subTest(changes=changes):
                manifest_path.write_text(json.dumps(dict(original, **changes)))
                result = self.cli('run', project, '--json')
                self.assertEqual(result.returncode, 1)
                self.assertEqual(json.loads(result.stdout)['diagnostics'][0]['code'], 'E_PROJECT')
        manifest_path.write_text(json.dumps(dict(original, entry='escape.zs')))
        outside = self.directory / 'outside.zs'
        outside.write_text('emit 7\n')
        (project / 'escape.zs').symlink_to(outside)
        self.assertEqual(self.cli('run', project, '--json').returncode, 1)

    def test_explicit_module_root_and_module_error_location(self):
        project = self.directory / 'sample'
        init_project(project)
        nested = project / 'lib' / 'runner.zs'
        nested.write_text('use "lib/math.zs"\nemit double(3)\n')
        self.assertEqual(self.cli('run', nested, '--json').returncode, 1)
        result = self.cli('run', nested, '--module-root', project, '--json')
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        self.assertEqual(json.loads(result.stdout)['values'], [6])
        (project / 'lib/math.zs').write_text('fn bad():\n    return [\n')
        result = json.loads(self.cli('check', project, '--json').stdout)
        self.assertFalse(result['ok'])
        self.assertEqual(result['diagnostics'][0]['source_file'], 'lib/math.zs')
        before = (project / 'lib/math.zs').read_bytes()
        result = self.cli('run', project, '--output', project / 'lib/math.zs', '--force')
        self.assertEqual(result.returncode, 1)
        self.assertEqual((project / 'lib/math.zs').read_bytes(), before)


if __name__ == '__main__':
    unittest.main()
