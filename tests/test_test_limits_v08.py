"""Test reports must remain bounded after source and trace resolution."""
import json
import unittest
from unittest.mock import patch

from zensigil import test as run_tests
from zensigil.testing import MAX_TEST_RESULT_BYTES, TestResultBudget, bound_test_result


def encoded_size(value):
    return len(json.dumps(value, ensure_ascii=True, separators=(',', ':')).encode('utf-8'))


class TestOutputLimits(unittest.TestCase):
    def assert_limited(self, result):
        self.assertFalse(result['ok'], result)
        self.assertTrue(result['stopped_early'])
        self.assertLessEqual(encoded_size(result), MAX_TEST_RESULT_BYTES)
        self.assertEqual(result['tests'][-1]['diagnostics'][0]['code'], 'E_TEST_LIMIT')
        self.assertEqual(result['tests'][-1]['ok'], False)
        self.assertEqual(result['failed'], sum(case['ok'] is False for case in result['tests']))
        self.assertEqual(result['total'], len(result['tests']))
        self.assertEqual(result['diagnostics'], [item for case in result['tests'] for item in case['diagnostics']])

    def test_many_large_failures_stop_before_report_expansion(self):
        source = ('fn fail():\n    require false, "' + ('x' * 16000) + '"\n    return 0\n' +
                  ''.join(f'test "Case {n}":\n    require fail() == 0, "No"\n' for n in range(100)))
        result = run_tests(source)
        self.assert_limited(result)
        self.assertLess(result['total'], 100)
        self.assertLess(result['stats']['steps'], 800)
        self.assertEqual(result['tests'][0]['name'], 'Case 0')
        self.assertEqual(result['tests'][0]['diagnostics'][0]['message'], 'x' * 16000)

    def test_imported_source_and_trace_are_measured_after_resolution(self):
        module = ('export fn fail():\n    require false, "' + ('x' * 16000) + '"\n    return 0\n')
        source = 'use "fail.zs"\n' + ''.join(f'test "Case {n}":\n    require fail() == 0, "No"\n' for n in range(100))
        result = run_tests(source, modules={'fail.zs': module})
        self.assert_limited(result)
        self.assertEqual(result['tests'][0]['diagnostics'][0]['source_name'], 'fail.zs')
        self.assertIn('x' * 16000, result['tests'][0]['diagnostics'][0]['source_line'])

    def test_ascii_json_escaping_counts_toward_budget(self):
        module = ('export fn fail():\n    require false, "' + ('🌱' * 3500) + '"\n    return 0\n')
        source = 'use "fail.zs"\n' + ''.join(f'test "Case {n}":\n    require fail() == 0, "No"\n' for n in range(100))
        result = run_tests(source, modules={'fail.zs': module})
        self.assert_limited(result)
        self.assertEqual(result['tests'][0]['diagnostics'][0]['message'], '🌱' * 3500)

    def test_small_failure_keeps_complete_source_and_call_trace(self):
        result = run_tests('fn fail():\n    require false, "Expected a value."\n    return 0\n'
                           'test "One":\n    require fail() == 0, "No"\n')
        self.assertFalse(result['ok'])
        self.assertFalse(result['stopped_early'])
        self.assertEqual(result['failed'], 1)
        error = result['diagnostics'][0]
        self.assertEqual(error['source_line'], '    require false, "Expected a value."')
        self.assertEqual(error['call_trace'][0]['source_line'], '    require fail() == 0, "No"')

    def test_list_only_reports_an_explicit_limit_without_execution(self):
        source = ''.join(f'test "Case {n} name":\n    require false, "Must not run"\n' for n in range(50))
        with patch('zensigil.testing.MAX_TEST_RESULT_BYTES', 8192):
            result = run_tests(source, list_only=True)
        self.assert_limited(result)
        self.assertEqual(result['stats']['steps'], 0)
        self.assertEqual(result['passed'], 0)
        self.assertTrue(all(case['ok'] is None for case in result['tests'][:-1]))
        self.assertLessEqual(encoded_size(result), 8192)

    def test_budget_counts_top_level_diagnostic_copy(self):
        case = {'name': 'Failure', 'source_name': '<program>', 'ok': False, 'steps': 1,
                'diagnostics': [{'code': 'E_REQUIRE', 'message': 'x' * 3000}]}
        with patch('zensigil.testing.MAX_TEST_RESULT_BYTES', 10000):
            budget = TestResultBudget()
            result = budget.add(case)
        self.assertLess(encoded_size(case), 10000 - 4096)
        self.assertTrue(budget.stopped)
        self.assertEqual(result['diagnostics'][0]['code'], 'E_TEST_LIMIT')

    def test_final_envelope_guard_catches_unanticipated_metadata(self):
        result = bound_test_result({'version': '0.8.0', 'mode': 'test', 'metadata': 'x' * MAX_TEST_RESULT_BYTES})
        self.assert_limited(result)

    def test_execution_limit_is_also_marked_as_stopped_early(self):
        result = run_tests('test "Loop":\n    while true:\n        let item = 1\n'
                           'test "Later":\n    require true, "ok"\n', max_steps=10)
        self.assertFalse(result['ok'])
        self.assertTrue(result['stopped_early'])
        self.assertEqual(result['diagnostics'][0]['code'], 'E_LIMIT')
        self.assertEqual(result['total'], 1)


if __name__ == '__main__':
    unittest.main()
