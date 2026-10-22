"""Public API regressions for bounded collection work and source diagnostics."""
import copy
import json
import unittest

from zensigil import check, run, test as run_tests
from zensigil.errors import SigilError
from zensigil.runtime import Runtime
from zensigil.syntax import parse


class RuntimeStabilityTests(unittest.TestCase):
    def error(self, source, code, data=None, **kwargs):
        result = run(source, data, **kwargs)
        self.assertFalse(result['ok'], result)
        self.assertEqual(result['diagnostics'][0]['code'], code, result)
        for output in ('values', 'notes', 'proposals'):
            self.assertEqual(result[output], [], result)
        return result['diagnostics'][0]

    def value(self, source, expected, data=None, **kwargs):
        result = run(source, data, **kwargs)
        self.assertTrue(result['ok'], result)
        self.assertEqual(result['values'], expected)
        return result

    def test_map_rejects_first_non_json_result_before_later_callback(self):
        source = ('fn transform(n):\n'
                  '    return choose n == 0 then abs otherwise 1 / 0\n'
                  'emit map([0, 1], transform)')
        error = self.error(source, 'E_VALUE')
        self.assertEqual((error['line'], error['column']), (3, 6))
        self.assertEqual(error['call_trace'][-1]['function'], 'map')
        self.assertIn('Only JSON values', error['message'])

    def test_map_node_limit_stops_before_a_later_callback(self):
        source = ('fn transform(n):\n'
                  '    return choose n < 20 then range(1000) otherwise 1 / 0\n'
                  'emit map(range(21), transform)')
        error = self.error(source, 'E_VALUE')
        self.assertIn('20,000-node', error['message'])

    def test_map_utf8_limit_stops_before_a_later_callback(self):
        source = ('fn transform(n):\n'
                  '    return choose n < 20 then ' + json.dumps('é' * 30000, ensure_ascii=False) + ' otherwise 1 / 0\n'
                  'emit map(range(21), transform)')
        self.error(source, 'E_VALUE')

    def test_map_counts_added_container_nesting(self):
        nested = 1
        for _ in range(32):
            nested = [nested]
        source = ('let deep = parse_json(' + json.dumps(json.dumps(nested)) + ')\n'
                  'emit map([0], fn (_n) => deep)')
        self.error(source, 'E_VALUE')

    def test_map_result_node_boundary(self):
        self.value('emit len(map(range(9999), fn (n) => [n]))', [9999])
        self.error('emit map(range(10000), fn (n) => [n])', 'E_VALUE')

    def test_sort_by_rejects_first_invalid_key_before_later_callback(self):
        for key in ('false', 'null', '[]', '{}', 'abs'):
            with self.subTest(key=key):
                source = ('fn key(n):\n'
                          '    return choose n == 0 then ' + key + ' otherwise 1 / 0\n'
                          'emit sort_by([0, 1], key)')
                self.error(source, 'E_TYPE')

    def test_sort_by_rejects_first_mixed_key_before_later_callback(self):
        source = ('fn key(n):\n'
                  '    return choose n == 0 then 1 otherwise choose n == 1 then "a" otherwise 1 / 0\n'
                  'emit sort_by([0, 1, 2], key)')
        self.error(source, 'E_TYPE')

    def test_sort_by_retained_keys_have_utf8_budget(self):
        # Each key is valid alone. Their retained combined representation is not.
        source = ('let key = fn (n) => text(n) + "' + 'x' * 1000 + '"\n'
                  'emit len(sort_by(range(1100), key))')
        error = self.error(source, 'E_VALUE')
        self.assertIn('text exceeds', error['message'])

    def test_sort_by_keeps_stability_and_numeric_category(self):
        self.value('emit sort_by(items, fn (x) => x.rank)', [[
            {'id': 'c', 'rank': 0}, {'id': 'a', 'rank': 1}, {'id': 'b', 'rank': 1.0}
        ]], {'items': [{'id': 'a', 'rank': 1}, {'id': 'b', 'rank': 1.0}, {'id': 'c', 'rank': 0}]})

    def test_sort_by_empty_input_still_checks_callback_arity(self):
        self.error('emit sort_by([], fn () => 1)', 'E_ARITY')
        self.value('emit sort_by([], fn (x) => x)', [[]])

    def test_expanding_builders_count_nodes_before_retention(self):
        self.value('emit len(zip(range(6666), range(6666)))', [6666])
        self.error('emit zip(range(6667), range(6667))', 'E_VALUE')
        self.value('emit len(enumerate(range(3999)))', [3999])
        self.error('emit enumerate(range(4000))', 'E_VALUE')
        self.value('emit len(record_entries(fields))', [3999],
                   {'fields': {str(n): n for n in range(3999)}})
        self.error('emit record_entries(fields)', 'E_VALUE',
                   {'fields': {str(n): n for n in range(4000)}})

    def test_record_merge_counts_only_final_values_and_preserves_order(self):
        # The right record replaces a large field. Counting both versions would
        # reject this valid result. This also verifies input immutability.
        data = {'left': {'first': list(range(9000)), 'last': 2},
                'right': {'first': 1, 'new': list(range(9000))}}
        original = copy.deepcopy(data)
        self.value('let merged = record_merge(left, right)\n'
                   'emit record_keys(merged)\nemit merged.first\nemit len(merged.new)',
                   [['first', 'last', 'new'], 1, 9000], data)
        self.assertEqual(data, original)

    def test_record_merge_checks_combined_node_and_text_limits(self):
        prefix = ('let a = record_from_entries(map(range(5000), fn (n) => [text(n), n]))\n'
                  'let b = record_from_entries(map(range(5000, 10000), fn (n) => [text(n), n]))\n')
        self.value(prefix + 'emit len(a)\nemit len(b)', [5000, 5000], max_steps=1000000)
        self.error(prefix + 'emit record_merge(a, b)', 'E_VALUE', max_steps=1000000)
        source = ('let a = {first: "' + 'x' * 60000 + '"}\n'
                  'var merged = {}\n'
                  'for n in range(18):\n'
                  '    set merged = record_merge(merged, record_from_entries([[text(n), a.first]]))\n'
                  'emit merged')
        self.error(source, 'E_VALUE')

    def test_nested_copy_work_consumes_execution_steps(self):
        data = {'items': [list(range(100))] * 10}
        for expression in ('map(items, fn (x) => x)', 'zip(items, items)',
                           'enumerate(items)', 'record_entries({items: items})',
                           'record_merge({}, {items: items})'):
            with self.subTest(expression=expression):
                self.error('emit ' + expression, 'E_LIMIT', data, max_steps=100)

    def test_collection_failures_discard_all_prior_effects(self):
        prefix = 'say "before"\nemit 7\npropose review(id: "before")\n'
        self.error(prefix + 'emit map([1], fn (n) => abs)', 'E_VALUE')
        self.error(prefix + 'emit sort_by([1], fn (n) => false)', 'E_TYPE')

    def test_callback_failure_keeps_imported_source_and_trace(self):
        module = 'export fn bad(n):\n    return 1 / n\n'
        error = self.error('use "math.zs" as math\nemit map([0], math.bad)', 'E_ZERO',
                           modules={'math.zs': module})
        self.assertEqual(error['source_name'], 'math.zs')
        self.assertEqual(error['source_line'], '    return 1 / n')
        self.assertEqual([frame['function'] for frame in error['call_trace']], ['math.zs::bad', 'map'])


class ParserDiagnosticTests(unittest.TestCase):
    def diagnostic(self, source, code='E_SYNTAX', **kwargs):
        result = check(source, **kwargs)
        self.assertFalse(result['ok'], result)
        error = result['diagnostics'][0]
        self.assertEqual(error['code'], code, error)
        return error

    def test_unclosed_delimiter_points_to_opening(self):
        error = self.diagnostic('emit [\n    1,\n')
        self.assertEqual((error['line'], error['column']), (1, 6))
        self.assertEqual(error['source_line'], 'emit [')
        self.assertIn("add ']'", error['message'])

    def test_unclosed_nested_delimiter_points_to_innermost_opening(self):
        error = self.diagnostic('emit [\n    {x: (1\n')
        self.assertEqual((error['line'], error['column']), (2, 9))
        self.assertIn("add ')'", error['message'])

    def test_mismatched_delimiter_identifies_both_ends(self):
        error = self.diagnostic('emit [\n    1)')
        self.assertEqual((error['line'], error['column']), (2, 6))
        self.assertIn("Expected ']'", error['message'])
        self.assertIn('line 1, column 6', error['message'])

    def test_unmatched_closer_stays_at_closing_character(self):
        error = self.diagnostic('emit 1]')
        self.assertEqual((error['line'], error['column']), (1, 7))
        self.assertIn("Unmatched ']'", error['message'])

    def test_imported_delimiter_error_has_module_source(self):
        error = self.diagnostic('use "broken.zs"',
                                modules={'broken.zs': 'export fn bad():\n    return [\n'})
        self.assertEqual(error['source_name'], 'broken.zs')
        self.assertEqual((error['line'], error['column']), (2, 12))
        self.assertEqual(error['source_line'], '    return [')

    def test_assignment_hint_uses_current_binding_syntax(self):
        error = self.diagnostic('answer = 42')
        for word in ('let name', 'var name', 'set name'):
            self.assertIn(word, error['message'])

    def test_unexpected_indent_and_orphan_otherwise_are_specific(self):
        error = self.diagnostic('    emit 1', 'E_INDENT')
        self.assertIn('Unexpected indentation', error['message'])
        error = self.diagnostic('otherwise:\n    emit 1')
        self.assertIn("matching 'when'", error['message'])

    def test_statement_hint_includes_current_language_forms(self):
        error = self.diagnostic('42')
        for word in ('emit', 'var', 'set', 'while', 'test', 'use', 'export'):
            self.assertIn(word, error['message'])

    def test_valid_delimiters_comments_and_crlf_still_parse(self):
        source = 'emit [\r\n    {x: "]"}, # } ignored\r\n    (1 + 2),\r\n]\r\n'
        result = run(source)
        self.assertTrue(result['ok'], result)
        self.assertEqual(result['values'], [[{'x': ']'}, 3]])
        self.assertEqual(len(parse(source)), 1)


class StepLimitTests(unittest.TestCase):
    def test_invalid_limits_return_structured_errors_without_execution(self):
        invalid = (True, False, None, '100', 1.0, float('inf'), float('nan'),
                   -1, 0, 1000001, 10 ** 100)
        for limit in invalid:
            for api, source in ((run, 'emit 1'), (run_tests, 'test "case":\n    require true, "ok"')):
                with self.subTest(limit=repr(limit), api=api.__name__):
                    result = api(source, max_steps=limit)
                    self.assertFalse(result['ok'], result)
                    self.assertEqual(result['diagnostics'][0]['code'], 'E_INPUT')
                    for output in ('values', 'notes', 'proposals'):
                        self.assertEqual(result[output], [])

    def test_empty_and_list_only_paths_still_validate_limits(self):
        self.assertEqual(run('', max_steps=None)['diagnostics'][0]['code'], 'E_INPUT')
        self.assertEqual(run_tests('', max_steps=None)['diagnostics'][0]['code'], 'E_INPUT')
        result = run_tests('test "case":\n    require true, "ok"', list_only=True, max_steps=float('nan'))
        self.assertEqual(result['diagnostics'][0]['code'], 'E_INPUT')

    def test_runtime_constructor_also_validates_limits(self):
        with self.assertRaises(SigilError) as caught:
            Runtime((), {}, max_steps='100')
        self.assertEqual(caught.exception.code, 'E_INPUT')

    def test_valid_boundaries_and_actual_exhaustion(self):
        self.assertTrue(run('', max_steps=1)['ok'])
        self.assertTrue(run('emit 1', max_steps=1000000)['ok'])
        result = run('emit 1', max_steps=1)
        self.assertFalse(result['ok'])
        self.assertEqual(result['diagnostics'][0]['code'], 'E_LIMIT')

    def test_integer_subclasses_are_not_silently_accepted(self):
        class CustomLimit(int):
            pass
        result = run('', max_steps=CustomLimit(100))
        self.assertEqual(result['diagnostics'][0]['code'], 'E_INPUT')


if __name__ == '__main__':
    unittest.main()
