"""Explicit pure source modules. The language API never reads files implicitly."""
from dataclasses import replace
from pathlib import Path, PurePosixPath
import re

from .errors import SigilError, fail
from .syntax import Node, Token, parse
from .typesys import NamespaceRef

MAX_MODULES = 32
MAX_MODULE_BYTES = 262144
MAX_MODULE_DEPTH = 8
SEGMENT = re.compile(r'[A-Za-z0-9_][A-Za-z0-9_.-]*')


def module_name(name):
    if (type(name) is not str or not name or len(name) > 160 or '\\' in name
            or not name.endswith('.zs') or name.startswith('/')
            or any(part in ('', '.', '..') or not SEGMENT.fullmatch(part) for part in name.split('/'))):
        raise SigilError('E_IMPORT', 'Module names must be root-relative .zs paths with plain names; no absolute paths, backslashes or parent traversal.')
    return name


def validate_modules(modules):
    if modules is None:
        return {}
    if type(modules) is not dict or len(modules) > MAX_MODULES:
        raise SigilError('E_IMPORT', 'Provide at most 32 named source modules in an object.')
    total, names = 0, set()
    for name, source in modules.items():
        module_name(name)
        if name.casefold() in names:
            raise SigilError('E_IMPORT', 'Module names must also be unique when ignoring letter case.')
        if any(name.casefold().startswith(other + "/") or other.startswith(name.casefold() + "/") for other in names):
            raise SigilError("E_IMPORT", "A module path cannot be both a source file and another module's directory.")
        names.add(name.casefold())
        if type(source) is not str:
            raise SigilError('E_IMPORT', f'Module {name!r} must contain source text.')
        try:
            size = len(source.encode('utf-8'))
        except UnicodeError:
            raise SigilError('E_IMPORT', f'Module {name!r} must contain valid Unicode text.')
        total += size
        if size > 65536 or total > MAX_MODULE_BYTES:
            raise SigilError('E_IMPORT', 'Modules allow 64 KiB per file and 256 KiB in total.')
    return dict(modules)


def named_tree(value, name):
    if isinstance(value, Token):
        return replace(value, source_name=name)
    if isinstance(value, Node):
        return replace(value, token=named_tree(value.token, name), parts=named_tree(value.parts, name))
    if type(value) is tuple:
        return tuple(named_tree(item, name) for item in value)
    return value


def named_parse(source, name):
    try:
        return named_tree(parse(source), name)
    except SigilError as error:
        error.source_name = name
        raise


def import_error(node, message):
    error = SigilError('E_IMPORT', message, node.token.line, node.token.column)
    error.source_name = node.token.source_name
    raise error


def function_identity(node):
    """The source spelling remains parts[0]; compiled functions carry an identity."""
    return node.parts[6] if len(node.parts) > 6 else node.parts[0].value


def module_scopes(program):
    """Read compiler metadata without executing or rewriting source nodes."""
    scopes, namespaces_by_path = {}, {}
    for node in program:
        if node.kind == 'module_scope':
            name, functions, namespaces = node.parts
            aliases = {}
            for alias, path, members in namespaces:
                if path not in namespaces_by_path:
                    namespaces_by_path[path] = NamespaceRef(path, members)
                aliases[alias] = namespaces_by_path[path]
            scopes[name] = {'functions': dict(functions), 'namespaces': aliases}
    if not scopes:
        # Direct parser consumers retain the pre-module Runtime/Checker interface.
        functions = {node.parts[0].value: function_identity(node) for node in program if node.kind == 'fn'}
        for name in {'<program>'} | {node.token.source_name or '<program>' for node in program}:
            scopes[name] = {'functions': functions, 'namespaces': {}}
    return scopes


def compile_program(source, modules=None):
    from .checker import BUILTINS
    modules = validate_modules(modules)
    sources = dict(modules, **{'<program>': source})
    units, scopes, exports, heights, visiting = {}, {}, {}, {}, []
    namespaces_by_path = {}

    def visit(name, depth, edge=None):
        if depth > MAX_MODULE_DEPTH or (name in heights and depth + heights[name] > MAX_MODULE_DEPTH):
            if edge is not None:
                import_error(edge, 'Module imports exceed eight levels of nesting.')
            raise SigilError('E_IMPORT', 'Module imports exceed eight levels of nesting.')
        if name in visiting:
            import_error(edge, 'Import cycle: ' + ' -> '.join(visiting + [name]))
        if name in scopes:
            return
        nodes = named_parse(sources[name], name)
        units[name] = nodes
        visiting.append(name)
        own, marked = {}, {}
        for node in nodes:
            if node.kind == 'fn':
                token = node.parts[0]
                if token.value in own or token.value in BUILTINS:
                    fail(token, 'E_DUPLICATE', f'Name {token.value!r} is already defined or reserved.')
                identity = token.value if name == '<program>' else name + '::' + token.value
                own[token.value] = identity
                if len(node.parts) > 5 and node.parts[5]:
                    marked[token.value] = identity
            elif name != '<program>' and node.kind not in {'use', 'test'}:
                import_error(node, 'Imported modules may contain only pure functions, test blocks and use declarations.')
        functions, namespaces, height = dict(own), {}, 0
        for node in nodes:
            if node.kind != 'use':
                continue
            try:
                target = module_name(node.parts[0])
            except SigilError as error:
                import_error(node, error.message)
            if target not in modules:
                import_error(node, f'Module {target!r} was not supplied. Add it to the program bundle or project root.')
            visit(target, depth + 1, node)
            height = max(height, 1 + heights[target])
            if len(node.parts) > 1:
                alias = node.parts[1]
                if alias.value in functions or alias.value in namespaces or alias.value in BUILTINS:
                    fail(alias, 'E_DUPLICATE', f'Import alias {alias.value!r} conflicts with a function, built-in, or another alias.')
                if target not in namespaces_by_path:
                    namespaces_by_path[target] = NamespaceRef(target, tuple(exports[target].items()))
                namespaces[alias.value] = namespaces_by_path[target]
            else:
                for public, identity in exports[target].items():
                    if public in namespaces or (public in functions and functions[public] != identity):
                        fail(node.token, 'E_DUPLICATE', f'Imported function {public!r} conflicts with another binding. Use an import alias.')
                    functions[public] = identity
        scopes[name] = {'functions': functions, 'namespaces': namespaces}
        # A legacy module re-exports bare imports. Explicit export markers select
        # only its own marked declarations; aliases never become public members.
        exports[name] = marked if marked else dict(functions)
        heights[name] = height
        visiting.pop()

    visit('<program>', 0)
    result = []
    for name, scope in scopes.items():
        result.append(Node('module_scope', Token('module_scope', name, 1, 1, name),
                           (name, tuple(scope['functions'].items()),
                            tuple((alias, value.path, value.members) for alias, value in scope['namespaces'].items()))))
    emitted = set()

    def emit(name):
        if name in emitted:
            return
        emitted.add(name)
        for node in units[name]:
            if node.kind == 'use':
                emit(node.parts[0])
            elif node.kind == 'fn':
                exported = len(node.parts) > 5 and node.parts[5]
                result.append(replace(node, parts=node.parts[:5] + (bool(exported), scopes[name]['functions'][node.parts[0].value])))
            else:
                result.append(node)
    emit('<program>')
    return tuple(result), sources


def file_modules(source, source_path, root=None):
    """Host-only convenience for CLI projects; only explicitly named imports load."""
    try:
        source_path = Path(source_path).resolve()
        base = Path(root).resolve() if root is not None else source_path.parent
    except (OSError, RuntimeError):
        raise SigilError('E_IMPORT', 'The source path and module root must resolve without symlink loops.')
    if not base.is_dir() or not source_path.is_relative_to(base):
        raise SigilError('E_IMPORT', 'The source file must be inside its selected module root directory.')
    found, active = {}, []
    total = 0

    def visit(text, label, depth):
        nonlocal total
        if depth > MAX_MODULE_DEPTH:
            raise SigilError('E_IMPORT', 'Module imports exceed eight levels of nesting.')
        for node in named_parse(text, label):
            if node.kind != 'use':
                continue
            try:
                name = module_name(node.parts[0])
            except SigilError as error:
                import_error(node, error.message)
            if name in active:
                import_error(node, 'Import cycle: ' + ' -> '.join(active + [name]))
            if name in found:
                continue
            if len(found) >= MAX_MODULES:
                import_error(node, 'A project may load at most 32 modules.')
            try:
                path = (base / PurePosixPath(name)).resolve()
            except (OSError, RuntimeError):
                import_error(node, f'Module {name!r} could not be resolved without symlink loops.')
            if not path.is_relative_to(base) or not path.is_file():
                import_error(node, f'Module {name!r} must be an existing file inside the selected module root.')
            try:
                with path.open('rb') as handle:
                    raw = handle.read(65537)
                if len(raw) > 65536:
                    import_error(node, f'Module {name!r} exceeds 64 KiB.')
                body = raw.decode('utf-8')
            except (OSError, UnicodeError):
                import_error(node, f'Module {name!r} could not be read as UTF-8 source.')
            total += len(raw)
            if total > MAX_MODULE_BYTES:
                import_error(node, 'Modules exceed the 256 KiB total limit.')
            found[name] = body
            active.append(name)
            visit(body, name, depth + 1)
            active.pop()
    visit(source, '<program>', 0)
    validate_modules(found)
    return found
