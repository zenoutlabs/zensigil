"""Definite type advice must not turn unknown or mutable values into errors."""
import unittest
from itertools import product
from unittest.mock import patch

from zensigil import check, run
from zensigil.lint import lint
from zensigil.modules import compile_program
from zensigil.type_lint import warnings, TypeLint, AnalysisLimit


class TypeAdviceTests(unittest.TestCase):
    def advice(self, source, **kwargs):
        result = lint(source, **kwargs)
        self.assertTrue(result['ok'], result)
        return [warning for warning in result['warnings'] if warning['code'].startswith('W_TYPE')]

    def test_literal_annotation_mismatch_is_advice_only(self):
        source = 'let count: integer = "three"\nemit count'
        warning, = self.advice(source)
        self.assertEqual((warning['code'], warning['severity'], warning['line'], warning['column']), ('W_TYPE', 'warning', 1, 1))
        self.assertEqual(warning['source_line'], 'let count: integer = "three"')
        self.assertTrue(check(source, {})['ok'])
        self.assertEqual(run(source, {})['diagnostics'][0]['code'], 'E_TYPE')

    def test_definite_operator_and_control_errors(self):
        cases = ['when 3:\n    emit 1', 'while "yes":\n    break',
                 'emit "three" - 1', 'emit true + 1', 'emit [1] + "x"',
                 'emit 1 and true', 'emit not 2', 'emit "a" < 1',
                 'emit 2 in "two"', 'emit 1 in 4', 'say 2',
                 'for x in "abc":\n    emit x', 'require 1, "bad"',
                 'require false, 12', 'emit choose 1 then 2 otherwise 3',
                 'emit 2.field', 'emit [1][true]', 'emit {a: 1}[0]',
                 'emit "abc"["x":]', 'emit 2[:]']
        for source in cases:
            with self.subTest(source=source):
                self.assertTrue(self.advice(source), source)

    def test_literal_nested_collections_and_unions(self):
        cases = ['let rows: list<integer> = [1, true]',
                 'let rows: record<list<number>> = {a: [1, "bad"]}',
                 'let rows: list<integer> | list<string> = [1, "bad"]',
                 'let rows: list<list<integer>> = [["bad"]]']
        for source in cases:
            with self.subTest(source=source):
                self.assertEqual(len(self.advice(source)), 1)
        for source in ['let rows: list<integer> = []',
                       'let rows: record<integer> = {}',
                       'let rows: list<integer | string> = [1, "ok"]',
                       'let rows: list<integer> = [input_value]',
                       'let rows: list<integer> | record<string> = {a: "ok"}',
                       'let optional: string | null = null']:
            with self.subTest(source=source):
                self.assertEqual(self.advice(source), [])

    def test_named_and_anonymous_arguments_and_results(self):
        cases = ['fn f() -> number:\n    return "bad"',
                 'let f = fn (x: integer) -> string => x',
                 'fn f(n: integer):\n    return n\nemit f("bad")',
                 'let f = fn (x: string) => x\nemit f(1)',
                 'let f = 2\nemit f()',
                 'let f = fn (x) => x\nemit f()',
                 'fn f() -> string:\n    return "x"\nlet n: number = f()']
        for source in cases:
            with self.subTest(source=source):
                self.assertTrue(self.advice(source))
        self.assertEqual(self.advice('fn apply(f: function, n):\n    return f(n)\nemit apply(fn (x) => x, 1)'), [])

    def test_immutable_aliases_and_capture(self):
        self.assertTrue(self.advice('let value = "bad"\nlet next = value\nlet count: integer = next'))
        self.assertTrue(self.advice('let value = "bad"\nlet f = fn () -> integer => value'))
        self.assertTrue(self.advice('let f = fn (x: string) => x\nlet alias = f\nemit alias(1)'))
        self.assertEqual(self.advice('let value = "outer"\nlet f = fn (value: integer) -> integer => value\nemit f(1)'), [])

    def test_core_builtin_signatures_and_aliases(self):
        for source in ['emit len(3)', 'emit has([], "x")', 'emit abs(true)',
                       'emit round(1, "2")', 'emit ceil_div(1.5, 2)',
                       'let length = len\nemit length(1)',
                       'let n: string = len([])', 'let f = len\nemit f()']:
            with self.subTest(source=source):
                self.assertTrue(self.advice(source))
        for source in ['emit len("abc")', 'emit abs(2.5)', 'emit type_of(fn () => 1)',
                       'let n: integer = get({n: 1}, "n", 0)', 'emit min(1, 2.5)']:
            with self.subTest(source=source):
                self.assertEqual(self.advice(source), [])

    def test_mutable_values_are_not_inferred_across_paths(self):
        cases = ['var x = 1\nset x = "ok"\nsay x',
                 'var x = 1\nwhen input_flag:\n    set x = "ok"\nsay x',
                 'var x = 1\nfor item in values:\n    set x = item\nsay x',
                 'var x = 1\nwhile input_flag:\n    set x = "ok"\n    break\nsay x',
                 'var x = 1\nlet f = fn () -> integer => x\nset x = "later"\nemit f()',
                 'var f = fn (x: integer) => x\nset f = fn (x: string) => x\nemit f("ok")']
        for source in cases:
            with self.subTest(source=source):
                self.assertEqual(self.advice(source), [])
        self.assertTrue(self.advice('var count: integer = 1\nset count = "bad"'))
        self.assertTrue(self.advice('var count: integer = 1\nsay count'))

    def test_union_joins_do_not_claim_one_branch_is_certain(self):
        cases = ['let x = choose flag then 1 otherwise "ok"\nsay x',
                 'let x: integer | string = value\nsay x',
                 'let x: number = value\nlet n: integer = x',
                 'let xs: list<string> = values\nlet numbers: list<integer> = xs',
                 'let x = choose flag then 1 otherwise value\nsay x']
        for source in cases:
            with self.subTest(source=source):
                self.assertEqual(self.advice(source), [])
        self.assertTrue(self.advice('let x = choose flag then 1 otherwise "ok"\nlet b: boolean = x'))

    def test_boolean_numeric_distinction_and_float_integer_distinction(self):
        for source in ['let n: number = true', 'let b: boolean = 1', 'let n: integer = 1.0']:
            self.assertTrue(self.advice(source))
        for source in ['let n: number = 1', 'let n: number = 1.0', 'let n: integer = 2 + 3', 'let n: boolean = 1 == true']:
            self.assertEqual(self.advice(source), [])

    def test_unknown_inputs_and_callback_results_do_not_warn(self):
        cases = ['let n: integer = value', 'emit value + "x"',
                 'let n: integer = callback(1)',
                 'let xs: list<integer> = map(values, fn (x) => x)',
                 'fn f(x):\n    return x\nlet n: integer = f("x")',
                 'let x = rows[0]\nlet n: integer = x.field']
        # A callback must be a declared binding; unknown callable input names are
        # rejected by the existing binding checker, before type advice.
        cases[2] = 'let callback = operation\nlet n: integer = callback(1)'
        for source in cases:
            with self.subTest(source=source):
                self.assertEqual(self.advice(source), [])

    def test_module_identities_private_helpers_and_locations(self):
        modules = {
            'words.zs': 'fn helper(x: string) -> string:\n    return x\nexport fn show(x: string) -> string:\n    return helper(x)',
            'numbers.zs': 'fn helper(x: integer) -> integer:\n    return x\nexport fn show(x: integer) -> integer:\n    return helper(x)',
        }
        valid = 'use "words.zs" as words\nuse "numbers.zs" as numbers\nemit words.show("ok")\nemit numbers.show(1)'
        self.assertEqual(self.advice(valid, modules=modules), [])
        source = valid + '\nemit words.show(1)\nemit numbers.show("bad")'
        found = self.advice(source, modules=modules)
        self.assertEqual([(warning['source_name'], warning['line']) for warning in found], [('<program>', 5), ('<program>', 6)])
        modules['numbers.zs'] = 'export fn show() -> integer:\n    return "bad"'
        found = self.advice('use "numbers.zs" as numbers\nemit numbers.show()', modules=modules)
        self.assertEqual([(warning['source_name'], warning['line'], warning['source_line']) for warning in found], [('numbers.zs', 2, '    return "bad"')])

    def test_advice_does_not_execute_source(self):
        with patch('zensigil.runtime.Runtime.execute', side_effect=AssertionError('must not execute')):
            self.assertEqual(self.advice('while true:\n    emit 1 / 0'), [])

    def test_successful_eager_literal_operations_have_no_type_advice(self):
        # Use execution as an independent oracle for every accepted pairing.
        # Short-circuit operators are excluded because lint also checks their
        # untaken operands, as it checks untaken statement branches.
        values = ['0', '1', '1.5', 'true', 'null', '"x"', '[]', '[1]', '{}', '{a: 1}']
        operators = ['+', '-', '*', '/', '%', '==', '!=', '<', '<=', '>', '>=', 'in', 'not in']
        successful = 0
        for left, operator, right in product(values, operators, values):
            source = f'emit ({left}) {operator} ({right})'
            if run(source, {})['ok']:
                successful += 1
                with self.subTest(source=source):
                    self.assertEqual(self.advice(source, data={}), [])
        self.assertGreater(successful, 250)

    def test_bounded_warning_output_and_partial_analysis_marker(self):
        source = '\n'.join('say 1' for _ in range(300))
        found = self.advice(source)
        self.assertEqual(len(found), 201)
        self.assertEqual(found[-1]['code'], 'W_TYPE_LIMIT')
        program, _ = compile_program('emit 1')
        with patch.object(TypeLint, 'tick', side_effect=AnalysisLimit):
            found = warnings(program)
        self.assertEqual([item['code'] for item in found], ['W_TYPE_LIMIT'])


if __name__ == '__main__':
    unittest.main()
