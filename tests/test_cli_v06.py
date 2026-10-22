"""Subprocess coverage for the 0.6 REPL and CI-report entry points."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

from zensigil import test as run_tests
from zensigil.projects import init_project


ROOT = Path(__file__).resolve().parents[1]
MATH = ('export fn double(value: number) -> number:\n'
        '    return helper(value)\n'
        'fn helper(value):\n'
        '    return value * 2\n')


class CLI06Tests(unittest.TestCase):
    def cli(self, *args, source=None, cwd=ROOT):
        env = os.environ.copy()
        env['PYTHONPATH'] = str(ROOT) + os.pathsep + env.get('PYTHONPATH', '')
        return subprocess.run([sys.executable, '-m', 'zensigil', *map(str, args)],
                              cwd=cwd, input=source, text=True, capture_output=True,
                              timeout=10, env=env)

    def report(self, path):
        root = ET.parse(path).getroot()
        self.assertEqual(root.tag, 'testsuites')
        suite = root.find('testsuite')
        self.assertIsNotNone(suite)
        for key in ('tests', 'failures', 'errors', 'skipped'):
            self.assertEqual(root.get(key), suite.get(key))
        return suite

    def test_junit_success_and_filter_use_executed_tests(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'checks.zs'
            source.write_text('test "Keep <&> this":\n    require 2 + 2 == 4, "sum"\n'
                              'test "Skip this":\n    require false, "not selected"\n')
            report = root / 'report.xml'
            result = self.cli('test', source, '--filter', 'Keep', '--junit', report, '--json')
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            self.assertEqual(json.loads(result.stdout)['passed'], 1)
            suite = self.report(report)
            self.assertEqual(suite.get('tests'), '1')
            self.assertEqual(suite.get('failures'), '0')
            self.assertEqual(suite.get('errors'), '0')
            case = suite.find('testcase')
            self.assertEqual(case.get('name'), 'Keep <&> this')
            self.assertEqual(case.get('file'), str(source))

    def test_junit_assertion_and_runtime_errors_remain_distinct(self):
        with tempfile.TemporaryDirectory() as directory:
            report = Path(directory) / 'failed.xml'
            source = ('test "Assertion":\n    require false, "Expected <ready> & safe"\n'
                      'test "Arithmetic":\n    let value = 1 / 0\n    require value == 0, "never"\n')
            result = self.cli('test', '-', '--junit', report, '--json', source=source)
            self.assertEqual(result.returncode, 1, result.stderr)
            self.assertEqual(json.loads(result.stdout)['failed'], 2)
            suite = self.report(report)
            self.assertEqual(suite.get('tests'), '2')
            self.assertEqual(suite.get('failures'), '1')
            self.assertEqual(suite.get('errors'), '1')
            failure = suite.find('testcase/failure')
            self.assertEqual(failure.get('type'), 'E_REQUIRE')
            self.assertEqual(failure.get('message'), 'Expected <ready> & safe')
            self.assertIn('require false', failure.text)
            self.assertIsNotNone(suite.find('testcase/error'))

    def test_junit_reports_pre_execution_and_empty_selection_failures(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for index, (source, flags, expected) in enumerate((
                ('test "Invalid":\n    require unknown_name, "missing"\n', [], 'E_NAME'),
                ('test "Exists":\n    require true, "ok"\n',
                 ['--filter', 'absent', '--fail-if-empty'], 'E_TEST_EMPTY'),
            )):
                with self.subTest(code=expected):
                    report = root / f'failure-{index}.xml'
                    result = self.cli('test', '-', *flags, '--junit', report, '--json', source=source)
                    self.assertEqual(result.returncode, 1, result.stderr)
                    self.assertEqual(json.loads(result.stdout)['diagnostics'][0]['code'], expected)
                    suite = self.report(report)
                    self.assertEqual(suite.get('tests'), '1')
                    self.assertEqual(suite.get('errors'), '1')
                    self.assertEqual(suite.find('testcase/error').get('type'), expected)

    def test_junit_missing_source_still_creates_error_report(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            report = root / 'missing.xml'
            result = self.cli('test', root / 'missing.zs', '--junit', report, '--json')
            self.assertEqual(result.returncode, 1, result.stderr)
            self.assertEqual(self.report(report).find('testcase/error').get('type'), 'E_INPUT')

    def test_junit_list_conflict_creates_no_report(self):
        with tempfile.TemporaryDirectory() as directory:
            report = Path(directory) / 'listed.xml'
            result = self.cli('test', '-', '--list', '--junit', report,
                              source='test "Never runs":\n    require false, "fail"\n')
            self.assertEqual(result.returncode, 1)
            self.assertIn('--junit requires execution', result.stderr)
            self.assertFalse(report.exists())

    def test_junit_exclusive_output_and_missing_directory_are_structured(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            existing = root / 'existing.xml'
            existing.write_bytes(b'existing report\x00keep')
            for report in (existing, root / 'absent' / 'report.xml'):
                with self.subTest(report=report):
                    result = self.cli('test', '-', '--junit', report, '--json', source='')
                    self.assertEqual(result.returncode, 1, result.stderr)
                    self.assertEqual(json.loads(result.stdout)['diagnostics'][0]['code'], 'E_OUTPUT')
            self.assertEqual(existing.read_bytes(), b'existing report\x00keep')
            rejected = self.cli('test', '-', '--junit', existing, '--force', source='')
            self.assertEqual(rejected.returncode, 1)
            self.assertIn('unrecognized arguments: --force', rejected.stderr)
            self.assertEqual(existing.read_bytes(), b'existing report\x00keep')

    def test_junit_protects_every_project_input(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / 'project'
            init_project(root)
            data = root / 'input.json'
            contract = root / 'contract.json'
            proposals = root / 'proposals.json'
            data.write_text('{}')
            contract.write_text('{"type":"object"}')
            proposals.write_text('{}')
            inputs = [root / 'main.zs', root / 'tests.zs', root / 'lib/math.zs',
                      root / 'zensigil.json', data, contract, proposals]
            before = {path: path.read_bytes() for path in inputs}
            for output in inputs:
                with self.subTest(output=output.name):
                    result = self.cli('test', root, '--data', data, '--contract', contract,
                                      '--proposal-contract', proposals, '--junit', output, '--json')
                    self.assertEqual(result.returncode, 1, result.stderr)
                    error = json.loads(result.stdout)['diagnostics'][0]
                    self.assertEqual(error['code'], 'E_OUTPUT')
                    self.assertIn('different from every input file', error['message'])
            self.assertEqual({path: path.read_bytes() for path in inputs}, before)

    def test_junit_protects_hardlink_and_symlink_aliases(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'checks.zs'
            source.write_text('test "Safe":\n    require true, "yes"\n')
            before = source.read_bytes()
            aliases = [root / 'hardlink.xml', root / 'symlink.xml']
            try:
                os.link(source, aliases[0])
                aliases[1].symlink_to(source)
            except OSError:
                self.skipTest('filesystem links are unavailable')
            for alias in aliases:
                with self.subTest(alias=alias):
                    result = self.cli('test', source, '--junit', alias, '--json')
                    self.assertEqual(result.returncode, 1, result.stderr)
                    error = json.loads(result.stdout)['diagnostics'][0]
                    self.assertEqual(error['code'], 'E_OUTPUT')
                    self.assertIn('different from every input file', error['message'])
                    self.assertEqual(source.read_bytes(), before)
                    self.assertEqual(alias.read_bytes(), before)

    def test_junit_symlink_loop_returns_structured_output_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            report = Path(directory) / 'loop.xml'
            try:
                report.symlink_to(report.name)
            except OSError:
                self.skipTest('symlinks are unavailable')
            result = self.cli('test', '-', '--junit', report, '--json', source='')
            self.assertEqual(result.returncode, 1)
            self.assertNotIn('Traceback', result.stderr)
            self.assertEqual(json.loads(result.stdout)['diagnostics'][0]['code'], 'E_OUTPUT')
            self.assertTrue(report.is_symlink())

    def test_api_listing_preserves_distinct_module_test_locations_without_execution(self):
        case = 'test "Same label":\n    require false, "must not execute"\n'
        result = run_tests('use "a.zs" as a\nuse "b.zs" as b\n' + case,
                           modules={'a.zs': case, 'b.zs': case}, list_only=True)
        self.assertTrue(result['ok'], result)
        self.assertEqual(result['total'], 3)
        self.assertEqual(result['stats']['steps'], 0)
        self.assertEqual({(case['source_name'], case['name']) for case in result['tests']},
                         {('a.zs', 'Same label'), ('b.zs', 'Same label'), ('<program>', 'Same label')})
        self.assertTrue(all(case['ok'] is None for case in result['tests']))

    def test_junit_distinguishes_identical_labels_across_modules_and_project_sources(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / 'project'
            init_project(root)
            case = 'test "Same label":\n    require true, "yes"\n'
            (root / 'lib/a.zs').write_text('export fn value():\n    return 1\n' + case)
            (root / 'lib/b.zs').write_text('export fn value():\n    return 2\n' + case)
            imports = 'use "lib/a.zs" as a\nuse "lib/b.zs" as b\n'
            (root / 'main.zs').write_text(imports + case)
            (root / 'tests.zs').write_text(imports + case)
            report = root / 'project.xml'
            result = self.cli('test', root, '--junit', report, '--json')
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            cases = self.report(report).findall('testcase')
            self.assertEqual(len(cases), 4)
            identities = {(item.get('classname'), item.get('name')) for item in cases}
            self.assertEqual(len(identities), 4)
            self.assertEqual({item.get('file') for item in cases},
                             {'lib/a.zs', 'lib/b.zs', 'main.zs',
                              'tests.zs'})

    def test_repl_explicit_data_modules_callbacks_and_portable_reopening(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            data = root / 'input.json'
            modules = root / 'modules.json'
            saved = root / 'saved program.sigil.json'
            data.write_text(json.dumps({'amount': 21}))
            modules.write_text(json.dumps({'lib/math.zs': MATH}))
            before = (data.read_bytes(), modules.read_bytes())
            commands = ('use "lib/math.zs" as math\n'
                        'let callback = fn (value) => math.double(value)\n'
                        'callback(amount)\n'
                        'map([1, 2], math.double)\n'
                        f':save "{saved}"\n:quit\n')
            result = self.cli('repl', '--data', data, '--modules', modules, source=commands, cwd=root)
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            self.assertEqual([line for line in result.stdout.splitlines() if line.startswith('VALUE ')],
                             ['VALUE 42', 'VALUE [2, 4]'])
            reopened = self.cli('run', saved, '--json', cwd=root)
            self.assertEqual(reopened.returncode, 0, reopened.stderr + reopened.stdout)
            self.assertEqual(json.loads(reopened.stdout)['values'], [42, [2, 4]])
            self.assertEqual((data.read_bytes(), modules.read_bytes()), before)

    def test_repl_rejects_private_member_and_recovers_without_committing_cell(self):
        with tempfile.TemporaryDirectory() as directory:
            modules = Path(directory) / 'modules.json'
            modules.write_text(json.dumps({'lib/math.zs': MATH}))
            result = self.cli('repl', '--modules', modules,
                              source='use "lib/math.zs" as math\nmath.helper(3)\nmath.double(3)\n:quit\n')
            self.assertEqual(result.returncode, 1)
            self.assertIn('E_IMPORT', result.stderr)
            self.assertEqual(result.stdout.splitlines(), ['VALUE 6'])

    def test_repl_never_discovers_modules_from_working_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'hidden.zs').write_text(MATH)
            result = self.cli('repl', source='use "hidden.zs" as hidden\n1 + 2\n:quit\n', cwd=root)
            self.assertEqual(result.returncode, 1)
            self.assertIn('E_IMPORT', result.stderr)
            self.assertEqual(result.stdout.splitlines(), ['VALUE 3'])

    def test_repl_startup_rejects_invalid_data_and_module_maps(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            invalid = [('--data', '[]'), ('--data', '{"n":NaN}'),
                       ('--data', '{"n":1,"n":2}'), ('--modules', '[]'),
                       ('--modules', '{"../escape.zs":""}'), ('--modules', '{"lib.zs":42}')]
            for index, (flag, text) in enumerate(invalid):
                with self.subTest(flag=flag, text=text):
                    path = root / f'invalid-{index}.json'
                    path.write_text(text)
                    result = self.cli('repl', flag, path, source='1 + 2\n')
                    self.assertNotEqual(result.returncode, 0)
                    self.assertEqual(result.stdout, '')
                    self.assertIn('Cannot start REPL', result.stderr)
                    self.assertNotIn('Traceback', result.stderr)


if __name__ == '__main__':
    unittest.main()
