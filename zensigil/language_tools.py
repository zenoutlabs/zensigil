"""Editor queries over explicit source, without executing a ZenSigil program."""
from dataclasses import dataclass
import os
from pathlib import Path, PurePosixPath, PureWindowsPath
import re
from urllib.parse import unquote, urlsplit

from . import check
from .checker import BUILTINS
from .errors import SigilError
from .formatter import format_source
from .modules import (MAX_MODULES, MAX_MODULE_BYTES, MAX_MODULE_DEPTH,
                      compile_program, function_identity, module_name, module_scopes,
                      named_parse, validate_modules)
from .syntax import Node, Token, WORDS, lex

MAX_DOCUMENTS = 64
MAX_SOURCE_BYTES = 65536
SIGNATURE_ARGUMENTS = {
    "len": "value", "has": "record, key", "get": "record, key, fallback", "text": "value",
    "ceil": "number", "floor": "number", "abs": "number", "min": "left, right", "max": "left, right",
    "fraction": "number", "ceil_div": "numerator, denominator", "round": "number, places",
    "range": "start, stop, step", "enumerate": "items", "zip": "left, right", "sum": "numbers",
    "sorted": "items", "reverse": "value", "unique": "items", "contains": "container, value",
    "record_keys": "record", "record_values": "record", "record_entries": "record", "record_merge": "left, right",
    "map": "items, transform", "filter": "items, predicate", "fold": "items, initial, combine",
    "any": "items, predicate", "all": "items, predicate", "sort_by": "items, key",
    "group_by": "items, key", "count_by": "items, key", "partition": "items, predicate",
    "flat_map": "items, transform", "find": "items, predicate, fallback", "find_index": "items, predicate",
    "take": "items, count", "drop": "items, count", "chunk": "items, size",
    "record_pick": "record, keys", "record_omit": "record, keys", "clamp": "number, low, high",
    "type_of": "value", "lower": "text", "upper": "text", "trim": "text", "split": "text, separator",
    "join": "strings, separator", "replace": "text, old, new", "starts_with": "text, prefix", "ends_with": "text, suffix",
    "parse_number": "text", "parse_json": "text", "json_text": "value", "dec": "decimal_text",
    "dec_add": "left, right", "dec_sub": "left, right", "dec_mul": "left, right",
    "dec_div": "left, right, places", "dec_round": "decimal_text, places", "dec_compare": "left, right",
    "scan": "items, initial, combine", "min_by": "items, key", "max_by": "items, key",
    "sum_by": "items, transform", "unique_by": "items, key", "frequencies": "strings",
    "flatten": "lists", "record_from_entries": "entries",
}


def _file_uri_path(uri, windows):
    """Convert our local-only file URI subset without touching the filesystem.

    RFC 8089 drive URIs contain `/C:/`, while Windows paths need `C:/`.
    Keeping the conversion pure lets either path flavour be tested on any host.
    """
    if not isinstance(uri, str) or any(ord(char) < 32 or ord(char) == 127 for char in uri):
        return None
    try:
        parsed = urlsplit(uri)
        if parsed.scheme != 'file' or parsed.netloc.lower() not in ('', 'localhost') or parsed.query or parsed.fragment:
            return None
        # Do not let decoding change path segment boundaries or accept Windows
        # UNC/device paths through the empty-authority form of a file URI.
        if ('\\' in parsed.path or re.search(r'%(?:2f|5c)', parsed.path, re.I)
                or re.search(r'%(?![0-9a-fA-F]{2})', parsed.path)):
            return None
        decoded = unquote(parsed.path, errors='strict')
        if decoded.startswith('//') or any(ord(char) < 32 or ord(char) == 127 for char in decoded):
            return None
        if windows:
            if not re.match(r'^/[A-Za-z]:/', decoded) or ':' in decoded[3:]:
                return None
            path = PureWindowsPath(decoded[1:])
        else:
            path = PurePosixPath(decoded)
        return path if path.is_absolute() else None
    except (ValueError, UnicodeError):
        return None


def file_path(uri):
    """Only native, absolute local file URIs can cause a filesystem read."""
    path = _file_uri_path(uri, windows=os.name == 'nt')
    if path is None:
        return None
    try:
        resolved = Path(path).resolve()
        # A Windows junction/symlink can resolve a local drive path to UNC.
        if os.name == 'nt' and not re.fullmatch(r'[A-Za-z]:', resolved.drive):
            return None
        return resolved
    except (ValueError, OSError, UnicodeError, RuntimeError):
        return None


def utf16(text):
    return len(text.encode('utf-16-le', errors='replace')) // 2


def position(source, line=1, column=1):
    lines = source.split('\n')
    row = max(0, min(len(lines) - 1, line - 1))
    prefix = lines[row][:max(0, column - 1)]
    return {'line': row, 'character': utf16(prefix)}


def token_range(source, token):
    start = position(source, token.line, token.column)
    width = len(str(token.value)) if isinstance(token.value, str) else 1
    end = position(source, token.line, token.column + max(1, width))
    return {'start': start, 'end': end}


def end_position(source):
    lines = source.split('\n')
    return {'line': len(lines) - 1, 'character': utf16(lines[-1])}


def at_position(source, where):
    if not isinstance(where, dict) or type(where.get('line')) is not int or type(where.get('character')) is not int:
        return None
    lines = source.split('\n')
    row, units = where['line'], where['character']
    if row < 0 or row >= len(lines) or units < 0:
        return None
    used = 0
    for col, char in enumerate(lines[row]):
        if used >= units:
            return row + 1, col + 1
        used += utf16(char)
    return row + 1, len(lines[row]) + 1


def annotation_text(value):
    if value is None:
        return ''
    if isinstance(value, str):
        return value
    if value[0] == 'union':
        return ' | '.join(annotation_text(item) for item in value[1])
    return value[0] + '<' + annotation_text(value[1]) + '>'


def function_signature(node):
    name, params = node.parts[:2]
    annotations = node.parts[3] if len(node.parts) > 3 else (None,) * len(params)
    result = node.parts[4] if len(node.parts) > 4 else None
    arguments = [p.value + (': ' + annotation_text(a) if a else '') for p, a in zip(params, annotations)]
    return 'fn ' + name.value + '(' + ', '.join(arguments) + ')' + (' -> ' + annotation_text(result) if result else '')


def builtin_signature(name):
    arity = BUILTINS[name]
    counts = (arity,) if type(arity) is int else arity
    arguments = SIGNATURE_ARGUMENTS.get(name, ', '.join('arg' + str(i + 1) for i in range(max(counts))))
    return name + '(' + arguments + ')' + (' — accepts ' + '/'.join(map(str, counts)) + ' arguments' if len(counts) > 1 else '')


def member_context(source, coordinate):
    """Recognize a direct alias member at the cursor, excluding strings/comments.

    This small recovery rule never interprets imports. The recovered document
    still goes through the real parser and the bounded explicit import loader.
    """
    if coordinate is None:
        return None
    line, column = coordinate
    rows = source.split('\n')
    before = rows[line - 1][:column - 1]
    match = re.search(r'(?<![A-Za-z_0-9.])([A-Za-z_][A-Za-z_0-9]*)\s*\.\s*([A-Za-z_][A-Za-z_0-9]*)?$', before)
    if match is None:
        return None
    if before[:match.start()].rstrip().endswith('.'):
        return None
    quoted, escaped = False, False
    for char in before[:match.start()]:
        if escaped:
            escaped = False
        elif quoted and char == '\\':
            escaped = True
        elif char == '"':
            quoted = not quoted
        elif char == '#' and not quoted:
            return None
    if quoted:
        return None
    alias, prefix = match.group(1), match.group(2) or ''
    indent = len(rows[line - 1]) - len(rows[line - 1].lstrip(' '))
    # A bare `math.` line and `return math.` are both useful completion sites.
    # Replace only this unfinished line for a query; never change the buffer.
    rows[line - 1] = ' ' * indent + 'emit ' + alias
    return alias, prefix, '\n'.join(rows)


@dataclass
class Document:
    uri: str
    source: str
    version: int
    error: str = ''


class LanguageService:
    """A bounded collection of open buffers and workspace-scoped editor queries."""
    def __init__(self, roots=()):
        self.roots = tuple(sorted({p for uri in roots if (p := file_path(uri)) is not None and p.is_dir()}, key=lambda p: len(str(p)), reverse=True))
        self.documents = {}

    def open(self, uri, source, version):
        if not isinstance(uri, str) or len(uri) > 4096 or not isinstance(source, str) or type(version) is not int:
            return False
        prior = self.documents.get(uri)
        if prior is not None and version <= prior.version:
            return False
        if prior is None and len(self.documents) >= MAX_DOCUMENTS:
            return False
        try:
            too_large = len(source.encode('utf-8')) > MAX_SOURCE_BYTES
        except UnicodeError:
            too_large = True
        self.documents[uri] = Document(uri, '' if too_large else source, version,
                                       'Editor source must be valid UTF-8 and at most 64 KiB.' if too_large else '')
        return True

    def change(self, uri, source, version):
        return uri in self.documents and self.open(uri, source, version)

    def close(self, uri):
        return self.documents.pop(uri, None) is not None

    def root(self, uri):
        path = file_path(uri)
        return next((root for root in self.roots if path is not None and path.is_relative_to(root)), None)

    def bundle(self, uri, source=None):
        document = self.documents[uri]
        if document.error:
            raise SigilError('E_LIMIT', document.error)
        root = self.root(uri)
        modules, uris = {}, {'<program>': uri}
        overlay = {file_path(d.uri): d for d in self.documents.values() if file_path(d.uri) is not None}
        total = 0

        def visit(source, label, depth):
            nonlocal total
            if depth > MAX_MODULE_DEPTH:
                error = SigilError('E_IMPORT', 'Module imports exceed eight levels of nesting.')
                error.source_name = label
                raise error
            for node in named_parse(source, label):
                if node.kind != 'use':
                    continue
                try:
                    name = module_name(node.parts[0])
                    if name in modules:
                        continue
                    if root is None:
                        raise SigilError('E_IMPORT', 'Open this program inside a declared workspace to resolve its explicit imports.')
                    path = (root / name).resolve()
                    if not path.is_relative_to(root):
                        raise SigilError('E_IMPORT', 'Imported source must stay inside the declared workspace root.')
                    if len(modules) >= MAX_MODULES:
                        raise SigilError('E_IMPORT', 'A project may load at most 32 modules.')
                    if path in overlay:
                        other = overlay[path]
                        if other.error:
                            raise SigilError('E_LIMIT', other.error)
                        body = other.source
                        target_uri = other.uri
                    else:
                        if not path.is_file():
                            raise SigilError('E_IMPORT', 'Explicit module must be a regular source file inside the workspace.')
                        # No scans: only a path named by a parsed top-level use is read.
                        with path.open('rb') as stream:
                            raw = stream.read(MAX_SOURCE_BYTES + 1)
                        if len(raw) > MAX_SOURCE_BYTES:
                            raise SigilError('E_IMPORT', 'Imported source exceeds 64 KiB.')
                        body = raw.decode('utf-8')
                        target_uri = path.as_uri()
                    total += len(body.encode('utf-8'))
                    if total > MAX_MODULE_BYTES:
                        raise SigilError('E_IMPORT', 'Modules exceed the 256 KiB total limit.')
                    modules[name], uris[name] = body, target_uri
                    visit(body, name, depth + 1)
                except (OSError, UnicodeError, RuntimeError):
                    error = SigilError('E_IMPORT', 'Explicit module could not be read as UTF-8 source.', node.token.line, node.token.column)
                    error.source_name = label
                    raise error
                except SigilError as error:
                    if not error.source_name:
                        error.source_name = label
                        error.line, error.column = node.token.line, node.token.column
                    # Keep maps so diagnostics can point at an imported open buffer.
                    error.editor_sources, error.editor_uris = modules, uris
                    raise
        visit(document.source if source is None else source, '<program>', 0)
        validate_modules(modules)
        return modules, uris

    def diagnostics(self, uri):
        document = self.documents[uri]
        modules, uris = {}, {'<program>': uri}
        try:
            modules, uris = self.bundle(uri)
            result = check(document.source, modules=modules)
            items = result['diagnostics']
        except (SigilError, RecursionError) as error:
            if isinstance(error, RecursionError):
                error = SigilError('E_LIMIT', 'Source nesting exceeds editor limits.')
            modules.update(getattr(error, 'editor_sources', {}))
            uris.update(getattr(error, 'editor_uris', {}))
            items = [error.as_dict(document.source)]
        result = {uri: []}
        for item in items:
            name = item.get('source_name') or item.get('source_file') or '<program>'
            target = uris.get(name, uri)
            source = document.source if name == '<program>' else modules.get(name, '')
            start = position(source, item.get('line', 1), item.get('column', 1))
            end = position(source, item.get('line', 1), item.get('column', 1) + 1)
            result.setdefault(target, []).append({'range': {'start': start, 'end': end}, 'severity': 1,
                                                  'source': 'ZenSigil', 'code': item['code'], 'message': item['message']})
        return result

    def index(self, uri, source=None):
        document = self.documents[uri]
        source = document.source if source is None else source
        modules, uris = self.bundle(uri, source)
        nodes, sources = compile_program(source, modules)
        return Index(nodes, sources, uris)

    def completion(self, uri, where):
        if uri not in self.documents:
            return []
        coordinate = at_position(self.documents[uri].source, where)
        member = member_context(self.documents[uri].source, coordinate)
        if member is not None:
            alias, prefix, recovered = member
            try:
                try:
                    index = self.index(uri)
                except SigilError:
                    index = self.index(uri, recovered)
                return [{'label': entry['name'], 'kind': 3, 'detail': entry['detail']}
                        for entry in index.members(uri, alias) if entry['name'].startswith(prefix)]
            except (SigilError, RecursionError):
                return []
        items = {word: {'label': word, 'kind': 14, 'detail': 'ZenSigil keyword'} for word in WORDS}
        items.update({name: {'label': name, 'kind': 3, 'detail': builtin_signature(name)} for name in BUILTINS})
        try:
            index = self.index(uri)
            for entry in index.visible(uri, coordinate):
                items[entry['name']] = {'label': entry['name'], 'kind': {12: 3, 3: 9}.get(entry['kind'], 6), 'detail': entry['detail']}
        except (SigilError, RecursionError):
            # Keywords and built-ins remain available while an expression is incomplete.
            pass
        return [items[name] for name in sorted(items)]

    def hover(self, uri, where):
        found = self.reference(uri, where)
        if found is None:
            return None
        token, entry, source = found
        detail = entry['detail'] if entry else builtin_signature(token.value) if token.kind == 'NAME' and token.value in BUILTINS else None
        return {'contents': {'kind': 'plaintext', 'value': detail}, 'range': token_range(source, token)} if detail else None

    def definition(self, uri, where):
        found = self.reference(uri, where)
        if found is None or found[1] is None:
            return None
        entry = found[1]
        return {'uri': entry['uri'], 'range': entry['range']}

    def reference(self, uri, where):
        if uri not in self.documents:
            return None
        try:
            index = self.index(uri)
            return index.reference(uri, at_position(self.documents[uri].source, where))
        except (SigilError, RecursionError):
            return None

    def symbols(self, uri):
        if uri not in self.documents:
            return []
        try:
            index = self.index(uri)
            return [{'name': e['name'], 'kind': e['kind'], 'location': {'uri': e['uri'], 'range': e['range']},
                     'containerName': e['container']} for e in index.declarations if e['uri'] == uri]
        except (SigilError, RecursionError):
            return []

    def formatting(self, uri):
        if uri not in self.documents or self.documents[uri].error:
            return []
        source = self.documents[uri].source
        formatted = format_source(source)
        return [] if formatted == source else [{'range': {'start': {'line': 0, 'character': 0}, 'end': end_position(source)}, 'newText': formatted}]


class Index:
    """Resolve name tokens with the language's lexical scopes, including lambdas."""
    def __init__(self, nodes, sources, uris):
        self.sources, self.uris = sources, uris
        self.declarations, self.references, self.contexts = [], [], []
        self.functions, self.globals, self.member_tokens = {}, {}, {}
        for node in nodes:
            if node.kind == 'fn':
                entry = self.declare(node.parts[0], 12, function_signature(node), '')
                self.functions[function_identity(node)] = entry
        for label, scope in module_scopes(nodes).items():
            self.globals[label] = {name: self.functions[identity] for name, identity in scope['functions'].items()}
            for node in named_parse(sources[label], label):
                if node.kind == 'use' and len(node.parts) > 1:
                    token = node.parts[1]
                    namespace = scope['namespaces'][token.value]
                    entry = self.declare(token, 3, 'namespace ' + token.value + ' from "' + namespace.path + '"')
                    entry['namespace'] = namespace
                    self.globals[label][token.value] = entry
            tokens = lex(sources[label])
            for before, after in zip(tokens, tokens[1:]):
                if before.kind == '.' and after.kind == 'NAME':
                    self.member_tokens[label, before.line, before.column] = Token('MEMBER', after.value, after.line, after.column, label)
            self.block([node for node in nodes if node.kind != 'module_scope' and
                        (node.token.source_name or '<program>') == label], [{}])

    def source(self, token):
        return self.sources.get(token.source_name or '<program>', '')

    def uri(self, token):
        return self.uris.get(token.source_name or '<program>')

    def declare(self, token, kind=13, detail='', container=''):
        entry = {'name': token.value, 'kind': kind, 'uri': self.uri(token), 'range': token_range(self.source(token), token),
                 'detail': detail or str(token.value), 'container': container}
        self.declarations.append(entry)
        self.references.append((token, entry))
        return entry

    def find(self, name, scopes, token):
        return next((scope[name] for scope in reversed(scopes) if name in scope),
                    self.globals.get(token.source_name or '<program>', {}).get(name))

    def remember(self, token, scopes, indent=None):
        visible = dict(self.globals.get(token.source_name or '<program>', {}))
        for scope in scopes:
            visible.update(scope)
        lines = self.source(token).split('\n')
        raw = lines[token.line - 1] if 0 < token.line <= len(lines) else ''
        if indent is None:
            indent = len(raw) - len(raw.lstrip(' '))
        self.contexts.append((token, list(visible.values()), indent))

    def after(self, node, scopes):
        tokens = []
        def collect(value):
            if isinstance(value, Token):
                tokens.append(value)
            elif isinstance(value, Node):
                collect(value.token)
                collect(value.parts)
            elif isinstance(value, tuple):
                for part in value:
                    collect(part)
        collect(node)
        final = max(tokens, key=lambda token: (token.line, token.column))
        compound = node.kind in {'fn', 'when', 'for', 'while', 'rule', 'test'}
        line = final.line + (1 if compound else 0)
        column = 1 if compound else final.column + max(1, len(str(final.value)))
        raw = self.source(node.token).split('\n')[node.token.line - 1]
        indent = len(raw) - len(raw.lstrip(' '))
        self.remember(Token('scope', '', line, column, node.token.source_name), scopes, indent)

    def expr(self, node, scopes, container=''):
        if not isinstance(node, Node):
            return
        self.remember(node.token, scopes)
        if node.kind == 'name':
            self.references.append((node.token, self.find(node.parts[0], scopes, node.token)))
        elif node.kind == 'field':
            base, name = node.parts
            self.expr(base, scopes, container)
            entry = self.find(base.parts[0], scopes, base.token) if base.kind == 'name' else None
            namespace = entry.get('namespace') if entry else None
            target = self.functions.get(namespace.member(name)) if namespace else None
            token = self.member_tokens.get((node.token.source_name or '<program>', node.token.line, node.token.column))
            if token is not None:
                self.references.append((token, target))
        elif node.kind == 'lambda':
            inner = scopes + [{}]
            for parameter in node.parts[0]:
                inner[-1][parameter.value] = self.declare(parameter, 13, 'parameter ' + parameter.value, container)
            self.expr(node.parts[1], inner, container)
        else:
            def descend(value):
                if isinstance(value, Node):
                    self.expr(value, scopes, container)
                elif isinstance(value, tuple):
                    for child in value:
                        descend(child)
            for part in node.parts:
                descend(part)

    def block(self, nodes, scopes, container=''):
        for node in nodes:
            kind, p = node.kind, node.parts
            self.remember(node.token, scopes)
            if kind in ('let', 'var'):
                self.expr(p[1], scopes, container)
                detail = kind + ' ' + p[0].value + (': ' + annotation_text(p[2]) if len(p) > 2 and p[2] else '')
                scopes[-1][p[0].value] = self.declare(p[0], 13, detail, container)
            elif kind == 'set':
                self.references.append((p[0], self.find(p[0].value, scopes, p[0])))
                self.expr(p[1], scopes, container)
            elif kind == 'fn':
                inner = [{}]
                annotations = p[3] if len(p) > 3 else (None,) * len(p[1])
                for parameter, annotation in zip(p[1], annotations):
                    detail = 'parameter ' + parameter.value + (': ' + annotation_text(annotation) if annotation else '')
                    inner[-1][parameter.value] = self.declare(parameter, 13, detail, p[0].value)
                self.block(p[2], inner, p[0].value)
            elif kind in ('rule', 'test'):
                token = Token('STRING', p[0], node.token.line, node.token.column, node.token.source_name)
                self.declare(token, 12, kind + ' ' + str(p[0]), '')
                self.block(p[1], [{}] if kind == 'test' else scopes + [{}], str(p[0]))
            elif kind == 'when':
                self.expr(p[0], scopes, container)
                for branch in p[1:]:
                    self.block(branch, scopes + [{}], container)
            elif kind == 'while':
                self.expr(p[0], scopes, container)
                self.block(p[1], scopes + [{}], container)
            elif kind == 'for':
                self.expr(p[1], scopes, container)
                inner = scopes + [{}]
                inner[-1][p[0].value] = self.declare(p[0], 13, 'loop binding ' + p[0].value, container)
                self.block(p[2], inner, container)
            else:
                # Includes proposal field expressions; field names are not references.
                for part in p:
                    if isinstance(part, Node):
                        self.expr(part, scopes, container)
                    elif isinstance(part, tuple):
                        for child in part:
                            if isinstance(child, tuple) and len(child) == 2 and isinstance(child[1], Node):
                                self.expr(child[1], scopes, container)
            self.after(node, scopes)

    def reference(self, uri, coordinate):
        if coordinate is None:
            return None
        line, column = coordinate
        for token, entry in self.references:
            if self.uri(token) == uri and token.line == line and token.column <= column < token.column + len(str(token.value)):
                return token, entry, self.source(token)
        return None

    def visible(self, uri, coordinate):
        label = next((name for name, target in self.uris.items() if target == uri), '<program>')
        fallback = list(self.globals.get(label, {}).values())
        if coordinate is None:
            return fallback
        source = next((self.sources[name] for name, target in self.uris.items() if target == uri), '')
        lines = source.split('\n')
        raw = lines[coordinate[0] - 1] if 0 < coordinate[0] <= len(lines) else ''
        indent = len(raw) - len(raw.lstrip(' '))
        candidates = [(t, entries) for t, entries, level in self.contexts
                      if self.uri(t) == uri and (t.line, t.column) <= coordinate and level <= indent]
        return max(candidates, key=lambda pair: (pair[0].line, pair[0].column))[1] if candidates else fallback

    def members(self, uri, alias):
        label = next((name for name, target in self.uris.items() if target == uri), '<program>')
        entry = self.globals.get(label, {}).get(alias)
        namespace = entry.get('namespace') if entry else None
        return sorted((self.functions[identity] for _, identity in namespace.members), key=lambda item: item['name']) if namespace else []
