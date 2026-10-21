import copy
import json
from pathlib import Path
import unittest
from zensigil import check, run
from zensigil.jsonio import loads

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"


class LanguageTests(unittest.TestCase):
    def result(self, source, data=None):
        result = run(source, data)
        self.assertTrue(result["ok"], result.get("diagnostics"))
        return result

    def note(self, expression, expected):
        self.assertEqual(self.result("say text(" + expression + ")")["notes"][0]["message"], expected)

    def error(self, source, code, data=None, **kwargs):
        result = run(source, data, **kwargs)
        self.assertFalse(result["ok"], result)
        self.assertEqual(result["diagnostics"][0]["code"], code, result)
        self.assertEqual(result["proposals"], [])
        self.assertEqual(result["notes"], [])
        return result["diagnostics"][0]

    def test_arithmetic_precedence(self):
        self.note("2 + 3 * 4", "14")
        self.note("(2 + 3) * 4", "20")
        self.note("10 - 3 - 2", "5")
        self.note("-2 * 3 + +1", "-5")
        self.note("7 % 3", "1")
        self.note("7 / 2", "3.5")
        self.note("1e2 + 0.5", "100.5")

    def test_logical_precedence_and_short_circuit(self):
        self.note("not 1 == 2 and true or false", "true")
        self.note("false and 1 / 0 > 0", "false")
        self.note("true or 1 / 0 > 0", "true")

    def test_strict_booleans(self):
        for source in ("when 1:\n    say \"no\"", "say text(not 0)", "say text(true and 1)"):
            with self.subTest(source=source):
                self.error(source, "E_TYPE")

    def test_numbers_are_not_booleans(self):
        self.note("true == 1", "false")
        self.note("[true] == [1]", "false")
        self.note("{x: true} == {x: 1}", "false")
        self.note("1 == 1.0", "true")
        self.error("say text(true + 1)", "E_TYPE")

    def test_strings_and_escapes(self):
        self.assertEqual(self.result('say "Hi, " + "Gregory! # a string"')["notes"][0]["message"], "Hi, Gregory! # a string")
        self.assertEqual(self.result('say "one\\ntwo" # a comment')["notes"][0]["message"], "one\ntwo")
        self.error('say "unterminated', "E_STRING")
        self.error('say "bad\\q"', "E_STRING")
        self.error('say "\\ud800"', "E_STRING")

    def test_no_coercion(self):
        self.error('say text(5 + "3")', "E_TYPE")
        self.error('say text("3" < 4)', "E_TYPE")
        self.error('say 7', "E_TYPE")
        self.error('say text("x" * 3)', "E_TYPE")

    def test_lists_records_indexing(self):
        self.note('{items: [3, 5]}["items"][1]', "5")
        self.note('{a: 1, b: [2]} == {b: [2], a: 1}', "true")
        self.error('say text([1][-1])', "E_INDEX")
        self.error('say text([1][1])', "E_INDEX")
        self.error('say text([1][false])', "E_TYPE")
        self.error('say text([1][0.0])', "E_TYPE")
        self.error('say text(1.sku)', "E_TYPE")

    def test_multiline_and_comments(self):
        self.note('[\n    1, # first\n    2,\n][1]', "2")
        self.note('{\n    a: 3,\n}.a', "3")
        self.result('# comment\n\nrule "x":\n    # nested comment\n    say "yes"\n')

    def test_scope_and_shadowing(self):
        result = self.result('let x = 1\nwhen true:\n    let x = 2\n    say text(x)\nsay text(x)')
        self.assertEqual([note["message"] for note in result["notes"]], ["2", "1"])
        self.error('when true:\n    let x = 1\nsay text(x)', "E_NAME")
        self.error('for x in [1]:\n    say text(x)\nsay text(x)', "E_NAME")
        self.error('let x = 1\nlet x = 2', "E_DUPLICATE")

    def test_fresh_loop_scope(self):
        result = self.result('for x in [1, 2, 3]:\n    let twice = x * 2\n    say text(twice)')
        self.assertEqual([n["message"] for n in result["notes"]], ["2", "4", "6"])
        self.error('for x in {a: 1}:\n    say "no"', "E_TYPE")

    def test_functions_and_early_return(self):
        result = self.result('say text(double(4))\nfn double(x):\n    return x * 2')
        self.assertEqual(result["notes"][0]["message"], "8")
        result = self.result('fn first(xs):\n    for x in xs:\n        when x > 2:\n            return x\n    return null\nsay text(first([1, 4, 9]))')
        self.assertEqual(result["notes"][0]["message"], "4")
        result = self.result('fn empty():\n    let x = 1\nsay text(empty())')
        self.assertEqual(result["notes"][0]["message"], "null")

    def test_function_purity(self):
        self.error('let x = 2\nfn f():\n    return x\nsay text(f())', "E_NAME")
        self.error('fn f():\n    say "side effect"', "E_PURITY")
        self.error('fn f():\n    propose x(a: 1)', "E_PURITY")
        self.error('return 1', "E_SCOPE")

    def test_functions_arity_names_and_depth(self):
        self.error('say text(abs())', "E_ARITY")
        self.error('fn f(x):\n    return x\nsay text(f(1, 2))', "E_ARITY")
        self.error('say text(unknown())', "E_CALL")
        self.error('fn f():\n    return f()\nsay text(f())', "E_LIMIT")
        self.error('fn f(x, x):\n    return x', "E_DUPLICATE")
        self.error('fn abs(x):\n    return x', "E_DUPLICATE")
        self.error('when true:\n    fn f():\n        return 1', "E_SCOPE")

    def test_builtins(self):
        for expr, expected in [('ceil(2.2)', '3'), ('floor(-2.2)', '-3'), ('abs(-2)', '2'),
                               ('min(2, 3)', '2'), ('max(2, 3)', '3'), ('len({a: 1})', '1'),
                               ('has({a: null}, "a")', 'true'), ('get({}, "a", 7)', '7'),
                               ('get({a: null}, "a", 7)', 'null')]:
            with self.subTest(expr=expr):
                self.note(expr, expected)
        self.error('say text(len(7))', 'E_TYPE')
        self.error('say text(get([], "x", 0))', 'E_TYPE')
        self.error('say text(ceil(true))', 'E_TYPE')

    def test_missing_field_diagnostic(self):
        error = self.error('say "before"\nsay text(item.stock)', 'E_FIELD', {"item": {"sku": "A17"}})
        self.assertEqual(error["line"], 2)
        self.assertEqual(error["column"], 14)
        self.assertIn("A17", error["message"])
        self.assertIn("stock", error["message"])
        self.assertEqual(error["source_line"], 'say text(item.stock)')

    def test_all_or_nothing_on_failure(self):
        self.error('propose buy(sku: "A17")\nsay "before"\nlet x = 1 / 0', 'E_ZERO')
        self.error('propose buy(sku: "A17")\nlet x = 1 % 0', 'E_ZERO')

    def test_proposals_and_deduplication(self):
        source = 'rule "x":\n    propose review(a: 1, b: 2)\n    propose review(b: 2, a: 1)'
        result = self.result(source)
        self.assertEqual(len(result["proposals"]), 1)
        self.assertEqual(result["stats"]["duplicates_collapsed"], 1)
        self.assertTrue(result["proposals"][0]["requires_review"])
        self.assertEqual(result, self.result(source))
        self.assertEqual(result["proposals"][0]["source"]["line"], 2)
        self.assertNotEqual(result["proposals"][0]["id"], self.result(source.replace('a: 1', 'a: 3'))["proposals"][0]["id"])

    def test_rule_identity_and_order(self):
        result = self.result('rule "one":\n    propose x(a: 1)\nrule "two":\n    propose x(a: 1)')
        self.assertEqual([p["rule"] for p in result["proposals"]], ["one", "two"])
        self.error('rule "x":\n    say "a"\nrule "x":\n    say "b"', 'E_DUPLICATE')
        self.error('when true:\n    rule "x":\n        say "a"', 'E_SCOPE')

    def test_duplicate_fields(self):
        self.error('propose x(a: 1, a: 2)', 'E_DUPLICATE')
        self.error('let x = {a: 1, a: 2}', 'E_DUPLICATE')
        self.error('propose x()', 'E_SYNTAX')

    def test_check_includes_untaken_branches(self):
        source = 'when false:\n    say typo'
        self.assertFalse(check(source, {})["ok"])
        self.assertEqual(check(source)["possible_inputs"], ["typo"])
        self.assertFalse(check(source)["input_names_checked"])
        self.assertTrue(check(source, {"typo": "known"})["ok"])
        self.assertFalse(check('when false:\n    say nope()')["ok"])

    def test_input_is_not_mutated(self):
        data = {"items": [{"sku": "A17"}]}
        original = copy.deepcopy(data)
        self.result('for x in items:\n    propose x(item: x)', data)
        self.assertEqual(data, original)

    def test_input_boundaries(self):
        for data in ([], {"x": float('nan')}, {"x": float('inf')}, {"x": 10 ** 1000},
                     {"a-b": 1}, {"len": 2}, {"x": object()}, {1: "bad"}):
            with self.subTest(data=repr(data)[:80]):
                self.error('say "hi"', 'E_INPUT', data)
        cyclic = []
        cyclic.append(cyclic)
        self.error('say "hi"', 'E_INPUT', {"x": cyclic})

    def test_limits(self):
        self.error('for x in [1, 2, 3]:\n    say text(x)', 'E_LIMIT', max_steps=3)
        self.error('#' * 65537, 'E_LIMIT')
        self.error('say text(' + '[' * 49 + '1' + ']' * 49 + ')', 'E_LIMIT')
        self.error('say text(1e999)', 'E_NUMBER')
        self.error('say text(1e100 * 10)', 'E_VALUE')
        self.error('for x in items:\n    say "hi"', 'E_LIMIT', {"items": list(range(1001))})
        self.error('let x = "a"\nsay x + long', 'E_VALUE', {"long": 'b' * 65536})

    def test_invalid_syntax(self):
        cases = [('say "x"\n  say "y"', 'E_INDENT'), ('when true:\n\tsay "x"', 'E_INDENT'),
                 ('when true:\n        say "x"', 'E_INDENT'), ('say text(1 < 2 < 3)', 'E_SYNTAX'),
                 ('let x = [1)', 'E_SYNTAX'), ('let x = [1', 'E_SYNTAX'),
                 ('say $', 'E_TOKEN'), ('let x =', 'E_SYNTAX'), ('when true:\n', 'E_SYNTAX'),
                 ('say text({a: 1}.a())', 'E_CALL')]
        for source, code in cases:
            with self.subTest(source=source):
                self.error(source, code)

    def test_no_host_execution(self):
        self.error('say text(__import__("os"))', 'E_CALL')
        self.error('say text(open("secret"))', 'E_CALL')
        self.error('say text(item.__class__)', 'E_FIELD', {"item": {}})

    def test_strict_json(self):
        for raw in ('{"x": 1, "x": 2}', '{"x": NaN}', '1' * 102):
            with self.subTest(raw=raw):
                with self.assertRaises(ValueError):
                    loads(raw)

    def test_all_examples(self):
        expected = {"restock": (2, 1), "shipments": (2, 0), "margins": (2, 1), "hello": (0, 1),
                    "functions": (0, 1), "records": (0, 2), "optional": (1, 1), "support": (1, 0), "duplicates": (2, 0)}
        for name, (proposals, notes) in expected.items():
            with self.subTest(name=name):
                result = self.result((EXAMPLES / f"{name}.zs").read_text(), json.loads((EXAMPLES / f"{name}.json").read_text()))
                self.assertEqual(len(result["proposals"]), proposals)
                self.assertEqual(len(result["notes"]), notes)
        self.error((EXAMPLES / 'error.zs').read_text(), 'E_FIELD', {"item": {"sku": "A17"}})

    def test_commerce_expected_values(self):
        def example(name):
            return self.result((EXAMPLES / f'{name}.zs').read_text(), json.loads((EXAMPLES / f'{name}.json').read_text()))
        self.assertEqual([p["fields"] for p in example('restock')["proposals"]],
                         [{"sku": "A17", "quantity": 105, "target_days": 30}, {"sku": "B24", "quantity": 54, "target_days": 30}])
        shipments = example('shipments')["proposals"]
        self.assertEqual(shipments[0]["fields"]["missing_units"], 8)
        self.assertEqual(shipments[1]["fields"]["extra_units"], 4)
        self.assertEqual([p["fields"]["profit_cents"] for p in example('margins')["proposals"]], [300, -50])

    def test_restock_boundary_and_optional_field(self):
        source = (EXAMPLES / 'restock.zs').read_text()
        items = [{"sku": "AT14", "stock": 28, "daily_sales": 2, "discontinued": False},
                 {"sku": "ZERO", "stock": 0, "daily_sales": 0, "discontinued": False},
                 {"sku": "MISSING", "stock": 2, "discontinued": False}]
        result = self.result(source, {"inventory": items})
        self.assertEqual(result["proposals"], [])
        self.assertEqual(len(result["notes"]), 2)


if __name__ == "__main__":
    unittest.main()
