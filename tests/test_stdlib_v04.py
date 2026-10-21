"""Standard-library acceptance cases with explicit expected results."""
import json
import unittest
from zensigil import run


class StandardLibraryTests(unittest.TestCase):
    def value(self, expression, expected, prefix=""):
        result = run(prefix + '\nsay json_text(' + expression + ')')
        self.assertTrue(result["ok"], result.get("diagnostics"))
        self.assertEqual(json.loads(result["notes"][0]["message"]), expected)

    def error(self, expression, code, prefix="", **kwargs):
        result = run(prefix + '\nsay json_text(' + expression + ')', **kwargs)
        self.assertFalse(result["ok"], result)
        self.assertEqual(result["diagnostics"][0]["code"], code, result)
        self.assertEqual(result["notes"], [])
        self.assertEqual(result["proposals"], [])

    def test_sequences(self):
        for expression, expected in [
            ('range(4)', [0, 1, 2, 3]), ('range(2, 6, 2)', [2, 4]),
            ('range(10, 1, -3)', [10, 7, 4]), ('range(3, 0)', []),
            ('range(0, 3, -1)', []), ('range(-3, 0)', [-3, -2, -1]),
            ('zip([1, 2], ["a"])', [[1, 'a']]),
            ('enumerate(["a", "b"])', [{'index': 0, 'value': 'a'}, {'index': 1, 'value': 'b'}]),
            ('reverse([1, 2, 3])', [3, 2, 1]), ('reverse("a🙂é")', 'é🙂a'),
        ]:
            with self.subTest(expression=expression):
                self.value(expression, expected)

    def test_range_limits_before_allocation(self):
        self.error('range(100000000000000000000)', 'E_LIMIT')
        self.error('range(1, 4, 0)', 'E_VALUE')
        self.error('range(true)', 'E_TYPE')
        self.error('range(1.0)', 'E_TYPE')
        self.value('len(range(10000))', 10000)
        self.error('range(10001)', 'E_LIMIT')
        self.value('range(0, -1, -1000000000000000)', [0])

    def test_collections_and_strict_equality(self):
        self.value('sum([1, 2.5, -3])', .5)
        self.value('sum([])', 0)
        self.error('sum([true])', 'E_TYPE')
        self.value('sorted([4, -1, 2.5])', [-1, 2.5, 4])
        self.value('sorted(["z", "A", "a"])', ['A', 'a', 'z'])
        self.error('sorted([true])', 'E_TYPE')
        self.error('sorted([1, "2"])', 'E_TYPE')
        self.value('unique([true, 1, 1.0, {x: 2}, {x: 2}, false])', [True, 1, {'x': 2}, False])
        self.value('contains([true], 1)', False)
        self.value('contains([{x: [1]}], {x: [1.0]})', True)
        self.value('contains("café", "fé")', True)
        self.value('contains({a: 1}, "a")', True)
        self.error('contains("abc", 1)', 'E_TYPE')
        self.error('contains({a: 1}, true)', 'E_TYPE')
        self.error('contains(1, 1)', 'E_TYPE')
        self.error('unique(range(1000))', 'E_LIMIT')

    def test_records_preserve_order_and_immutable_record_merge(self):
        self.value('record_keys({z: 1, a: 2})', ['z', 'a'])
        self.value('record_values({z: 1, a: 2})', [1, 2])
        self.value('record_entries({z: 1, a: 2})', [{'key': 'z', 'value': 1}, {'key': 'a', 'value': 2}])
        self.value('record_merge({a: 1, b: 2}, {b: 9, c: 3})', {'a': 1, 'b': 9, 'c': 3})
        self.value('original', {'a': 1}, 'let original = {a: 1}\nlet changed = record_merge(original, {a: 9})')
        self.error('record_keys([])', 'E_TYPE')
        self.error('record_merge({}, [])', 'E_TYPE')

    def test_function_collections(self):
        prefix = ('fn double(x):\n    return x * 2\n'
                  'fn positive(x):\n    return x > 0\n'
                  'fn add(a, b):\n    return a + b\n'
                  'fn priority(x):\n    return x.priority\n')
        self.value('map([1, 3, -2], double)', [2, 6, -4], prefix)
        self.value('filter([-1, 0, 2, 3], positive)', [2, 3], prefix)
        self.value('fold([2, 3, 4], 1, add)', 10, prefix)
        self.value('any([-1, 3], positive)', True, prefix)
        self.value('all([1, 2], positive)', True, prefix)
        self.value('all([], positive)', True, prefix)
        self.value('any([], positive)', False, prefix)
        self.value('fold([], 19, add)', 19, prefix)
        self.value('sort_by([{id: "a", priority: 2}, {id: "b", priority: 1}, {id: "c", priority: 2}], priority)',
                   [{'id': 'b', 'priority': 1}, {'id': 'a', 'priority': 2}, {'id': 'c', 'priority': 2}], prefix)
        self.value('type_of(double)', 'function', prefix)
        self.error('map([1], add)', 'E_ARITY', prefix)
        self.error('filter([1], double)', 'E_TYPE', prefix)
        self.error('map([], add)', 'E_ARITY', prefix)
        self.error('fold([], 0, double)', 'E_ARITY', prefix)
        for name in ('map', 'filter', 'any', 'all', 'sort_by'):
            with self.subTest(name=name):
                self.error(name + '([], 7)', 'E_TYPE')
        self.error('fold([], 0, true)', 'E_TYPE')
        self.error('sort_by([1, "a"], identity)', 'E_TYPE', 'fn identity(x):\n    return x')

    def test_callback_short_circuit(self):
        prefix = 'fn nonzero(x):\n    require x != 0, "zero reached"\n    return x > 0'
        self.value('any([1, 0], nonzero)', True, prefix)
        self.value('all([-1, 0], nonzero)', False, prefix)
        self.error('any([-1, 0], nonzero)', 'E_REQUIRE', prefix)
        self.error('map(range(100), double)', 'E_LIMIT', 'fn double(x):\n    return x * 2', max_steps=150)

    def test_types(self):
        for expression, expected in [('null', 'null'), ('true', 'boolean'), ('1', 'number'),
                                     ('1.2', 'number'), ('"a"', 'string'), ('[]', 'list'), ('{}', 'record')]:
            self.value('type_of(' + expression + ')', expected)

    def test_strings(self):
        self.value('lower("CAFÉ")', 'café')
        self.value('upper("straße")', 'STRASSE')
        self.value('trim("  hello\\n")', 'hello')
        self.value('split("a::b::", "::")', ['a', 'b', ''])
        self.value('join(["a", "b", "c"], " / ")', 'a / b / c')
        self.value('replace("aaa", "aa", "b")', 'ba')
        self.value('starts_with("hello", "he")', True)
        self.value('ends_with("hello", "lo")', True)
        self.value('join([], "x")', '')
        self.error('split("a", "")', 'E_VALUE')
        self.error('replace("a", "", "x")', 'E_VALUE')
        self.error('join(["x", true], "")', 'E_TYPE')
        self.error('join(range(10000), "")', 'E_TYPE')
        self.error('join(map(range(10000), ten), "")', 'E_VALUE', 'fn ten(x):\n    return "abcdefghij"')

    def test_json_and_number_boundaries(self):
        self.value('parse_number("-12.5e1")', -125)
        self.value('parse_number("12")', 12)
        for text in (' 2', '2 ', '+2', '01', 'NaN', 'Infinity', '2abc', '.5', '1.'):
            with self.subTest(text=text):
                self.error('parse_number(' + json.dumps(text) + ')', 'E_VALUE')
        self.error('parse_number("1e999")', 'E_VALUE')
        self.error('parse_number(true)', 'E_TYPE')
        self.value('parse_json("{\\"items\\":[true,null,3]}")', {'items': [True, None, 3]})
        for text in ('{"x":1,"x":2}', 'NaN', '1e999', '[1,]'):
            self.error('parse_json(' + json.dumps(text) + ')', 'E_VALUE')
        self.value('parse_json(json_text({"café": [1, 2]}))', {'café': [1, 2]})

    def test_exact_decimal_text(self):
        for expression, expected in [
            ('dec("1.2300")', '1.23'), ('dec("-0.000")', '0'),
            ('dec_add("0.1", "0.2")', '0.3'), ('dec_sub("0.3", "0.1")', '0.2'),
            ('dec_mul("0.14", "50")', '7'), ('dec_div("1", "8", 2)', '0.12'),
            ('dec_div("3", "8", 2)', '0.38'), ('dec_round("-1.225", 2)', '-1.22'),
            ('dec_compare("1.00", "1")', 0), ('dec_compare("-2", "1")', -1),
            ('dec_add("99999999999999999999", "1")', '100000000000000000000'),
        ]:
            with self.subTest(expression=expression):
                self.value(expression, expected)
        for text in ('NaN', 'Infinity', '+1', '01', '.1', '1.', '1e2', ' 2'):
            self.error('dec(' + json.dumps(text) + ')', 'E_VALUE')
        self.error('dec(0.1)', 'E_TYPE')
        self.error('dec_div("1", "0", 2)', 'E_ZERO')
        self.error('dec_round("1", true)', 'E_VALUE')
        self.error('dec_div("1", "3", 19)', 'E_VALUE')
        self.error('dec("' + '1' * 101 + '")', 'E_VALUE')

    def test_decimal_precision_and_context_isolation(self):
        from decimal import getcontext
        original = getcontext().prec
        try:
            getcontext().prec = 6
            self.value('dec_mul("123456789.25", "2")', '246913578.5')
            self.assertEqual(getcontext().prec, 6)
        finally:
            getcontext().prec = original
        self.value('dec_div("1", "3", 18)', '0.333333333333333333')
        self.value('dec_round("2.5", 0)', '2')
        self.value('dec_round("3.5", 0)', '4')
        self.error('dec_mul("' + '9' * 100 + '", "9")', 'E_VALUE')
        self.error('dec_add("0.' + '0' * 99 + '1", "0")', 'E_VALUE')

    def test_builtin_callbacks_and_common_binding_compatibility(self):
        self.value('map([-2, 1], abs)', [2, 1])
        self.value('fold([2, 7, 3], 0, max)', 7)
        self.value('values', [1, 2], 'let values = [1, 2]')
        self.value('keys', ["a"], 'let keys = ["a"]')
        self.error('map([], get)', 'E_ARITY')

    def test_old_builtins_remain_usable(self):
        self.value('len([1, 2])', 2)
        self.value('ceil_div(7, 2)', 4)
        self.value('fraction(0.14)', {'numerator': 7, 'denominator': 50})
        self.value('round(1.234, 2)', 1.23)
        self.value('get({a: 1}, "b", 7)', 7)
