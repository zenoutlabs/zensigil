"""Conservative advisory checks over lexically scoped syntax; never executes code."""
from .syntax import Node


def warnings(program):
    found = []

    def report(code, token, message):
        found.append({'code': code, 'severity': 'warning', 'message': message,
                      'line': token.line, 'column': token.column,
                      'source_name': token.source_name or '<program>'})

    def expression(node, scopes):
        if not isinstance(node, Node):
            return
        if node.kind == 'name':
            for scope in reversed(scopes):
                if node.parts[0] in scope:
                    scope[node.parts[0]]['used'] = True
                    break
            return
        if node.kind == 'lambda':
            parameters, body = node.parts[:2]
            inner = {}
            for token in parameters:
                declare(token, scopes + [inner])
            expression(body, scopes + [inner])
            finish(inner)
            return
        def walk(value):
            if isinstance(value, Node):
                expression(value, scopes)
            elif isinstance(value, tuple):
                for item in value:
                    walk(item)
        walk(node.parts)

    def declare(token, scopes):
        if any(token.value in scope for scope in scopes[:-1]) and not token.value.startswith('_'):
            report('W_SHADOW', token, f'{token.value!r} shadows a binding in an outer block.')
        scopes[-1][token.value] = {'token': token, 'used': False}

    def finish(scope):
        for name, binding in scope.items():
            if not binding['used'] and not name.startswith('_'):
                report('W_UNUSED', binding['token'], f'{name!r} is declared but never read; prefix an intentional placeholder with _.')

    def block(body, outer, parameters=()):
        local = {}
        scopes = outer + [local]
        for parameter in parameters:
            declare(parameter, scopes)
        terminated = False
        for node in body:
            kind, parts = node.kind, node.parts
            if terminated:
                report('W_UNREACHABLE', node.token, 'This statement follows unconditional control transfer and cannot run.')
            if kind in {'let', 'var'}:
                expression(parts[1], scopes)
                declare(parts[0], scopes)
            elif kind == 'set':
                expression(parts[1], scopes)
            elif kind == 'fn':
                block(parts[2], [], parts[1])
            elif kind in {'rule', 'test'}:
                block(parts[1], [] if kind == 'test' else scopes)
            elif kind == 'when':
                expression(parts[0], scopes)
                yes = block(parts[1], scopes)
                no = block(parts[2], scopes) if parts[2] else False
                terminated = terminated or (yes and no)
            elif kind == 'for':
                expression(parts[1], scopes)
                block(parts[2], scopes, (parts[0],))
            elif kind == 'while':
                expression(parts[0], scopes)
                block(parts[1], scopes)
            else:
                for value in parts:
                    if kind == 'propose' and isinstance(value, tuple):
                        for _, child in value:
                            expression(child, scopes)
                    else:
                        expression(value, scopes)
            if kind in {'return', 'break', 'continue'}:
                terminated = True
        finish(local)
        return terminated

    block(program, [])
    return sorted(found, key=lambda item: (item['source_name'], item['line'], item['column'], item['code']))


def lint(source, data=None, *, modules=None, contract=None, proposal_contract=None):
    from . import check, located, __version__
    from .modules import compile_program
    result = check(source, data, modules=modules, contract=contract, proposal_contract=proposal_contract)
    result.update(mode='lint', warnings=[])
    if result['ok']:
        program, _ = compile_program(source, modules)
        from .type_lint import warnings as type_warnings
        combined = warnings(program) + type_warnings(program)
        combined.sort(key=lambda item: (item['source_name'], item['line'], item['column'], item['code']))
        result['warnings'] = [located(item, source, modules) for item in combined]
    result['version'] = __version__
    return result
