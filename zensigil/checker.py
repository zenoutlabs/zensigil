"""Lexical binding, purity and control-flow checks, including untaken branches."""
from .errors import fail, SigilError
from .syntax import WORDS, IDENT
from .modules import function_identity, module_scopes

BUILTINS = {"len": 1, "has": 2, "get": 3, "text": 1, "ceil": 1, "floor": 1,
            "abs": 1, "min": 2, "max": 2, "fraction": 1, "ceil_div": 2, "round": 2}
try:
    from .stdlib import ARITIES
    BUILTINS.update(ARITIES)
except ImportError:
    pass

class Checker:
    def __init__(self, program, input_names=None):
        self.functions, self.possible_inputs = {}, set()
        self.module_scopes = module_scopes(program)
        self.allow_inputs = input_names is None
        self.inputs = set(input_names or ())
        for node in program:
            if node.kind == 'fn':
                name, identity = node.parts[0], function_identity(node)
                if identity in self.functions or name.value in BUILTINS:
                    fail(name, 'E_DUPLICATE', f'Name {name.value!r} is already defined or reserved.')
                if name.source_name in ('', '<program>') and name.value in self.inputs:
                    fail(name, 'E_DUPLICATE', f'Name {name.value!r} is already defined or reserved.')
                self.functions[identity] = node
        self.reserved = WORDS | set(BUILTINS)
        self.source_reserved = {name: self.reserved | set(scope['functions']) | set(scope['namespaces'])
                                for name, scope in self.module_scopes.items()}
        root = self.module_scopes.get('<program>', {'functions': {}, 'namespaces': {}})
        root_names = set(root['functions']) | set(root['namespaces'])
        for name in self.inputs:
            if not IDENT.fullmatch(name) or name in self.reserved or name in root_names:
                raise SigilError('E_INPUT', f'Input key {name!r} must be a nonreserved identifier.')
        self.rules, self.tests = set(), set()

    def environment(self, token):
        return self.module_scopes.get(token.source_name or '<program>', {'functions': {}, 'namespaces': {}})

    def reserved_at(self, token):
        return self.source_reserved.get(token.source_name or '<program>', self.reserved)

    def static_function(self, node):
        environment = self.environment(node.token)
        if node.kind == 'name':
            name = node.parts[0]
            return name if name in BUILTINS else environment['functions'].get(name)
        if node.kind == 'field' and node.parts[0].kind == 'name':
            base = node.parts[0]
            namespace = self.environment(base.token)['namespaces'].get(base.parts[0])
            if namespace is not None:
                return namespace.member(node.parts[1])
        return None

    def bind(self, token, scopes, mutable=False):
        if token.value in scopes[-1] or token.value in self.reserved_at(token):
            fail(token, 'E_DUPLICATE', f'Name {token.value!r} is already defined in this block or reserved.')
        scopes[-1][token.value] = mutable

    def block(self, body, scopes, in_function=False, top=False, loop=0, in_test=False):
        for node in body:
            kind, parts = node.kind, node.parts
            if kind == 'module_scope':
                continue
            if kind in {'let', 'var'}:
                self.expr(parts[1], scopes, in_function or in_test)
                self.bind(parts[0], scopes, kind == 'var')
            elif kind == 'set':
                self.expr(parts[1], scopes, in_function or in_test)
                scope = next((s for s in reversed(scopes) if parts[0].value in s), None)
                if scope is None and parts[0].value in self.environment(parts[0])['namespaces']:
                    fail(parts[0], 'E_MUTABILITY', 'Import aliases are immutable namespace bindings.')
                if scope is None:
                    fail(parts[0], 'E_NAME', f'Unknown variable {parts[0].value!r}.')
                if not scope[parts[0].value]:
                    fail(parts[0], 'E_MUTABILITY', "Only a 'var' binding can be changed with 'set'.")
            elif kind == 'require':
                for expression in parts:
                    self.expr(expression, scopes, in_function or in_test)
            elif kind in {'say', 'return', 'emit'}:
                if kind == 'return' and not in_function:
                    fail(node.token, 'E_SCOPE', "'return' belongs inside a function.")
                if kind in {'say', 'emit'} and (in_function or in_test):
                    fail(node.token, 'E_PURITY', f"Pure bodies cannot use '{kind}'.")
                self.expr(parts[0], scopes, in_function or in_test)
            elif kind == 'propose':
                if in_function or in_test:
                    fail(node.token, 'E_PURITY', 'Pure bodies cannot propose actions.')
                for _, value in parts[1]:
                    self.expr(value, scopes, False)
            elif kind == 'when':
                self.expr(parts[0], scopes, in_function or in_test)
                for branch in parts[1:]:
                    self.block(branch, scopes + [{}], in_function, loop=loop, in_test=in_test)
            elif kind == 'for':
                self.expr(parts[1], scopes, in_function or in_test)
                inner = scopes + [{}]
                self.bind(parts[0], inner)
                self.block(parts[2], inner, in_function, loop=loop+1, in_test=in_test)
            elif kind == 'while':
                self.expr(parts[0], scopes, in_function or in_test)
                self.block(parts[1], scopes + [{}], in_function, loop=loop+1, in_test=in_test)
            elif kind in {'break', 'continue'}:
                if not loop:
                    fail(node.token, 'E_SCOPE', f"'{kind}' belongs inside a loop in this function.")
            elif kind in {'rule', 'test'}:
                if not top:
                    fail(node.token, 'E_SCOPE', f'Declare {kind}s at the top level.')
                labels = self.rules if kind == 'rule' else self.tests
                label = (node.token.source_name, parts[0]) if kind == 'test' else parts[0]
                if label in labels:
                    fail(node.token, 'E_DUPLICATE', f'{kind.title()} label {parts[0]!r} is repeated.')
                labels.add(label)
                self.block(parts[1], [{}] if kind == 'test' else scopes + [{}], in_test=kind == 'test')
            elif kind == 'fn':
                if not top:
                    fail(node.token, 'E_IMPORT' if len(parts) > 5 and parts[5] else 'E_SCOPE', 'Declare and export functions only at the top level.')
                inner = [{}]
                for parameter in parts[1]:
                    self.bind(parameter, inner)
                self.block(parts[2], inner, True)
            elif kind == 'use':
                fail(node.token, 'E_IMPORT', 'Resolve top-level use declarations through a project loader before checking.')
            else:
                fail(node.token, 'E_SYNTAX', f'Unsupported statement {kind!r}.')

    def expr(self, node, scopes, pure):
        kind, parts = node.kind, node.parts
        if kind == 'name':
            name = parts[0]
            environment = self.environment(node.token)
            if name in BUILTINS or name in environment['functions'] or name in environment['namespaces']:
                return
            if not any(name in scope for scope in reversed(scopes)):
                if self.allow_inputs and not pure and name not in self.reserved_at(node.token):
                    self.possible_inputs.add(name)
                else:
                    fail(node.token, 'E_NAME', f'Unknown variable {name!r}. Check its spelling and scope.')
        elif kind == 'lambda':
            # Lambda bodies share the enclosing lexical visibility. Root expressions
            # may capture supplied inputs; named functions/tests keep their isolation.
            inner = scopes + [{}]
            for parameter in parts[0]:
                self.bind(parameter, inner)
            self.expr(parts[1], inner, pure)
        elif kind == 'call':
            callee, args = parts
            if callee.kind == 'name':
                name = callee.parts[0]
                environment = self.environment(callee.token)
                if name not in BUILTINS and name not in environment['functions'] and name not in environment['namespaces'] and not any(name in scope for scope in scopes):
                    fail(callee.token, 'E_CALL', f'Unknown function {name!r}.')
            self.expr(callee, scopes, pure)
            identity = self.static_function(callee)
            if identity is not None:
                arity = BUILTINS[identity] if identity in BUILTINS else len(self.functions[identity].parts[1])
                accepted = (arity,) if type(arity) is int else arity
                if len(args) not in accepted:
                    fail(node.token, 'E_ARITY', f'{identity} expects {arity} argument(s), received {len(args)}.')
            for arg in args:
                self.expr(arg, scopes, pure)
        elif kind in {'unary', 'field'}:
            self.expr(parts[1] if kind == 'unary' else parts[0], scopes, pure)
            if kind == 'field' and parts[0].kind == 'name':
                namespace = self.environment(parts[0].token)['namespaces'].get(parts[0].parts[0])
                if namespace is not None and namespace.member(parts[1]) is None:
                    fail(node.token, 'E_IMPORT', f'Module {namespace.path!r} has no exported function {parts[1]!r}.')
        elif kind in {'binary', 'index', 'slice', 'choose'}:
            for value in (parts[1:] if kind == 'binary' else parts):
                if value is not None:
                    self.expr(value, scopes, pure)
        elif kind in {'list', 'record'}:
            for value in parts[0]:
                self.expr(value[1] if kind == 'record' else value, scopes, pure)

    def check(self, program):
        self.block(program, [{name: False for name in self.inputs}], top=True)
        return sorted(self.possible_inputs)
