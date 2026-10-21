"""A versioned, JSON-compatible view of the parsed syntax tree."""
from .syntax import Node, Token, parse
from .errors import SigilError


def _public(value):
    if isinstance(value, Node):
        return {"kind": value.kind, "line": value.token.line,
                "column": value.token.column, "parts": [_public(item) for item in value.parts]}
    if isinstance(value, Token):
        return {"kind": value.kind, "value": value.value, "line": value.line, "column": value.column}
    if isinstance(value, (tuple, list)):
        return [_public(item) for item in value]
    if value is None or type(value) in (str, int, float, bool):
        return value
    raise TypeError("Unsupported syntax tree value.")


def ast_document(source):
    """Parse without executing, resolving imports, or consulting host files."""
    try:
        return {"format": "zensigil-ast", "format_version": 1, "body": _public(parse(source))}
    except (RecursionError, UnicodeError):
        raise SigilError("E_LIMIT", "Source nesting or text encoding exceeds syntax tree limits.")


def semantic_tree(value):
    """Position-free tree used to verify formatting, including identifier tokens."""
    if isinstance(value, Node):
        return (value.kind, tuple(semantic_tree(item) for item in value.parts))
    if isinstance(value, Token):
        return (value.kind, value.value)
    if isinstance(value, (tuple, list)):
        return tuple(semantic_tree(item) for item in value)
    return value
