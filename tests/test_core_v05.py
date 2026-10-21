"""Behavioral contracts for closures and compositional runtime annotations."""
import unittest
from zensigil import check, run, test as run_tests
from zensigil.formatter import format_source
from zensigil.astio import ast_document, semantic_tree
from zensigil.syntax import parse


class CoreV05Tests(unittest.TestCase):
    def output(self, source, expected, data=None, **kwargs):
        result = run(source, {} if data is None else data, **kwargs)
        self.assertTrue(result['ok'], result)
        self.assertEqual(result['values'], expected)
        return result

    def error(self, source, code, data=None, **kwargs):
        result = run(source, {} if data is None else data, **kwargs)
        self.assertFalse(result['ok'], result)
        self.assertEqual(result['diagnostics'][0]['code'], code, result)
        self.assertEqual(result['values'], [])
        self.assertEqual(result['notes'], [])
        self.assertEqual(result['proposals'], [])
        return result['diagnostics'][0]

    def test_anonymous_functions_and_immediate_calls(self):
        self.output('let double = fn (n: number) -> number => n * 2\nemit double(3)\nemit (fn () => 7)()\nemit map([1, 2, 3], fn (x) => x + 1)', [6, 7, [2, 3, 4]])

    def test_input_capture_and_creation_time_snapshot(self):
        self.output('var factor = scale\nlet multiply = fn (n) => n * factor\nset factor = 100\nemit multiply(3)', [12], {'scale': 4})
        self.output('var xs = [1, 2]\nlet original = fn () => xs\nset xs = xs + [3]\nemit original()\nemit xs', [[1, 2], [1, 2, 3]])
        result = check('let operation = fn (x) => x + adjustment')
        self.assertTrue(result['ok'], result)
        self.assertEqual(result['possible_inputs'], ['adjustment'])
        self.error('let operation = fn (x) => x + adjustment', 'E_NAME')

    def test_closures_survive_return_and_nested_capture(self):
        self.output('fn make_adder(base: number) -> function:\n    return fn (value: number) -> number => base + value\nlet add5 = make_adder(5)\nemit add5(7)\nlet nested = fn (a) => fn (b) => fn (c) => a + b + c\nemit nested(1)(2)(3)', [12, 6])
        self.output('let recur = fn (self, n: integer) -> integer => choose n == 0 then 0 otherwise self(self, n - 1) + 1\nemit recur(recur, 5)', [5])
        self.output('let seed = 10\nlet outer = fn (a) => fn (b) => a + b + seed\nemit outer(2)(3)', [15])

    def test_parameter_and_block_shadowing(self):
        self.output('let x = 100\nlet outer = fn (x) => fn (x) => x\nemit outer(2)(3)\nvar callback = fn () => 0\nwhen true:\n    let x = 9\n    set callback = fn () => x\nemit callback()', [3, 9])
        self.output('var callback = fn () => 0\nfor index in [1, 2, 3]:\n    set callback = fn () => index\nemit callback()', [3])
        self.error('let f = fn (x, x) => x', 'E_DUPLICATE')
        self.error('let f = fn (map) => map', 'E_DUPLICATE')

    def test_capture_does_not_include_unused_bindings(self):
        # A large unused input must neither be copied nor consume capture work.
        result = self.output('let f = fn () => 1\nemit f()', [1], {'unused': list(range(9000))}, max_steps=30)
        self.assertLess(result['stats']['steps'], 30)

    def test_higher_order_functions_callbacks_and_aliases(self):
        self.output('fn apply(operation: function, value):\n    return operation(value)\nlet plus = fn (x) => x + 10\nemit apply(plus, 4)\nemit filter([1, 2, 3, 4], fn (x) => x % 2 == 0)\nemit fold([1, 2, 3], 0, fn (a, b) => a + b)\nemit sort_by([{rank: 3}, {rank: 1}], fn (item) => item.rank)', [14, [2, 4], 6, [{'rank': 1}, {'rank': 3}]])
        for source in ['let f = fn (x) => x\nemit f()', 'emit map([], fn () => 1)', 'emit filter([], fn (a, b) => true)', 'emit fold([], 0, fn (a) => a)']:
            with self.subTest(source=source):
                self.error(source, 'E_ARITY')

    def test_function_identity_and_json_boundary(self):
        self.output('let first = fn () => 1\nlet alias = first\nlet second = fn () => 1\nemit [first == alias, first == second, abs == abs, first != abs]\nemit type_of(first)', [[True, False, True, True], 'function'])
        for source in ['emit fn () => 1', 'emit [fn () => 1]', 'emit {callback: fn () => 1}', 'emit text(fn () => 1)', 'emit json_text(fn () => 1)']:
            with self.subTest(source=source):
                self.error(source, 'E_VALUE')
        self.error('let f = fn () => 1\nemit f < f', 'E_TYPE')

    def test_capturing_closure_keeps_old_function_identity(self):
        self.output('var previous = fn (x) => x + 1\nlet saved = fn (x) => previous(x)\nset previous = fn (x) => x + 100\nemit saved(4)', [5])

    def test_purity_named_function_isolation_and_invalid_forward_capture(self):
        for source in ['let x = 1\nfn bad():\n    return fn () => x', 'fn bad():\n    return fn () => input_value', 'let f = fn () => later\nlet later = 1', 'test "isolated":\n    let f = fn () => input_value\n    require f() == 1, "bad"']:
            with self.subTest(source=source):
                self.error(source, 'E_NAME')
        self.error('let f = fn (x) => f(x)', 'E_CALL')
        for source in ['let f = fn () => set x = 1', 'let f = fn () => emit 1', 'let f = fn () => say "no"', 'let f = fn () => propose action(x: 1)']:
            with self.subTest(source=source):
                self.error(source, 'E_SYNTAX')

    def test_untaken_lambda_is_checked_without_evaluation(self):
        self.output('let unused = choose false then fn () => 1 / 0 otherwise fn () => 5\nemit unused()', [5])
        self.error('let unused = choose true then fn () => 1 otherwise fn () => missing', 'E_NAME')
        self.output('let f = fn () -> integer => "not checked yet"\nemit 1', [1])
        self.error('let f = fn () -> integer => "not checked yet"\nemit f()', 'E_TYPE')

    def test_nested_annotations_lists_records_nullable_unions(self):
        self.output('let rows: list<record<number | null>> = [{a: 1, b: null}, {c: 2.5}]\nlet names: record<list<string>> = {groups: ["A", "B"]}\nlet optional: list<number> | null = null\nemit [rows, names, optional]', [[[{'a': 1, 'b': None}, {'c': 2.5}], {'groups': ['A', 'B']}, None]])
        self.output('let values: list<list<integer> | string> = [[1, 2], "ok"]\nlet callback: function | null = fn () => 8\nemit values\nemit callback()', [[[1, 2], 'ok'], 8])
        self.output('let empty: list<record<list<function>>> = []\nlet record_empty: record<integer> = {}\nemit [empty, record_empty]', [[[], {}]])

    def test_typed_reassignment_arguments_and_returns(self):
        self.output('var xs: list<integer> | null = null\nset xs = [1, 2]\nfn total(xs: list<integer>) -> integer | null:\n    return choose len(xs) == 0 then null otherwise sum(xs)\nlet transform = fn (xs: list<integer>) -> list<number> => map(xs, fn (x) => x * 1.5)\nemit total(xs)\nemit total([])\nemit transform(xs)', [3, None, [1.5, 3.0]])
        bad = ['let xs: list<integer> = [1, true]', 'let xs: record<list<number>> = {a: [1, "bad"]}', 'var xs: list<integer> = [1]\nset xs = [2.5]', 'fn f(xs: list<string>):\n    return xs\nemit f([1])', 'fn f() -> record<integer>:\n    return {a: false}\nemit f()', 'let f = fn (xs: list<string>) => xs\nemit f([1])', 'let f = fn () -> list<integer> => [1.5]\nemit f()', 'let value: null | boolean = 0']
        for source in bad:
            with self.subTest(source=source):
                diagnostic = self.error(source, 'E_TYPE')
                self.assertIn('type', diagnostic['message'])

    def test_annotation_runtime_work_is_budgeted(self):
        self.error('let xs: list<integer> = values', 'E_LIMIT', {'values': list(range(200))}, max_steps=50)
        self.error('let xs: list<list<string> | list<integer>> = values', 'E_LIMIT', {'values': [list(range(50))] * 20}, max_steps=100)

    def test_invalid_annotation_syntax_and_complexity(self):
        cases = [('let x: number<string> = 1', 'E_TYPE'), ('let x: list<> = []', 'E_TYPE'), ('let x: list<number = []', 'E_SYNTAX'), ('let x: list<number, string> = []', 'E_SYNTAX'), ('let x: number | = 1', 'E_TYPE'), ('let x: (number | string) = 1', 'E_TYPE'), ('let x: ' + 'list<' * 17 + 'integer' + '>' * 17 + ' = []', 'E_LIMIT'), ('let x: ' + ' | '.join(['integer'] * 9) + ' = 1', 'E_LIMIT')]
        for source, code in cases:
            with self.subTest(source=source):
                self.error(source, code)
        for source in ['let x: "number" = 1', 'let x: "list"<"integer"> = [1]', 'let x: list<"integer"> = [1]', 'let f = fn (x: "number") -> number => x', 'let f = fn (x: number) -> "number" => x']:
            with self.subTest(source=source):
                self.error(source, 'E_TYPE')
        huge_union = ' | '.join(['list<' + ' | '.join(['integer'] * 8) + '>'] * 8)
        self.error('let x: ' + huge_union + ' = []', 'E_LIMIT')
        self.output('let x: ' + 'list<' * 16 + 'integer' + '>' * 16 + ' = []\nemit x', [[]])

    def test_invalid_lambda_grammar(self):
        for source in ['let f = fn x => x', 'let f = fn (x): x', 'let f = fn () =>', 'let f = fn (x = 1) => x', 'let f = fn (x) -> => x', 'let f = fn (x) => return x']:
            with self.subTest(source=source):
                result = run(source, {})
                self.assertFalse(result['ok'], result)
                self.assertIn(result['diagnostics'][0]['code'], ['E_TYPE', 'E_SYNTAX'])

    def test_lambda_failure_trace_and_transactional_rollback(self):
        diagnostic = self.error('fn apply(f):\n    return f()\nlet bad = fn () => 1 / 0\nemit 7\nsay "discard"\nemit apply(bad)', 'E_ZERO')
        self.assertEqual(diagnostic['line'], 3)
        self.assertEqual([item['function'] for item in diagnostic['call_trace']], ['fn@<program>:3:11', 'apply'])
        self.output('use "lib.zs"\nemit make(3)(4)', [7], modules={'lib.zs': 'fn make(base):\n    return fn (x) => base + x'})
        diagnostic = self.error('use "lib.zs"\nemit bad()()', 'E_ZERO', modules={'lib.zs': 'fn bad():\n    return fn () => 1 / 0'})
        self.assertEqual(diagnostic['source_name'], 'lib.zs')
        self.assertEqual(diagnostic['call_trace'][0]['function'], 'fn@lib.zs:2:12')

    def test_closure_call_depth_and_retained_environment_limits(self):
        self.error('var callback = fn (x) => x\nfor n in range(60):\n    let previous = callback\n    set callback = fn (x) => previous(x)\nemit callback(1)', 'E_LIMIT')
        self.error('var callback = fn () => 0\nfor n in range(10000):\n    let previous = callback\n    set callback = fn () => previous', 'E_LIMIT')
        self.error('let large = values\nfor n in range(4):\n    let f = fn () => large', 'E_LIMIT', {'values': list(range(9000))})
        self.error('let message = text_value\nfor n in range(20):\n    let f = fn () => message', 'E_LIMIT', {'text_value': 'x' * 65536})

    def test_formatter_and_public_ast_preserve_new_syntax(self):
        source = 'let double:list<number>|null=null\nlet f=fn(x:record<list<integer>>)->integer=>x.a[0]+1\nemit f({a:[3]})\n'
        formatted = format_source(source)
        self.assertEqual(format_source(formatted), formatted)
        self.assertEqual(semantic_tree(parse(source)), semantic_tree(parse(formatted)))
        self.output(formatted, [4])
        self.output(format_source('let xs:list<integer>=[1]\nlet f=fn()->list<integer>=>xs\nemit f()'), [[1]])
        document = ast_document(source)
        self.assertEqual(document['body'][1]['parts'][1]['kind'], 'lambda')

    def test_inline_tests_support_local_closures(self):
        source = 'test "closure":\n    let base = 5\n    let f = fn (n: number) -> number => base + n\n    require f(2) == 7, "Expected seven"'
        result = run_tests(source)
        self.assertTrue(result['ok'], result)
        self.assertEqual(result['passed'], 1)


if __name__ == '__main__':
    unittest.main()
