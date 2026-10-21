import unittest
from zensigil import check, run


class RequireTests(unittest.TestCase):
    def test_pass_and_lazy_message(self):
        result = run('require true, text(1 / 0)\nsay "passed"')
        self.assertTrue(result['ok'], result)
        self.assertEqual(result['notes'][0]['message'], 'passed')

    def test_failure_rolls_back_all_output(self):
        result = run('say "before"\npropose review(id: "x")\nrequire false, "Target must cover the review threshold"')
        self.assertFalse(result['ok'])
        self.assertEqual(result['proposals'], [])
        self.assertEqual(result['notes'], [])
        error = result['diagnostics'][0]
        self.assertEqual(error['code'], 'E_REQUIRE')
        self.assertEqual(error['message'], 'Target must cover the review threshold')
        self.assertEqual(error['line'], 3)

    def test_types_and_bindings(self):
        for source in ('require 1, "boolean needed"', 'require false, 42'):
            self.assertEqual(run(source)['diagnostics'][0]['code'], 'E_TYPE')
        self.assertFalse(check('require true, typo', {})['ok'])
        self.assertEqual(run('let require = 1')['diagnostics'][0]['code'], 'E_SYNTAX')

    def test_pure_functions_and_loop(self):
        source = 'fn positive(n):\n    require n > 0, "Expected a positive number"\n    return n\nfor n in values:\n    say text(positive(n))'
        self.assertTrue(run(source, {'values': [1, 2]})['ok'])
        result = run(source, {'values': [1, 0]})
        self.assertFalse(result['ok'])
        self.assertEqual(result['notes'], [])
        self.assertEqual(result['diagnostics'][0]['message'], 'Expected a positive number')
