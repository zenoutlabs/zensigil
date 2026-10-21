"""Behavioral acceptance cases for the 0.5 collection additions."""
import json
import unittest

from zensigil import run
from zensigil.checker import BUILTINS


IDENTITY = "fn identity(item):\n    return item\n"
PAIR = "fn pair(item):\n    return [item, item]\n"
POSITIVE = "fn positive(item):\n    return item > 0\n"


class StandardLibraryV05Tests(unittest.TestCase):
    def value(self, expression, expected, prefix="", **kwargs):
        result = run(prefix + "\nemit " + expression, **kwargs)
        self.assertTrue(result["ok"], result.get("diagnostics"))
        # JSON spelling distinguishes false/0 and true/1 unlike Python equality.
        self.assertEqual(json.dumps(result["values"], sort_keys=True),
                         json.dumps([expected], sort_keys=True))

    def error(self, expression, code, prefix="", **kwargs):
        result = run(prefix + '\nsay "Discard me"\nemit 42\nemit ' + expression, **kwargs)
        self.assertFalse(result["ok"], result)
        self.assertEqual(result["diagnostics"][0]["code"], code, result)
        for field in ("values", "notes", "proposals"):
            self.assertEqual(result[field], [])

    def test_grouping_order_and_mixed_values(self):
        prefix = "fn kind(item):\n    return item.kind\n"
        items = '[{kind: "b", n: 1}, {kind: "a", n: 2}, {kind: "b", n: 3}]'
        self.value("group_by(" + items + ", kind)",
                   {"b": [{"kind": "b", "n": 1}, {"kind": "b", "n": 3}],
                    "a": [{"kind": "a", "n": 2}]}, prefix)
        self.value("record_keys(group_by(" + items + ", kind))", ["b", "a"], prefix)
        self.value('group_by([false, 0, null, [], {}, true, 1], type_of)',
                   {"boolean": [False, True], "number": [0, 1], "null": [None],
                    "list": [[]], "record": [{}]})
        self.value('group_by(["", "é", "", "__proto__"], identity)',
                   {"": ["", ""], "é": ["é"], "__proto__": ["__proto__"]}, IDENTITY)

    def test_counts_preserve_first_key_order(self):
        self.value('count_by(["b", "a", "b"], identity)', {"b": 2, "a": 1}, IDENTITY)
        self.value('record_keys(count_by(["b", "a", "b"], identity))', ["b", "a"], IDENTITY)
        self.value('count_by([false, 0, true, 1, null], type_of)',
                   {"boolean": 2, "number": 2, "null": 1})
        for function in ("group_by", "count_by"):
            self.value(function + "([], identity)", {}, IDENTITY)
            for item in ("0", "false", "null", "[]", "{}"):
                with self.subTest(function=function, item=item):
                    self.error(function + "([" + item + "], identity)", "E_TYPE", IDENTITY)

    def test_partition_has_stable_named_halves(self):
        self.value("partition([2, -1, 0, 3, -2], positive)",
                   {"matched": [2, 3], "unmatched": [-1, 0, -2]}, POSITIVE)
        self.value("partition([], positive)", {"matched": [], "unmatched": []}, POSITIVE)
        self.value("partition([false, true, false], identity)",
                   {"matched": [True], "unmatched": [False, False]}, IDENTITY)
        for item in ("0", "1", "null", '"yes"'):
            self.error("partition([" + item + "], identity)", "E_TYPE", IDENTITY)

    def test_flat_map_flattens_exactly_one_level(self):
        self.value("flat_map([1, null, false], pair)", [1, 1, None, None, False, False], PAIR)
        self.value("flat_map([[], [1], [[2]]], identity)", [1, [2]], IDENTITY)
        self.value("flat_map([], identity)", [], IDENTITY)
        self.value("flat_map([[], []], identity)", [], IDENTITY)
        for item in ("0", "false", "null", '"abc"', "{}"):
            self.error("flat_map([" + item + "], identity)", "E_TYPE", IDENTITY)

    def test_find_and_find_index_short_circuit(self):
        predicate = 'fn positive(item):\n    require item != 0, "Reached zero"\n    return item > 0\n'
        self.value("find([-1, 2, 0], positive, null)", 2, predicate)
        self.value("find_index([-1, 2, 0], positive)", 1, predicate)
        self.value('find([-3, -1], positive, {missing: true})', {"missing": True}, predicate)
        self.value("find_index([-3, -1], positive)", -1, predicate)
        self.value("find([], positive, false)", False, predicate)
        self.value("find_index([], positive)", -1, predicate)
        self.value("find([false, true], identity, null)", True, IDENTITY)
        self.value("find_index([false, true], identity)", 1, IDENTITY)
        self.value('find([false, 0, null], is_boolean, "absent")', False,
                   'fn is_boolean(item):\n    return type_of(item) == "boolean"\n')
        self.value('find([false, 0, null], is_null, "absent")', None,
                   'fn is_null(item):\n    return item == null\n')
        self.error("find([-1, 0], positive, null)", "E_REQUIRE", predicate)
        self.error("find_index([-1, 0], positive)", "E_REQUIRE", predicate)
        self.error("find([0], identity, null)", "E_TYPE", IDENTITY)
        self.error("find_index([0], identity)", "E_TYPE", IDENTITY)
        self.error("find([true], identity, 1 / 0)", "E_ZERO", IDENTITY)
        self.error("find([true], identity, identity)", "E_VALUE", IDENTITY)

    def test_callback_type_and_arity_are_checked_on_empty_input(self):
        prefix = "fn needs_two(left, right):\n    return left\n"
        for function in ("group_by", "count_by", "partition", "flat_map", "find", "find_index"):
            suffix = ", null" if function == "find" else ""
            with self.subTest(function=function):
                self.error(function + "([], false" + suffix + ")", "E_TYPE")
                self.error(function + "([], needs_two" + suffix + ")", "E_ARITY", prefix)
                self.error(function + "([], get" + suffix + ")", "E_ARITY")
                self.error(function + "({}, type_of" + suffix + ")", "E_TYPE")

    def test_take_drop_chunk_preserve_order_and_mixed_types(self):
        for expression, expected in [
            ("take([false, 0, null], 2)", [False, 0]),
            ("drop([false, 0, null], 1)", [0, None]),
            ("take([1, 2], 0)", []), ("drop([1, 2], 0)", [1, 2]),
            ("take([1, 2], 100000000000000000000)", [1, 2]),
            ("drop([1, 2], 100000000000000000000)", []),
            ("chunk([1, 2, 3, 4, 5], 2)", [[1, 2], [3, 4], [5]]),
            ("chunk([false, 0], 100000000000000000000)", [[False, 0]]),
            ("chunk([1, 2], 1)", [[1], [2]]),
            ("take([], 3)", []), ("drop([], 3)", []), ("chunk([], 3)", []),
        ]:
            with self.subTest(expression=expression):
                self.value(expression, expected)
        for function in ("take", "drop", "chunk"):
            for amount, code in [("true", "E_TYPE"), ("2.0", "E_TYPE"), ('"2"', "E_TYPE"), ("-1", "E_VALUE")]:
                self.error(function + "([], " + amount + ")", code)
            self.error(function + '("abc", 1)', "E_TYPE")
        self.error("chunk([], 0)", "E_VALUE")

    def test_record_projection_order_missing_duplicate_keys_and_immutability(self):
        self.value('record_pick({z: false, a: 0, b: null}, ["a", "missing", "z", "a"])',
                   {"z": False, "a": 0})
        self.value('record_keys(record_pick({z: 1, a: 2}, ["a", "z"]))', ["z", "a"])
        self.value('record_omit({z: false, a: 0, b: null}, ["a", "missing", "a"])',
                   {"z": False, "b": None})
        self.value('record_keys(record_omit({z: 1, a: 2, b: 3}, ["a"]))', ["z", "b"])
        for expression, expected in [('record_pick({a: 1}, [])', {}),
                                     ('record_omit({a: 1}, [])', {"a": 1}),
                                     ('record_pick({}, ["missing"])', {}),
                                     ('record_omit({}, ["missing"])', {})]:
            self.value(expression, expected)
        self.value("original", {"a": [1], "b": 2},
                   'let original = {a: [1], b: 2}\nlet picked = record_pick(original, ["a"])\nlet omitted = record_omit(original, ["b"])')
        for function in ("record_pick", "record_omit"):
            self.error(function + "({}, [false])", "E_TYPE")
            self.error(function + "({}, [0])", "E_TYPE")
            self.error(function + '({}, "a")', "E_TYPE")
            self.error(function + "([], [])", "E_TYPE")

    def test_clamp_boundaries_and_strict_numeric_types(self):
        for expression, expected in [("clamp(-3, 0, 10)", 0), ("clamp(4, 0, 10)", 4),
                                     ("clamp(13, 0, 10)", 10), ("clamp(2, 3, 3)", 3),
                                     ("clamp(0.5, 0, 1)", 0.5), ("clamp(0, 0, 1)", 0)]:
            self.value(expression, expected)
        self.error("clamp(1, 4, 2)", "E_VALUE")
        for expression in ("clamp(false, 0, 1)", "clamp(0, false, 1)",
                           "clamp(0, 0, true)", 'clamp("1", 0, 2)'):
            self.error(expression, "E_TYPE")

    def test_collection_limits_and_result_preflight(self):
        self.error("flat_map([0, 1], many)", "E_LIMIT", "fn many(item):\n    return range(6000)\n")
        self.value("len(flat_map([0, 1], many))", 10000,
                   "fn many(item):\n    return range(5000)\n")
        self.error("flat_map(items, pair)", "E_VALUE", PAIR,
                   data={"items": [{"a": 1, "b": 2}] * 3900})
        # Original list has 10,001 nodes; adding 10,000 chunk lists would exceed 20,000.
        self.error("chunk(range(10000), 1)", "E_VALUE")
        self.value("len(chunk(range(9999), 1))", 9999)
        self.error("group_by(range(7000), text)", "E_VALUE")
        self.error("count_by(range(10000), text)", "E_VALUE")

    def test_added_nesting_and_cumulative_utf8_text_are_bounded(self):
        nested = 1
        for _ in range(32):
            nested = [nested]
        encoded = json.dumps(json.dumps(nested))
        self.error("chunk(parse_json(" + encoded + "), 1)", "E_VALUE")
        # Input bytes fit, repeated references would expand beyond one MiB.
        self.error("flat_map(items, copies)", "E_VALUE",
                   "fn copies(item):\n    return [item, item, item, item, item]\n",
                   data={"items": ["é" * 14000] * 9})

    def test_traversals_and_callbacks_obey_execution_budget(self):
        for expression in ("take(items, 100)", "drop(items, 0)", "chunk(items, 10)",
                           "group_by(items, text)", "count_by(items, text)",
                           "partition(items, positive)", "flat_map(items, pair)",
                           "find(items, negative, null)", "find_index(items, negative)"):
            with self.subTest(expression=expression):
                self.error(expression, "E_LIMIT", PAIR + POSITIVE +
                           "fn negative(item):\n    return item < 0\n",
                           data={"items": list(range(100))}, max_steps=50)
        for function in ("record_pick", "record_omit"):
            self.error(function + "(fields, [])", "E_LIMIT",
                       data={"fields": {str(i): i for i in range(100)}}, max_steps=50)

    def test_callbacks_retain_purity_and_json_boundary(self):
        self.error("group_by([1], bad)", "E_PURITY", 'fn bad(item):\n    say "effect"\n    return "group"\n')
        self.error("flat_map([1], bad)", "E_VALUE", "fn bad(item):\n    return [abs]\n")

    def test_existing_arity_contracts_and_twelve_new_names(self):
        expected = {"group_by": 2, "count_by": 2, "partition": 2, "flat_map": 2,
                    "find": 3, "find_index": 2, "take": 2, "drop": 2, "chunk": 2,
                    "record_pick": 2, "record_omit": 2, "clamp": 3}
        for name, arity in expected.items():
            self.assertEqual(BUILTINS[name], arity)
            self.error(name + "()", "E_ARITY")
        self.assertGreaterEqual(len(BUILTINS), 61)
        self.assertEqual(BUILTINS["range"], (1, 2, 3))
        self.assertEqual(BUILTINS["fold"], 3)
        self.assertEqual(BUILTINS["dec_div"], 3)


if __name__ == "__main__":
    unittest.main()
