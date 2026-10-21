import unittest
from zensigil import run, check
from zensigil.syntax import parse
from zensigil.checker import Checker
from zensigil.testing import run_test_program

class CoreV04Tests(unittest.TestCase):
    def output(self, source, expected, data=None):
        result = run(source, data or {})
        self.assertTrue(result['ok'], result)
        self.assertEqual(result['values'], expected)

    def error(self, source, code):
        result = run(source, {})
        self.assertFalse(result['ok'], result)
        self.assertEqual(result['diagnostics'][0]['code'], code, result)
        self.assertEqual(result['proposals'], [])
        self.assertEqual(result['notes'], [])
        self.assertEqual(result.get('values', []), [])
        return result['diagnostics'][0]

    def test_local_mutation_loop_and_control(self):
        self.output('var n: integer = 0\nvar total = 0\nwhile n < 8:\n    set n = n + 1\n    when n == 2:\n        continue\n    when n == 5:\n        break\n    set total = total + n\nemit [n, total]', [[5,8]])

    def test_nearest_scope_mutation_and_shadowing(self):
        self.output('var x = 1\nwhen true:\n    var x = 5\n    set x = 6\n    emit x\nemit x', [6,1])
        self.error('var x = 1\nwhen true:\n    let x = 5\n    set x = 6', 'E_MUTABILITY')
        self.error('let x = 1\nset x = 2', 'E_MUTABILITY')
        self.error('for x in [1]:\n    set x = 2', 'E_MUTABILITY')

    def test_pure_mutation_higher_order_and_function_result(self):
        self.output('fn count(n: integer) -> integer:\n    var total = 0\n    for x in [1,2,3]:\n        set total = total + n\n    return total\nfn apply(f: function, n: integer) -> integer:\n    return f(n)\nfn identity(f: function) -> function:\n    return f\nlet callback = identity(count)\nemit apply(callback, 4)\nemit identity(abs)(-9)', [12,9])

    def test_control_context_and_purity(self):
        for source, code in [('break', 'E_SCOPE'), ('continue', 'E_SCOPE'),
            ('fn bad():\n    break','E_SCOPE'), ('fn bad():\n    emit 1','E_PURITY'),
            ('var x = 1\nfn bad():\n    set x = 2','E_NAME'),
            ('let x = 1\nfn bad():\n    return x','E_NAME')]:
            with self.subTest(source=source): self.error(source,code)

    def test_annotations(self):
        self.output('let a: any = null\nlet b: null = null\nlet c: number = 2\nlet d: list = []\nlet e: record = {}\nlet f: boolean = true\nlet g: string = "yes"\nemit [a,b,c,d,e,f,g]', [[None,None,2,[],{},True,'yes']])
        for source in ['let x: integer = true', 'var x: integer = 1\nset x = 1.5',
                       'fn f(x: integer):\n    return x\nemit f(1.0)',
                       'fn f() -> integer:\n    let x = 1\nemit f()']:
            with self.subTest(source=source): self.error(source, 'E_TYPE')
        self.error('let x: nonsense = 1', 'E_TYPE')

    def test_lazy_selection_null_and_missing_field(self):
        self.output('emit choose false then 1 / 0 otherwise 4\nemit null ?? 9\nemit false ?? true\nemit 0 ?? 9\nemit 1 ?? 1 / 0\nemit null ?? null ?? 3', [4,9,False,0,1,3])
        self.error('emit {}.missing ?? 1','E_FIELD')
        self.error('emit choose 1 then 2 otherwise 3','E_TYPE')
        self.error('emit choose true then 1 otherwise unknown()', 'E_CALL')

    def test_membership_concat_and_unicode_slices(self):
        self.output('emit true in [1]\nemit {a: 1} in [{a: 1.0}]\nemit "a" in {a: null}\nemit "bc" in "abcd"\nemit 3 not in [1,2]\nemit [1] + [2,3]\nemit "a🦊b"[1]\nemit "a🦊b"[1:99]\nemit [1,2,3][:2]\nemit [1,2][9:]\nemit [1,2][2:1]', [False,True,True,True,True,[1,2,3],'🦊','🦊b',[1,2],[],[]])
        for source, code in [('emit 1 in {a: 1}', 'E_TYPE'), ('emit 1 in "1"','E_TYPE'),
                             ('emit [1][-1:]', 'E_INDEX'), ('emit "a"[true]', 'E_TYPE'),
                             ('emit [1][0:1:2]', 'E_SYNTAX')]:
            with self.subTest(source=source): self.error(source,code)

    def test_function_boundaries_and_dynamic_arity(self):
        for source, code in [('emit abs','E_VALUE'),('emit [abs]','E_VALUE'),
                             ('emit text(abs)','E_VALUE'), ('let f = abs\nemit f(1,2)','E_ARITY'),
                             ('let f = 1\nemit f(2)','E_CALL')]:
            with self.subTest(source=source): self.error(source, code)

    def test_failure_trace_and_transaction(self):
        diagnostic = self.error('fn inner():\n    return 1 / 0\nfn outer():\n    return inner()\nemit 1\nsay "discard"\nemit outer()', 'E_ZERO')
        self.assertEqual(diagnostic['line'], 2)
        self.assertEqual([x['function'] for x in diagnostic['call_trace']], ['inner','outer'])

    def test_output_budget_and_while_budget(self):
        self.error('for n in range(1001):\n    emit n', 'E_LIMIT')
        result=run('while true:\n    let x = 1', {}, max_steps=100)
        self.assertFalse(result['ok'])
        self.assertEqual(result['diagnostics'][0]['code'], 'E_LIMIT')

    def test_inline_tests_independent_and_skipped_in_run(self):
        source='fn twice(x):\n    return x * 2\ntest "arithmetic":\n    require twice(3) == 6, "Wrong double"\ntest "failure":\n    require false, "Expected failure"\nemit 9'
        self.output(source, [9])
        program = parse(source)
        Checker(program, []).check(program)
        result=run_test_program(program,{},source)
        self.assertFalse(result['ok'])
        self.assertEqual(result['stats']['passed'],1)
        self.assertEqual(result['stats']['failed'],1)
        self.error('let x = 1\ntest "isolated":\n    require x == 1, "capture"','E_NAME')
        self.error('test "pure":\n    say "no"','E_PURITY')
        self.error('when true:\n    test "nested":\n        require true, "no"','E_SCOPE')
        self.error('test "same":\n    require true, "x"\ntest "same":\n    require true, "y"','E_DUPLICATE')

    def test_unresolved_use_rejected(self):
        program=parse('use "helpers.zs"')
        with self.assertRaises(Exception) as caught: Checker(program,[]).check(program)
        self.assertEqual(caught.exception.code,'E_IMPORT')

if __name__ == '__main__': unittest.main()
