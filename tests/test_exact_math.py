import unittest
from zensigil import run


class ExactMathTests(unittest.TestCase):
    def test_round_for_readable_display(self):
        self.assertEqual(self.note('round(7 / 0.14, 2)'), '50.0')
        self.assertEqual(self.note('round(1 / 3, 2)'), '0.33')
        self.assertEqual(self.note('round(2.5, 0)'), '2.0')
        for expression in ('round(1, -1)', 'round(1, 11)', 'round(1, 2.0)'):
            self.assertEqual(run('say text(' + expression + ')')['diagnostics'][0]['code'], 'E_VALUE')

    def note(self, expression):
        result = run(f'say text({expression})')
        self.assertTrue(result['ok'], result)
        return result['notes'][0]['message']

    def test_fraction_uses_decimal_spelling(self):
        self.assertEqual(self.note('fraction(0.14)'), '{"denominator":50,"numerator":7}')
        self.assertEqual(self.note('fraction(-0.125)'), '{"denominator":8,"numerator":-1}')
        self.assertEqual(self.note('fraction(3)'), '{"denominator":1,"numerator":3}')

    def test_ceil_div_exact_large_and_negative_integers(self):
        for expr, expected in [('ceil_div(7, 1)', '7'), ('ceil_div(7, 2)', '4'), ('ceil_div(-7, 2)', '-3'), ('ceil_div(7, -2)', '-3'),
                               ('ceil_div(100000000000000000001, 100000000000000000000)', '2')]:
            self.assertEqual(self.note(expr), expected)

    def test_types_zero_and_limits(self):
        for expr in ('fraction(true)', 'ceil_div(1.0, 2)', 'ceil_div(1, false)'):
            self.assertEqual(run('say text(' + expr + ')')['diagnostics'][0]['code'], 'E_TYPE')
        self.assertEqual(run('say text(ceil_div(1, 0))')['diagnostics'][0]['code'], 'E_ZERO')
        self.assertEqual(run('say text(fraction(1e-200))')['diagnostics'][0]['code'], 'E_VALUE')
