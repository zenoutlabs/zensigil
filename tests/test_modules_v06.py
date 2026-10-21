"""Independent behavior contracts for namespaced imports and explicit exports."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from zensigil import check, run, test as run_tests
from zensigil.astio import ast_document, semantic_tree
from zensigil.checker import Checker
from zensigil.formatter import format_source
from zensigil.modules import compile_program, file_modules, function_identity, module_scopes
from zensigil.syntax import parse


MATH = 'fn helper(n: number) -> number:\n    return n * 2\nexport fn double(n: number) -> number:\n    return helper(n)\n'


class NamespaceModuleTests(unittest.TestCase):
    def output(self, source, expected, modules=None, data=None, **kwargs):
        result = run(source, {} if data is None else data, modules=modules, **kwargs)
        self.assertTrue(result['ok'], result)
        self.assertEqual(json.dumps(result['values'], sort_keys=True), json.dumps(expected, sort_keys=True))
        return result

    def error(self, source, code, modules=None, data=None, **kwargs):
        result = run(source, {} if data is None else data, modules=modules, **kwargs)
        self.assertFalse(result['ok'], result)
        self.assertEqual(result['diagnostics'][0]['code'], code, result)
        self.assertEqual([result[key] for key in ('values', 'notes', 'proposals')], [[], [], []])
        return result['diagnostics'][0]

    def test_alias_calls_members_as_values_and_static_arity(self):
        modules = {'lib/math.zs': MATH}
        self.output('use "lib/math.zs" as math\nemit math.double(3)\nlet twice = math.double\nemit twice(4)\nemit map([1, 2], math.double)', [6, 8, [2, 4]], modules)
        self.error('use "lib/math.zs" as math\nemit math.double()', 'E_ARITY', modules)
        self.error('use "lib/math.zs" as math\nemit map([], math.double)', 'E_ARITY', {'lib/math.zs': 'export fn double(a, b):\n    return a + b'})

    def test_private_helpers_are_isolated_and_public_same_names_are_allowed(self):
        modules = {'add.zs': 'fn helper(n):\n    return n + 1\nexport fn apply(n):\n    return helper(n)',
                   'multiply.zs': 'fn helper(n):\n    return n * 10\nexport fn apply(n):\n    return helper(n)'}
        self.output('use "add.zs" as add\nuse "multiply.zs" as multiply\nemit [add.apply(2), multiply.apply(2)]\nemit add.apply == multiply.apply', [[3, 20], False], modules)
        self.error('use "add.zs"\nuse "multiply.zs"', 'E_DUPLICATE', modules)

    def test_explicit_exports_hide_helpers_in_aliased_and_bare_imports(self):
        modules = {'math.zs': MATH}
        self.output('use "math.zs"\nemit double(5)', [10], modules)
        for member in ('helper', 'missing'):
            with self.subTest(member=member):
                diagnostic = self.error('use "math.zs" as math\nwhen false:\n    emit math.' + member + '(1)', 'E_IMPORT', modules)
                self.assertEqual((diagnostic['source_name'], diagnostic['line']), ('<program>', 3))
                self.assertIn('exported', diagnostic['message'])
        self.error('use "math.zs"\nemit helper(1)', 'E_CALL', modules)
        self.error('use "math.zs" as math\nlet alias = math\nemit alias.helper(1)', 'E_IMPORT', modules)

    def test_unmarked_modules_remain_public_and_bare_imports_reexport(self):
        modules = {'inner.zs': 'fn helper(n):\n    return n + 2',
                   'outer.zs': 'use "inner.zs"\nfn wrapper(n):\n    return helper(n)'}
        self.output('use "outer.zs"\nemit [wrapper(1), helper(2)]', [[3, 4]], modules)
        self.output('use "outer.zs" as outer\nemit [outer.wrapper(1), outer.helper(2)]', [[3, 4]], modules)
        modules['outer.zs'] = 'use "inner.zs"\nexport fn wrapper(n):\n    return helper(n)'
        self.output('use "outer.zs" as outer\nemit outer.wrapper(1)', [3], modules)
        self.error('use "outer.zs" as outer\nemit outer.helper(2)', 'E_IMPORT', modules)

    def test_aliases_are_source_local_and_transitive_calls_keep_identity(self):
        modules = {'a.zs': 'fn value():\n    return 1', 'b.zs': 'fn value():\n    return 2',
                   'left.zs': 'use "a.zs" as tool\nexport fn value():\n    return tool.value()',
                   'right.zs': 'use "b.zs" as tool\nexport fn value():\n    return tool.value()'}
        self.output('use "left.zs" as left\nuse "right.zs" as right\nemit [left.value(), right.value()]', [[1, 2]], modules)
        self.error('use "left.zs" as left\nemit tool.value()', 'E_NAME', modules)
        self.error('use "left.zs" as left\nemit left.tool', 'E_IMPORT', modules)

    def test_same_module_aliases_and_diamond_imports_share_function_identity(self):
        modules = {'shared.zs': 'fn value():\n    return 1\ntest "shared":\n    require value() == 1, "bad"',
                   'a.zs': 'use "shared.zs"\nfn a():\n    return value()',
                   'b.zs': 'use "shared.zs"\nfn b():\n    return value()'}
        source = 'use "a.zs"\nuse "b.zs"\nuse "shared.zs" as first\nuse "shared.zs" as second\nemit [value == first.value, first.value == second.value, first == second]\nemit [a(), b()]'
        self.output(source, [[True, True, True], [1, 1]], modules)
        result = run_tests(source, modules=modules)
        self.assertTrue(result['ok'], result)
        self.assertEqual(result['total'], 1)

    def test_alias_binding_collisions_and_import_alias_immutability(self):
        modules = {'math.zs': MATH}
        sources = ['use "math.zs" as abs', 'use "math.zs" as math\nuse "math.zs" as math',
                   'use "math.zs" as math\nfn math():\n    return 1',
                   'use "math.zs" as math\nlet math = 1',
                   'use "math.zs" as math\nfn f(math):\n    return math',
                   'use "math.zs" as math\nlet f = fn (math) => math',
                   'use "math.zs" as double\nuse "math.zs"']
        for source in sources:
            with self.subTest(source=source):
                self.error(source, 'E_DUPLICATE', modules)
        self.error('use "math.zs" as math\nset math = 1', 'E_MUTABILITY', modules)
        self.error('use "math.zs" as math\nemit 1', 'E_INPUT', modules, {'math': 1})

    def test_private_names_in_other_modules_do_not_reserve_root_bindings(self):
        self.output('use "math.zs" as math\nemit helper\nemit math.double(3)', [9, 6], {'math.zs': MATH}, {'helper': 9})
        self.output('use "math.zs" as math\nfn helper(n):\n    return n + 1\nemit [helper(3), math.double(3)]', [[4, 6]], {'math.zs': MATH})

    def test_namespaces_have_opaque_type_and_immutable_value_semantics(self):
        modules = {'math.zs': MATH}
        source = 'use "math.zs" as math\nlet ns: namespace = math\nfn invoke(ns: namespace, n):\n    return ns.double(n)\nemit type_of(ns)\nemit invoke(ns, 3)\nlet closure = fn (n) => ns.double(n)\nemit closure(4)'
        self.output(source, ['namespace', 6, 8], modules)
        for expression in ['math', '[math]', '{library: math}', 'text(math)', 'json_text(math)']:
            with self.subTest(expression=expression):
                self.error('use "math.zs" as math\nemit ' + expression, 'E_VALUE', modules)
        for expression in ['len(math)', 'get(math, "double", null)', 'has(math, "double")', 'record_keys(math)', 'math["double"]']:
            with self.subTest(expression=expression):
                self.error('use "math.zs" as math\nemit ' + expression, 'E_TYPE', modules)
        self.error('use "math.zs" as math\nlet ns: record = math', 'E_TYPE', modules)
        self.error('let ns: namespace = {}', 'E_TYPE')
        self.error('use "math.zs" as math\nemit math()', 'E_CALL', modules)

    def test_closures_and_returned_function_capabilities_preserve_module_scope(self):
        modules = {'offset.zs': 'fn helper(n):\n    return n + 10\nexport fn make(base):\n    return fn (n) => helper(base + n)\nexport fn helper_ref():\n    return helper',
                   'wrapper.zs': 'use "offset.zs" as offset\nexport fn make(base):\n    return fn (n) => offset.make(base)(n)'}
        source = 'use "wrapper.zs" as wrapper\nuse "offset.zs" as offset\nlet first = wrapper.make(2)\nlet second = offset.helper_ref()\nemit first(3)\nemit second(4)\nemit map([1, 2], fn (n) => first(n))'
        self.output(source, [15, 14, [13, 14]], modules)

    def test_named_functions_stay_pure_and_cannot_capture_importer_functions(self):
        self.error('use "bad.zs" as bad\nemit bad.value()', 'E_NAME', {'bad.zs': 'export fn value():\n    return input_value'}, {'input_value': 1})
        self.error('fn supplied():\n    return 1\nuse "bad.zs" as bad\nemit bad.value()', 'E_CALL', {'bad.zs': 'export fn value():\n    return supplied()'})
        self.error('use "bad.zs" as bad', 'E_PURITY', {'bad.zs': 'export fn value():\n    emit 1'})
        self.error('use "bad.zs" as bad', 'E_IMPORT', {'bad.zs': 'let cache = 1'})

    def test_export_markers_are_valid_only_on_top_level_named_functions(self):
        for source in ['export let n = 1', 'export fn (n) => n', 'export use "math.zs"', 'export export fn f():\n    return 1']:
            with self.subTest(source=source):
                result = run(source, {})
                self.assertFalse(result['ok'], result)
                self.assertIn(result['diagnostics'][0]['code'], ('E_IMPORT', 'E_SYNTAX'))
        self.error('when true:\n    export fn f():\n        return 1', 'E_IMPORT')
        self.error('fn outer():\n    export fn inner():\n        return 1', 'E_IMPORT')
        self.output('export fn double(n):\n    return n * 2\nemit double(3)', [6])
        self.error('export fn abs(n):\n    return n', 'E_DUPLICATE')
        self.error('use "math.zs" as math\nwhen true:\n    use "math.zs" as other', 'E_IMPORT', {'math.zs': MATH})

    def test_namespace_imports_and_functions_are_hoisted_within_source(self):
        source = 'fn evaluate(n):\n    return math.double(n)\nemit evaluate(3)\nuse "math.zs" as math'
        self.output(source, [6], {'math.zs': MATH})

    def test_imported_error_locations_call_traces_and_atomic_outputs(self):
        modules = {'lib.zs': 'fn helper(n):\n    return 1 / n\nexport fn divide(n):\n    return helper(n)'}
        error = self.error('use "lib.zs" as lib\nemit 9\nsay "discard"\nemit lib.divide(0)', 'E_ZERO', modules)
        self.assertEqual((error['source_name'], error['line'], error['source_line']), ('lib.zs', 2, '    return 1 / n'))
        self.assertEqual([frame['function'] for frame in error['call_trace']], ['lib.zs::helper', 'lib.zs::divide'])
        error = self.error('use "outer.zs" as outer', 'E_IMPORT', {'outer.zs': 'use "math.zs" as math\nexport fn run():\n    return math.private()', 'math.zs': MATH})
        self.assertEqual((error['source_name'], error['line']), ('outer.zs', 3))

    def test_module_test_labels_are_source_scoped_and_private_helpers_remain_available(self):
        modules = {name: 'fn helper():\n    return 1\nexport fn value():\n    return helper()\ntest "works":\n    require helper() == 1, "bad"' for name in ['a.zs', 'b.zs']}
        result = run_tests('use "a.zs" as a\nuse "b.zs" as b\ntest "works":\n    require a.value() == b.value(), "bad"', modules=modules)
        self.assertTrue(result['ok'], result)
        self.assertEqual(result['total'], 3)
        self.assertEqual({case['source_name'] for case in result['tests']}, {'a.zs', 'b.zs', '<program>'})
        self.error('test "same":\n    require true, "yes"\ntest "same":\n    require true, "yes"', 'E_DUPLICATE')

    def test_alias_import_cycles_depth_limits_and_cached_paths(self):
        self.error('use "a.zs" as a', 'E_IMPORT', {'a.zs': 'use "b.zs" as b', 'b.zs': 'use "a.zs" as a'})
        modules = {f'n{i}.zs': f'use "n{i+1}.zs" as child\nexport fn value():\n    return child.value() + 1' for i in range(7)}
        modules['n7.zs'] = 'export fn value():\n    return 0'
        self.output('use "n7.zs" as leaf\nuse "n0.zs" as chain\nemit chain.value()', [7], modules)
        modules['outer.zs'] = 'use "n0.zs" as chain\nexport fn value():\n    return chain.value()'
        self.error('use "n7.zs" as leaf\nuse "outer.zs" as outer', 'E_IMPORT', modules)
        self.error('use "../escape.zs" as escape', 'E_IMPORT')
        self.error('use "missing.zs" as missing', 'E_IMPORT')

    def test_function_and_namespace_work_stays_bounded(self):
        module = 'export fn recur(n):\n    return recur(n + 1)'
        self.error('use "loop.zs" as loop\nemit loop.recur(0)', 'E_LIMIT', {'loop.zs': module})
        self.error('use "math.zs" as math\nfor n in range(100):\n    let value = math.double(n)', 'E_LIMIT', {'math.zs': MATH}, max_steps=50)
        # Repeated aliases reuse one immutable namespace/export index.
        source = '\n'.join('use "math.zs" as alias' + str(i) for i in range(100))
        program, _ = compile_program(source, {'math.zs': MATH})
        aliases = module_scopes(program)['<program>']['namespaces']
        self.assertEqual(len({id(value) for value in aliases.values()}), 1)

    def test_ast_formatter_and_compiler_metadata_contract(self):
        self.assertEqual(len(parse('use "math.zs"')[0].parts), 1)
        self.assertEqual(len(parse('fn f():\n    return 1')[0].parts), 5)
        source = 'use "math.zs" as math\nexport fn apply(n:number)->number:\n    return math.double(n)\nemit apply(2)\n'
        parsed = parse(source)
        self.assertEqual(parsed[0].parts[1].value, 'math')
        self.assertTrue(parsed[1].parts[5])
        formatted = format_source(source)
        self.assertEqual(semantic_tree(parse(source)), semantic_tree(parse(formatted)))
        self.assertEqual(format_source(formatted), formatted)
        self.output(formatted, [4], {'math.zs': MATH})
        self.assertTrue(ast_document(source)['body'][1]['parts'][5])
        program, sources = compile_program(source, {'math.zs': MATH})
        ids = {function_identity(node) for node in program if node.kind == 'fn'}
        self.assertEqual(ids, {'apply', 'math.zs::helper', 'math.zs::double'})
        self.assertEqual(set(module_scopes(program)), {'math.zs', '<program>'})
        self.assertEqual(sources['math.zs'], MATH)
        with self.assertRaises(Exception) as caught:
            Checker(parsed, []).check(parsed)
        self.assertEqual(caught.exception.code, 'E_IMPORT')

    def test_explicit_file_loading_supports_aliases_and_rejects_symlink_loops(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            entry = root / 'main.zs'
            entry.write_text('use "math.zs" as math\nemit math.double(2)')
            (root / 'math.zs').write_text(MATH)
            modules = file_modules(entry.read_text(), entry)
            self.output(entry.read_text(), [4], modules)
            with patch('pathlib.Path.open', side_effect=AssertionError('Implicit I/O')):
                self.error('use "math.zs" as math', 'E_IMPORT')
            try:
                (root / 'loop.zs').symlink_to(root / 'other.zs')
                (root / 'other.zs').symlink_to(root / 'loop.zs')
            except OSError:
                self.skipTest('Symlinks unavailable')
            from zensigil.errors import SigilError
            with self.assertRaises(SigilError) as caught:
                file_modules('use "loop.zs" as loop', entry)
            self.assertEqual(caught.exception.code, 'E_IMPORT')


if __name__ == '__main__':
    unittest.main()
