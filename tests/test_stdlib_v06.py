"""Explicit behavior and bounds for the eight 0.6 standard functions."""
import json
import unittest

from zensigil import run
from zensigil.checker import BUILTINS


class StandardLibraryV06Tests(unittest.TestCase):
    def value(self, expression, expected, prefix="", **kwargs):
        result = run(prefix + "\nemit " + expression, **kwargs)
        self.assertTrue(result["ok"], result)
        self.assertEqual(json.dumps(result["values"], sort_keys=True), json.dumps([expected], sort_keys=True))

    def error(self, expression, code, prefix="", **kwargs):
        result = run(prefix + '\nsay "discard"\nemit 1\nemit ' + expression, **kwargs)
        self.assertFalse(result["ok"], result)
        self.assertEqual(result["diagnostics"][0]["code"], code, result)
        self.assertEqual(result["values"], [])
        self.assertEqual(result["notes"], [])
        self.assertEqual(result["proposals"], [])

    def test_scan_returns_accumulations_without_initial(self):
        self.value("scan([1, 2, 3], 10, fn (total, x) => total + x)", [11, 13, 16])
        self.value('scan([1, 2, 3], [], fn (xs, x) => xs + [x])', [[1], [1, 2], [1, 2, 3]])
        self.value('scan([], false, fn (a, b) => a)', [])
        self.value('scan([false, 0, null], null, fn (a, b) => b)', [False, 0, None])
        self.value('scan([1, 2], 0, fn (a, b) => a + b * factor)', [2, 6], 'let factor = 2')
        self.error('scan([], abs, fn (a, b) => a)', 'E_VALUE')
        self.error('scan([1], 0, fn (a, b) => abs)', 'E_VALUE')

    def test_extrema_keep_first_tie_and_validate_all_keys(self):
        items = '[{id: "a", n: 3}, {id: "b", n: 1}, {id: "c", n: 1}, {id: "d", n: 3}]'
        self.value('min_by(' + items + ', fn (x) => x.n)', {'id': 'b', 'n': 1})
        self.value('max_by(' + items + ', fn (x) => x.n)', {'id': 'a', 'n': 3})
        self.value('min_by(["z", "A", "é"], fn (x) => x)', 'A')
        self.value('max_by(["z", "A", "é"], fn (x) => x)', 'é')
        self.value('min_by([1, 1.0], fn (x) => x)', 1)
        self.value('max_by([1.0, 1], fn (x) => x)', 1.0)
        for name in ('min_by', 'max_by'):
            self.value(name + '([], fn (x) => x)', None)
            self.value(name + '([null], fn (x) => 0)', None)
            for key in ('false', 'null', '[]', '{}', 'abs'):
                self.error(name + '([1], fn (x) => ' + key + ')', 'E_TYPE')
            self.error(name + '([1, "a"], fn (x) => x)', 'E_TYPE')
            self.error(name + '([1, 0], fn (x) => 1 / x)', 'E_ZERO')

    def test_sum_by_strict_order_and_overflow(self):
        self.value('sum_by([{n: 1}, {n: 2.5}], fn (x) => x.n)', 3.5)
        self.value('sum_by([], fn (x) => x)', 0)
        self.value('sum_by([1e16, -1e16, 1], fn (x) => x)', 1.0)
        self.error('sum_by([true], fn (x) => x)', 'E_TYPE')
        self.error('sum_by(["1"], fn (x) => x)', 'E_TYPE')
        self.error('sum_by([1], fn (x) => abs)', 'E_TYPE')
        self.error('sum_by([1e100, 1e100], fn (x) => x)', 'E_VALUE')

    def test_unique_by_uses_structural_type_aware_json_equality(self):
        self.value('unique_by([1, 1.0, true, false, 0, null, null], fn (x) => x)',
                   [1, True, False, 0, None])
        self.value('unique_by([{key: [1, false], id: "first"}, {key: [1.0, false], id: "later"}, {key: [true, 0], id: "other"}], fn (x) => x.key)',
                   [{'key': [1, False], 'id': 'first'}, {'key': [True, 0], 'id': 'other'}])
        self.value('unique_by([{a: 1, b: 2}, {b: 2, a: 1}], fn (x) => x)', [{'a': 1, 'b': 2}])
        self.value('unique_by([], fn (x) => x)', [])
        self.error('unique_by([1], fn (x) => abs)', 'E_VALUE')
        self.error('unique_by(range(1000), fn (x) => x)', 'E_LIMIT')

    def test_frequencies_are_string_only_and_preserve_key_order(self):
        self.value('frequencies(["b", "a", "b", "", "é", "__proto__"])',
                   {'b': 2, 'a': 1, '': 1, 'é': 1, '__proto__': 1})
        self.value('record_keys(frequencies(["b", "a", "b"]))', ['b', 'a'])
        self.value('frequencies([])', {})
        for value in ('true', '0', 'null', '{}', '[]'):
            self.error('frequencies([' + value + '])', 'E_TYPE')

    def test_flatten_removes_one_level_without_mutation(self):
        self.value('flatten([[], [1, false], [[2], null]])', [1, False, [2], None])
        self.value('flatten([])', [])
        self.value('flatten([[], []])', [])
        self.value('original', [[1], [2]], 'let original = [[1], [2]]\nlet changed = flatten(original)')
        for value in ('false', '0', 'null', '"abc"', '{}'):
            self.error('flatten([[],' + value + '])', 'E_TYPE')
        self.error('flatten([range(6000), range(6000)])', 'E_LIMIT')
        self.value('len(flatten([range(5000), range(5000)]))', 10000)

    def test_record_from_entries_is_explicit_and_rejects_duplicate_keys(self):
        self.value('record_from_entries([["b", false], ["a", 0], ["", null], ["é", [1]]])',
                   {'b': False, 'a': 0, '': None, 'é': [1]})
        self.value('record_keys(record_from_entries([["b", 1], ["a", 2]]))', ['b', 'a'])
        self.value('record_from_entries([])', {})
        self.error('record_from_entries([["a", 1], ["a", 2]])', 'E_DUPLICATE')
        for entry in ('[]', '["a"]', '["a", 1, 2]'):
            self.error('record_from_entries([' + entry + '])', 'E_VALUE')
        for entry in ('[false, 1]', '[0, 1]', '{key: "a", value: 1}'):
            self.error('record_from_entries([' + entry + '])', 'E_TYPE')
        self.error('record_from_entries([["callback", abs]])', 'E_VALUE')

    def test_callback_arity_is_checked_on_empty_lists(self):
        for name in ('min_by', 'max_by', 'sum_by', 'unique_by'):
            self.error(name + '([], fn () => 1)', 'E_ARITY')
            self.error(name + '([], get)', 'E_ARITY')
            self.error(name + '([], false)', 'E_TYPE')
        self.error('scan([], 0, fn (x) => x)', 'E_ARITY')
        self.error('scan([], 0, false)', 'E_TYPE')
        self.error('scan([], 0, get)', 'E_ARITY')

    def test_every_new_function_rejects_non_list_input_and_wrong_arity(self):
        calls = {'scan': '{}, 0, max', 'min_by': '{}, abs', 'max_by': '{}, abs',
                 'sum_by': '{}, abs', 'unique_by': '{}, abs', 'frequencies': '{}',
                 'flatten': '{}', 'record_from_entries': '{}'}
        for name, arguments in calls.items():
            self.error(name + '(' + arguments + ')', 'E_TYPE')
            self.error(name + '()', 'E_ARITY')
        self.assertEqual(BUILTINS['scan'], 3)
        self.assertEqual(BUILTINS['flatten'], 1)
        self.assertEqual(BUILTINS['range'], (1, 2, 3))

    def test_result_and_retained_key_budgets(self):
        self.error('scan(range(300), [], fn (xs, x) => xs + [x])', 'E_VALUE')
        self.error('unique_by(range(100), fn (x) => [x, range(1000)])', 'E_VALUE')
        self.error('scan(range(18), "", fn (a, x) => message)', 'E_VALUE',
                   data={'message': 'a' * 64000})

    def test_work_limits_and_rollback(self):
        self.error('scan([], initial, max)', 'E_LIMIT',
                   data={'initial': list(range(100))}, max_steps=50)
        for expression in ('scan(items, 0, max)', 'min_by(items, abs)', 'max_by(items, abs)',
                           'sum_by(items, abs)', 'unique_by(items, abs)',
                           'frequencies(words)', 'flatten(batches)', 'record_from_entries(pairs)'):
            self.error(expression, 'E_LIMIT', data={'items': list(range(100)),
                       'words': ['x'] * 100, 'batches': [[1]] * 100,
                       'pairs': [[str(i), i] for i in range(100)]}, max_steps=50)


if __name__ == '__main__':
    unittest.main()
