"""Independent XML parsing verifies report status, escaping and failure accounting."""
import copy
import unittest
import xml.etree.ElementTree as ET

from zensigil import test as run_tests
from zensigil.reports import junit_xml


class JUnitReportTests(unittest.TestCase):
    def document(self, result, name='ZenSigil'):
        text = junit_xml(result, name)
        self.assertTrue(text.startswith("<?xml"))
        root = ET.fromstring(text)
        self.assertEqual(root.tag, 'testsuites')
        suite = root.find('testsuite')
        self.assertIsNotNone(suite)
        for field in ('tests', 'failures', 'errors', 'skipped'):
            self.assertEqual(root.get(field), suite.get(field))
        self.assertNotIn('time=', text)
        self.assertNotIn('timestamp=', text)
        return root, suite

    def test_passes_have_no_fabricated_timing(self):
        result = run_tests('test "Arithmetic":\n    require 2 + 2 == 4, "sum"\n')
        _, suite = self.document(result)
        self.assertEqual(suite.attrib, {'name': 'ZenSigil', 'tests': '1', 'failures': '0', 'errors': '0', 'skipped': '0'})
        self.assertEqual(suite.find('testcase').get('name'), 'Arithmetic')
        self.assertEqual(list(suite.find('testcase')), [])

    def test_assertion_failures_and_runtime_errors_are_distinct(self):
        result = run_tests('test "False":\n    require false, "assertion"\ntest "Zero":\n    require 1 / 0 == 1, "division"\n')
        _, suite = self.document(result)
        self.assertEqual(suite.get('tests'), '2')
        self.assertEqual(suite.get('failures'), '1')
        self.assertEqual(suite.get('errors'), '1')
        first, second = suite.findall('testcase')
        self.assertEqual(first.find('failure').get('type'), 'E_REQUIRE')
        self.assertEqual(second.find('error').get('type'), 'E_ZERO')
        self.assertIn('1 / 0', second.find('error').text)

    def test_identical_test_labels_keep_module_and_aggregate_source_identity(self):
        result = run_tests('use "a.zs" as a\nuse "b.zs" as b\n', modules={
            'a.zs': 'test "Same label":\n    require true, "a"\n',
            'b.zs': 'test "Same label":\n    require true, "b"\n'})
        self.assertTrue(result['ok'], result)
        _, suite = self.document(result)
        cases = suite.findall('testcase')
        self.assertEqual([case.get('name') for case in cases], ['Same label', 'Same label'])
        self.assertEqual([case.get('file') for case in cases], ['a.zs', 'b.zs'])
        self.assertEqual(len({(case.get('classname'), case.get('name')) for case in cases}), 2)

        # Project reports attach the entry source as source_file; keep it as
        # context without replacing the module's own logical filename.
        aggregated = dict(result, tests=[dict(case, source_file=entry)
                                        for entry in ('first.zs', 'second.zs')
                                        for case in result['tests']])
        _, suite = self.document(aggregated)
        cases = suite.findall('testcase')
        self.assertEqual([case.get('file') for case in cases], ['a.zs', 'b.zs', 'a.zs', 'b.zs'])
        self.assertEqual(len({(case.get('classname'), case.get('name')) for case in cases}), 4)

        _, suite = self.document({'ok': True, 'tests': [
            {'name': 'Root', 'ok': True, 'source_name': '<program>', 'source_file': 'root.zs'}]})
        self.assertEqual(suite.find('testcase').get('file'), 'root.zs')
        self.assertEqual(suite.find('testcase').get('classname'), 'ZenSigil:root.zs')

    def test_pre_discovery_and_missing_diagnostic_failures_stay_red(self):
        for result in (run_tests('broken source'),
                       {'ok': False, 'diagnostics': [{'code': 'E_INPUT', 'message': 'Could not read source.'}]},
                       {'ok': False, 'tests': [], 'diagnostics': []}):
            _, suite = self.document(result)
            self.assertEqual(suite.get('tests'), '1')
            self.assertEqual(suite.get('errors'), '1')
            self.assertEqual(suite.get('failures'), '0')
            self.assertIsNotNone(suite.find('testcase/error'))

    def test_listing_is_not_reported_as_passing_tests(self):
        listed = run_tests('test "Never run":\n    require false, "bad"', list_only=True)
        with self.assertRaisesRegex(ValueError, 'list-only'):
            junit_xml(listed)
        with self.assertRaisesRegex(ValueError, 'list-only'):
            junit_xml({'ok': True, 'listed': True, 'tests': [], 'diagnostics': []})
        _, suite = self.document(run_tests('emit 1'))
        self.assertEqual(suite.get('tests'), '0')

    def test_xml_escaping_unicode_and_invalid_control_replacement(self):
        result = {'ok': False, 'tests': [{'name': 'Name <&" 🌱\x00\ud800', 'ok': False,
                   'source_file': '/tmp/"<&\x01.zs', 'diagnostics': [{'code': 'E_REQUIRE',
                   'message': 'wanted <x> & "y"\x00\uffff', 'source_line': 'require false, "<bad>"',
                   'line': 2, 'column': 3}]}], 'diagnostics': []}
        original = copy.deepcopy(result)
        _, suite = self.document(result, 'Suite <&"\x02')
        case = suite.find('testcase')
        self.assertEqual(suite.get('name'), 'Suite <&"\ufffd')
        self.assertEqual(case.get('name'), 'Name <&" 🌱\ufffd\ufffd')
        self.assertEqual(case.get('file'), '/tmp/"<&\ufffd.zs')
        self.assertEqual(case.find('failure').get('message'), 'wanted <x> & "y"\ufffd\ufffd')
        self.assertEqual(result, original)

    def test_aggregate_diagnostics_are_not_double_counted(self):
        diagnostic = {'code': 'E_REQUIRE', 'message': 'bad', 'line': 2, 'column': 1}
        result = {'ok': False, 'tests': [
            {'name': 'A', 'ok': False, 'source_file': 'a.zs', 'diagnostics': [dict(diagnostic)]},
            {'name': 'B', 'ok': False, 'source_file': 'b.zs', 'diagnostics': [dict(diagnostic)]}],
            'diagnostics': [dict(diagnostic, project_source='a.zs'),
                            dict(diagnostic, project_source='b.zs'),
                            {'code': 'E_IMPORT', 'message': 'missing', 'project_source': 'c.zs'}]}
        _, suite = self.document(result)
        self.assertEqual(suite.get('tests'), '3')
        self.assertEqual(suite.get('failures'), '2')
        self.assertEqual(suite.get('errors'), '1')
        self.assertEqual(suite.findall('testcase')[-1].get('file'), 'c.zs')

    def test_aggregate_counts_do_not_trust_summary_totals(self):
        result = {'ok': True, 'total': 800, 'passed': 800, 'failed': 0,
                  'tests': [{'name': 'actual', 'ok': True, 'diagnostics': []}], 'diagnostics': []}
        _, suite = self.document(result)
        self.assertEqual(suite.get('tests'), '1')
        result['ok'] = False
        _, suite = self.document(result)
        self.assertEqual(suite.get('tests'), '2')
        self.assertEqual(suite.get('errors'), '1')

    def test_failed_case_without_diagnostics_gets_error(self):
        _, suite = self.document({'ok': False, 'tests': [{'name': 'Unknown', 'ok': False}], 'diagnostics': []})
        self.assertEqual(suite.get('errors'), '1')
        self.assertEqual(suite.find('testcase/error').get('type'), 'E_TEST')

    def test_call_trace_and_contract_path_are_preserved(self):
        result = {'ok': False, 'tests': [], 'diagnostics': [{'code': 'E_INPUT', 'message': 'wrong type',
                  'data_path': '$.value', 'source_file': 'lib.zs', 'line': 5, 'column': 9,
                  'call_trace': [{'function': 'f', 'source_name': 'main.zs', 'line': 2, 'column': 4}]}]}
        _, suite = self.document(result)
        text = suite.find('testcase/error').text
        self.assertIn('$.value', text)
        self.assertIn('lib.zs:5:9', text)
        self.assertIn('Called f at main.zs:2:4', text)

    def test_invalid_shapes_and_report_bounds_are_rejected(self):
        for result in (None, [], {}, {'ok': 1}, {'ok': True, 'tests': {}},
                       {'ok': True, 'tests': [{'name': 'x', 'ok': 1}]},
                       {'ok': False, 'diagnostics': ['bad']},
                       {'ok': False, 'diagnostics': [{'code': 1, 'message': 'bad'}]}):
            with self.subTest(result=result), self.assertRaises(ValueError):
                junit_xml(result)
        with self.assertRaisesRegex(ValueError, '10,000'):
            junit_xml({'ok': True, 'tests': [{'name': 'x', 'ok': True}] * 10001})
        with self.assertRaisesRegex(ValueError, '8 MiB'):
            junit_xml({'ok': True, 'tests': [{'name': '&' * 65536, 'ok': True}] * 30})


if __name__ == '__main__':
    unittest.main()
