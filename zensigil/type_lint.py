"""Bounded, advisory type checks. Unknown values are never treated as errors.

This pass reads syntax and runtime annotations. It does not evaluate expressions,
infer callback results, or change the binding checker and runtime contract.
"""
from dataclasses import dataclass

from .checker import BUILTINS
from .modules import function_identity, module_scopes
from .typesys import type_text


@dataclass(frozen=True)
class Fact:
    kinds: object = None
    children: object = None
    signature: object = None
    namespace: object = None


UNKNOWN = Fact()
NUMERIC = frozenset({'integer', 'decimal'})
BUILTIN_SIGNATURES = {
    'len': ((('union', ('list', 'record', 'string')),), 'integer'),
    'has': (('record', 'string'), 'boolean'),
    'get': (('record', 'string', None), None),
    'text': ((None,), 'string'),
    'ceil': (('number',), 'integer'), 'floor': (('number',), 'integer'),
    'abs': (('number',), 'number'),
    'min': (('number', 'number'), 'number'), 'max': (('number', 'number'), 'number'),
    'fraction': (('number',), 'record'), 'ceil_div': (('integer', 'integer'), 'integer'),
    'round': (('number', 'integer'), 'number'), 'type_of': ((None,), 'string'),
}


def known(*kinds, **details):
    return Fact(frozenset(kinds), **details)


def annotation_fact(annotation):
    if annotation in (None, 'any'):
        return UNKNOWN
    if type(annotation) is tuple:
        kind, inner = annotation
        return join(annotation_fact(item) for item in inner) if kind == 'union' else known(kind)
    return Fact(NUMERIC) if annotation == 'number' else known(annotation)


def join(facts):
    facts = tuple(facts)
    if not facts or any(fact.kinds is None for fact in facts):
        return UNKNOWN
    return Fact(frozenset().union(*(fact.kinds for fact in facts)))


class AnalysisLimit(Exception):
    pass


class TypeLint:
    def __init__(self, program):
        self.scopes = module_scopes(program)
        self.functions = {function_identity(node): node for node in program if node.kind == 'fn'}
        self.found, self.visits, self.depth = [], 0, 0
        self.last_token = program[0].token if program else None

    def tick(self, token=None):
        self.visits += 1
        if token is not None:
            self.last_token = token
        if self.visits > 100000 or len(self.found) >= 200:
            raise AnalysisLimit()

    def report(self, token, message, code='W_TYPE'):
        self.found.append({'code': code, 'severity': 'warning', 'message': message,
                           'line': token.line, 'column': token.column,
                           'source_name': token.source_name or '<program>'})

    def impossible(self, fact, annotation):
        """True only when no value described by this fact can match the type."""
        self.tick()
        if fact.kinds is None or annotation in (None, 'any'):
            return False
        if type(annotation) is tuple and annotation[0] == 'union':
            return all(self.impossible(fact, item) for item in annotation[1])
        expected = annotation_fact(annotation).kinds
        if fact.kinds.isdisjoint(expected):
            return True
        if type(annotation) is tuple and fact.kinds == frozenset({annotation[0]}) and fact.children is not None:
            return any(self.impossible(child, annotation[1]) for child in fact.children)
        return False

    def expect(self, fact, annotation, token, label):
        if self.impossible(fact, annotation):
            self.report(token, f'{label} cannot have type {type_text(annotation)}. Check the value or its annotation.')

    def lookup(self, name, token, scopes):
        for scope in reversed(scopes):
            if name in scope:
                return scope[name][0]
        environment = self.scopes.get(token.source_name or '<program>', {})
        if name in environment.get('namespaces', {}):
            return known('namespace', namespace=environment['namespaces'][name])
        identity = environment.get('functions', {}).get(name)
        if identity in self.functions:
            node = self.functions[identity]
            return known('function', signature=(node.parts[3], node.parts[4]))
        if name in BUILTINS:
            return known('function', signature=BUILTIN_SIGNATURES.get(name))
        return UNKNOWN

    def expr(self, node, scopes):
        self.tick(node.token)
        self.depth += 1
        try:
            if self.depth > 128:
                raise AnalysisLimit()
            return self.expression(node, scopes)
        finally:
            self.depth -= 1

    def expression(self, node, scopes):
        kind, parts, token = node.kind, node.parts, node.token
        if kind == 'literal':
            return known({bool: 'boolean', int: 'integer', float: 'decimal', str: 'string', type(None): 'null'}[type(parts[0])])
        if kind == 'name':
            return self.lookup(parts[0], token, scopes)
        if kind in {'list', 'record'}:
            children = tuple(self.expr(value[1] if kind == 'record' else value, scopes) for value in parts[0])
            return known(kind, children=children)
        if kind == 'lambda':
            parameters, body, annotations, result = parts
            inner = {parameter.value: (annotation_fact(annotation), annotation)
                     for parameter, annotation in zip(parameters, annotations)}
            self.expect(self.expr(body, scopes + [inner]), result, body.token, 'Function result')
            return known('function', signature=(annotations, result))
        if kind == 'field':
            base = self.expr(parts[0], scopes)
            if base.namespace is not None:
                identity = base.namespace.member(parts[1])
                if identity in self.functions:
                    node = self.functions[identity]
                    return known('function', signature=(node.parts[3], node.parts[4]))
            self.expect(base, ('union', ('record', 'namespace')), token, 'Field access')
            return UNKNOWN
        if kind == 'call':
            callee = self.expr(parts[0], scopes)
            arguments = tuple(self.expr(arg, scopes) for arg in parts[1])
            self.expect(callee, 'function', token, 'Called value')
            if callee.signature is not None:
                parameters, result = callee.signature
                if len(arguments) != len(parameters):
                    self.report(token, f'This function needs {len(parameters)} argument(s), but the call supplies {len(arguments)}.')
                for index, (argument, annotation) in enumerate(zip(arguments, parameters), 1):
                    self.expect(argument, annotation, parts[1][index - 1].token, f'Argument {index}')
                return annotation_fact(result)
            return UNKNOWN
        if kind == 'choose':
            self.expect(self.expr(parts[0], scopes), 'boolean', parts[0].token, 'Condition')
            return join((self.expr(parts[1], scopes), self.expr(parts[2], scopes)))
        if kind == 'unary':
            value = self.expr(parts[1], scopes)
            self.expect(value, 'boolean' if parts[0] == 'not' else 'number', token, 'Operand')
            return known('boolean') if parts[0] == 'not' else value
        if kind == 'binary':
            op, left, right = parts
            a, b = self.expr(left, scopes), self.expr(right, scopes)
            if op == '??':
                if a.kinds is None:
                    return UNKNOWN
                if 'null' not in a.kinds:
                    return a
                return join((Fact(a.kinds - {'null'}), b))
            if op in {'and', 'or'}:
                self.expect(a, 'boolean', left.token, 'Logical operand')
                self.expect(b, 'boolean', right.token, 'Logical operand')
                return known('boolean')
            if op in {'==', '!='}:
                return known('boolean')
            if op in {'in', 'not in'}:
                self.expect(b, ('union', ('list', 'record', 'string')), right.token, 'Membership collection')
                if b.kinds is not None and b.kinds <= {'record', 'string'}:
                    self.expect(a, 'string', left.token, 'Membership key')
                return known('boolean')
            if op in {'<', '<=', '>', '>='}:
                pairs = [(NUMERIC, NUMERIC), ({'string'}, {'string'})]
            elif op == '+':
                pairs = [(NUMERIC, NUMERIC), ({'string'}, {'string'}), ({'list'}, {'list'})]
            else:
                pairs = [(NUMERIC, NUMERIC)]
            possible = [(x, y) for x, y in pairs if (a.kinds is None or not a.kinds.isdisjoint(x))
                        and (b.kinds is None or not b.kinds.isdisjoint(y))]
            if not possible:
                self.report(token, f'These operand types cannot use {op!r}. Use compatible value types.')
            if op in {'<', '<=', '>', '>='}:
                return known('boolean')
            if not possible or a.kinds is None or b.kinds is None:
                return UNKNOWN
            if op == '/' or a.kinds != {'integer'} or b.kinds != {'integer'}:
                return Fact(frozenset().union(*(x for x, _ in possible)))
            return known('integer')
        if kind == 'index':
            base, index = (self.expr(value, scopes) for value in parts)
            self.expect(base, ('union', ('list', 'record', 'string')), token, 'Indexed value')
            if base.kinds is not None and base.kinds <= {'list', 'string'}:
                self.expect(index, 'integer', parts[1].token, 'Sequence index')
            elif base.kinds == {'record'}:
                self.expect(index, 'string', parts[1].token, 'Record key')
            return known('string') if base.kinds == {'string'} else UNKNOWN
        if kind == 'slice':
            base = self.expr(parts[0], scopes)
            self.expect(base, ('union', ('list', 'string')), token, 'Sliced value')
            for value in parts[1:]:
                if value is not None:
                    self.expect(self.expr(value, scopes), 'integer', value.token, 'Slice bound')
            return Fact(base.kinds)
        return UNKNOWN

    def block(self, body, scopes, result=None):
        self.depth += 1
        try:
            if self.depth > 128:
                raise AnalysisLimit()
            self.statements(body, scopes, result)
        finally:
            self.depth -= 1

    def statements(self, body, scopes, result):
        for node in body:
            self.tick(node.token)
            kind, parts, token = node.kind, node.parts, node.token
            if kind in {'let', 'var'}:
                value = self.expr(parts[1], scopes)
                annotation = parts[2]
                self.expect(value, annotation, token, 'Binding value')
                # Mutable values may change on any branch or loop iteration.
                # Only runtime-enforced annotations remain valid in all paths.
                fact = annotation_fact(annotation) if annotation is not None or kind == 'var' else value
                scopes[-1][parts[0].value] = (fact, annotation)
            elif kind == 'set':
                value = self.expr(parts[1], scopes)
                binding = next((scope[parts[0].value] for scope in reversed(scopes) if parts[0].value in scope), (UNKNOWN, None))
                self.expect(value, binding[1], token, 'Assigned value')
            elif kind == 'fn':
                inner = {parameter.value: (annotation_fact(annotation), annotation)
                         for parameter, annotation in zip(parts[1], parts[3])}
                self.block(parts[2], [inner], parts[4])
            elif kind in {'rule', 'test'}:
                self.block(parts[1], [{}] if kind == 'test' else scopes + [{}])
            elif kind in {'when', 'while'}:
                self.expect(self.expr(parts[0], scopes), 'boolean', parts[0].token, 'Condition')
                for branch in parts[1:]:
                    self.block(branch, scopes + [{}], result)
            elif kind == 'for':
                self.expect(self.expr(parts[1], scopes), 'list', parts[1].token, 'Loop sequence')
                self.block(parts[2], scopes + [{parts[0].value: (UNKNOWN, None)}], result)
            elif kind == 'require':
                self.expect(self.expr(parts[0], scopes), 'boolean', parts[0].token, 'Required condition')
                self.expect(self.expr(parts[1], scopes), 'string', parts[1].token, 'Failure message')
            elif kind in {'say', 'return', 'emit'}:
                value = self.expr(parts[0], scopes)
                if kind != 'emit':
                    self.expect(value, 'string' if kind == 'say' else result, token, 'Note' if kind == 'say' else 'Function result')
            elif kind == 'propose':
                for _, value in parts[1]:
                    self.expr(value, scopes)


def warnings(program):
    analysis = TypeLint(program)
    try:
        analysis.block(program, [{}])
    except (AnalysisLimit, RecursionError):
        if analysis.last_token is not None:
            analysis.report(analysis.last_token, 'Type advice stopped at its analysis limit. Some expressions were not checked.', 'W_TYPE_LIMIT')
    return analysis.found
