"""Conservative source formatting, verified against the parser's syntax tree."""
import os
from pathlib import Path
import stat
import tempfile
from .astio import semantic_tree
from .errors import SigilError
from .syntax import IDENT, NUMBER, STRING, Parser, parse

_LAYOUT = {"INDENT", "DEDENT", "NEWLINE", "EOF"}
_OPERATORS = {"=", "+", "-", "*", "/", "%", "==", "!=", "<", ">", "<=", ">=", "??", "->", "=>", "|"}
_UNARY_CONTEXT = _OPERATORS | {"(", "[", "{", ",", ":", "return", "say", "emit", "then", "choose", "otherwise", "and", "or", "not", "require"}


def _spelling(token, raw):
    start = token.column - 1
    pattern = STRING if token.kind == "STRING" else NUMBER if token.kind == "NUMBER" else IDENT
    match = pattern.match(raw, start) if token.kind in {"STRING", "NUMBER", "NAME"} or raw[start:start + 1].isalpha() or raw[start:start + 1] == "_" else None
    return match.group() if match else raw[start:start + len(token.kind)]


def _line(tokens, raw):
    pieces = []
    previous = None
    unary_previous = False
    for index, token in enumerate(tokens):
        kind = token.kind
        spelling = _spelling(token, raw)
        unary = kind in {"+", "-"} and (previous is None or previous in _UNARY_CONTEXT)
        if previous is None:
            space = False
        elif kind in {",", ":", ")", "]", "}", "."} or previous in {"(", "[", "{", "."}:
            space = False
        elif unary_previous:
            space = False
        elif kind == "(" and previous in {"NAME", ")", "]"}:
            space = False
        elif kind == "[" and previous in {"NAME", "STRING", "NUMBER", ")", "]", "}"}:
            space = False
        else:
            space = True
        pieces.append((" " if space else "") + spelling)
        previous, unary_previous = kind, unary
    last = tokens[-1]
    end = last.column - 1 + len(_spelling(last, raw))
    comment = raw[end:].lstrip(" \t")
    if comment:
        pieces.append("  " + comment.rstrip())
    return "".join(pieces)


def _format_source(source):
    """Preserve tokens, string spellings, comments and blank lines; reject invalid syntax."""
    parser = Parser(source)
    before = semantic_tree(parser.program())
    by_line = {}
    for token in parser.tokens:
        if token.kind not in _LAYOUT:
            by_line.setdefault(token.line, []).append(token)
    result = []
    stack = []
    block_indent = 0
    for number, raw in enumerate(source.split("\n"), 1):
        raw = raw.rstrip("\r")
        tokens = by_line.get(number, [])
        if not tokens:
            # Comments have no syntactic effect. Keep their existing indentation.
            result.append(raw.rstrip())
            continue
        if not stack:
            block_indent = len(raw) - len(raw.lstrip(" "))
            indent = block_indent
        else:
            closing = tokens[0].kind in {")", "]", "}"}
            indent = block_indent + max(0, len(stack) - (1 if closing else 0)) * 4
        result.append(" " * indent + _line(tokens, raw))
        for token in tokens:
            if token.kind in {"(", "[", "{"}:
                stack.append(token.kind)
            elif token.kind in {")", "]", "}"}:
                stack.pop()
    while result and result[-1] == "":
        result.pop()
    formatted = "\n".join(result) + ("\n" if result else "")
    if semantic_tree(parse(formatted)) != before:
        raise SigilError("E_FORMAT", "Formatting changed the syntax tree; the original source was preserved.")
    return formatted


def format_source(source):
    """Return verified formatting or a structured diagnostic for invalid input."""
    try:
        return _format_source(source)
    except (RecursionError, UnicodeError):
        raise SigilError("E_LIMIT", "Source nesting or text encoding exceeds formatter limits.")


def write_formatted(path, text):
    """Atomically replace one explicit regular source file, retaining its permissions."""
    destination = Path(path)
    if destination.is_symlink() or not destination.is_file():
        raise ValueError("Formatting in place requires a regular .zs file, not a symbolic link.")
    descriptor, temporary = tempfile.mkstemp(prefix=".zensigil-format-", dir=str(destination.parent))
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary, stat.S_IMODE(destination.stat().st_mode))
        os.replace(temporary, destination)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
