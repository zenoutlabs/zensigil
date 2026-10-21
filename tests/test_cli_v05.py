import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from zensigil import test as run_tests
from zensigil.lint import lint
from zensigil.projects import init_project
from zensigil.project_tools import format_project

ROOT = Path(__file__).resolve().parents[1]

class DeveloperWorkflowTests(unittest.TestCase):
    def cli(self, *args, source=None):
        return subprocess.run([sys.executable, '-m', 'zensigil', *args], cwd=ROOT,
                              input=source, text=True, capture_output=True, timeout=10)

    def test_invalid_project_manifest_cannot_be_overwritten_by_failure_output(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / 'project';init_project(root)
            manifest = root/'zensigil.json'
            manifest.write_text('{unfinished manifest')
            before=manifest.read_bytes()
            result=self.cli('run',str(root),'--output',str(manifest),'--force','--json')
            self.assertEqual(result.returncode,1)
            self.assertEqual(manifest.read_bytes(),before)
            self.assertEqual(json.loads(result.stdout)['diagnostics'][0]['code'],'E_OUTPUT')

    def test_stdin_output_failure_never_implicitly_reads_modules(self):
        import contextlib,io
        from unittest.mock import patch
        from zensigil.__main__ import main
        with tempfile.TemporaryDirectory() as d:
            output=Path(d)/'result.json';output.write_text('{}')
            with patch('sys.stdin',io.StringIO('use "hidden.zs"\nemit 1\n')), patch('zensigil.modules.file_modules') as reader, contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main(['run','-','--output',str(output),'--force','--json']),1)
            reader.assert_not_called()

    def test_stdin_runs_formats_and_inspects_without_implicit_imports(self):
        result = self.cli('run', '-', '--json', source='emit 6 * 7\n')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)['values'], [42])
        self.assertEqual(self.cli('fmt', '-', source='emit   1+2\n').stdout, 'emit 1 + 2\n')
        self.assertEqual(self.cli('ast', '-', source='emit 1\n').returncode, 0)
        missing = self.cli('run', '-', '--json', source='use "lib/math.zs"\nemit double(1)\n')
        self.assertEqual(json.loads(missing.stdout)['diagnostics'][0]['code'], 'E_IMPORT')
        self.assertNotEqual(self.cli('fmt', '-', '--write', source='emit 1').returncode, 0)
        self.assertNotEqual(self.cli('run', '-', '--json', source='#' * 65537).returncode, 0)

    def test_stdin_explicit_module_root(self):
        with tempfile.TemporaryDirectory() as d:
            init_project(Path(d) / 'project')
            result = self.cli('run', '-', '--module-root', str(Path(d) / 'project'), '--json',
                              source='use "lib/math.zs"\nemit double(9)\n')
            self.assertEqual(json.loads(result.stdout)['values'], [18])

    def test_filter_and_listing_do_not_execute_excluded_tests(self):
        source = 'test "Slow":\n    while true:\n        require true, "loop"\ntest "Fast":\n    require 2 + 2 == 4, "sum"\n'
        result = run_tests(source, name_filter='Fast')
        self.assertTrue(result['ok'], result)
        self.assertEqual(result['total'], 1)
        self.assertEqual(result['passed'], 1)
        listed = run_tests(source, list_only=True)
        self.assertEqual([t['name'] for t in listed['tests']], ['Slow', 'Fast'])
        self.assertEqual(listed['stats']['steps'], 0)
        self.assertEqual(listed['passed'], 0)
        self.assertIsNone(listed['tests'][0]['ok'])
        self.assertFalse(run_tests(source, name_filter=3)['ok'])

    def test_cli_empty_filter_and_project_listing(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / 'project'
            init_project(root)
            empty = self.cli('test', str(root), '--filter', 'absent', '--fail-if-empty', '--json')
            self.assertEqual(empty.returncode, 1)
            self.assertEqual(json.loads(empty.stdout)['diagnostics'][0]['code'], 'E_TEST_EMPTY')
            listed = self.cli('test', str(root), '--list', '--json')
            self.assertEqual(listed.returncode, 0, listed.stderr)
            self.assertEqual(json.loads(listed.stdout)['total'], 2)
            self.assertEqual(json.loads(listed.stdout)['stats']['steps'], 0)

    def test_lints_resolve_lexical_uses_and_closure_captures(self):
        source = 'let taken = 3\nlet unused = 5\nlet apply = fn (x) => x + taken\nemit apply(1)\nfn f(x):\n    return x\n    return 2\n'
        result = lint(source)
        self.assertTrue(result['ok'], result)
        self.assertEqual([w['code'] for w in result['warnings']], ['W_UNUSED', 'W_UNREACHABLE'])
        self.assertEqual(result['warnings'][0]['line'], 2)
        result = lint('let value = 1\nwhen true:\n    let value = 2\n    emit value\nemit value\n')
        self.assertEqual([w['code'] for w in result['warnings']], ['W_SHADOW'])
        self.assertEqual(lint('let _intentional = 2\n')['warnings'], [])
        self.assertFalse(lint('return 2\n')['ok'])

    def test_lint_project_strict_is_opt_in(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / 'project';init_project(root)
            with (root/'main.zs').open('a') as f:f.write('let forgotten = 1\n')
            normal = self.cli('lint', str(root), '--json')
            strict = self.cli('lint', str(root), '--strict', '--json')
            self.assertEqual(normal.returncode, 0, normal.stderr)
            self.assertEqual(strict.returncode, 1)
            self.assertEqual(len(json.loads(normal.stdout)['warnings']), 1)

    def test_project_format_preflight_and_explicit_sources(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)/'project';init_project(root)
            library = root/'lib/math.zs'
            library.write_text('fn double(value):\n    return value*2\n')
            untouched = root/'unlisted.zs';untouched.write_text('broken ignored source')
            result = format_project(root)
            self.assertEqual(result['changed'], ['lib/math.zs'])
            self.assertEqual(result['files'], 3)
            (root/'tests.zs').write_text('broken source')
            before=library.read_text()
            with self.assertRaises(Exception):format_project(root,write=True)
            self.assertEqual(library.read_text(), before)
            (root/'tests.zs').write_text('test "Works":\n    require true, "yes"\n')
            format_project(root,write=True)
            self.assertIn('value * 2',library.read_text())
            self.assertEqual(untouched.read_text(),'broken ignored source')

    def test_project_format_rejects_file_symlinks(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)/'project';init_project(root)
            real=root/'actual.zs';real.write_text('emit   1\n')
            (root/'main.zs').unlink()
            try:(root/'main.zs').symlink_to(real)
            except OSError:self.skipTest('symlinks unavailable')
            with self.assertRaises(ValueError):format_project(root,write=True)
            self.assertEqual(real.read_text(),'emit   1\n')

if __name__ == '__main__':unittest.main()
