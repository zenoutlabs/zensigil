"""A standalone lexer and recursive-descent/Pratt parser. No eval or Python AST."""
import json
import math
import re
from dataclasses import dataclass
from .errors import SigilError, fail

WORDS = {"let", "say", "when", "otherwise", "for", "in", "fn", "return",
         "rule", "propose", "require", "var", "set", "while", "break", "continue",
         "choose", "then", "emit", "test", "use", "as", "export", "true", "false", "null", "and", "or", "not"}
IDENT = re.compile(r"[A-Za-z_][A-Za-z_0-9]*")
NUMBER = re.compile(r"[0-9]+(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?")
STRING = re.compile(r'"(?:[^"\\\n]|\\.)*"')
PRECEDENCE = {"??": 5, "or": 10, "and": 20, "==": 30, "!=": 30, "<": 30,
              "in": 30, "not in": 30, "<=": 30, ">": 30, ">=": 30, "+": 40, "-": 40,
              "*": 50, "/": 50, "%": 50}


@dataclass(frozen=True)
class Token:
    kind: str
    value: object
    line: int
    column: int
    source_name: str = ""


@dataclass(frozen=True)
class Node:
    kind: str
    token: Token
    parts: tuple


def lex(source):
    if not isinstance(source, str):
        raise SigilError("E_INPUT", "Source must be text.")
    if len(source.encode("utf-8")) > 65536:
        raise SigilError("E_LIMIT", "Source exceeds the 64 KiB limit.")
    tokens, levels, brackets = [], [0], []
    lines = source.split("\n")
    for line_no, raw in enumerate(lines, 1):
        raw = raw.rstrip("\r")
        prefix = raw[:len(raw) - len(raw.lstrip(" \t"))]
        if "\t" in prefix:
            raise SigilError("E_INDENT", "Use four spaces for indentation, not tabs.", line_no, 1)
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        if not brackets:
            indent = len(prefix)
            if indent % 4:
                raise SigilError("E_INDENT", "Indentation must be a multiple of four spaces.", line_no, 1)
            if indent > levels[-1]:
                if indent != levels[-1] + 4:
                    raise SigilError("E_INDENT", "Indent each block by exactly four more spaces.", line_no, 1)
                levels.append(indent)
                tokens.append(Token("INDENT", None, line_no, 1))
            while indent < levels[-1]:
                levels.pop()
                tokens.append(Token("DEDENT", None, line_no, 1))
        pos = len(prefix)
        while pos < len(raw):
            ch = raw[pos]
            if ch in " \t":
                pos += 1
                continue
            if ch == "#":
                break
            start = pos
            if ch == '"':
                match = STRING.match(raw, pos)
                if not match:
                    raise SigilError("E_STRING", "Unclosed string; use double quotes and escape newlines.", line_no, pos + 1)
                try:
                    value = json.loads(match.group())
                    value.encode("utf-8")
                except (ValueError, UnicodeError):
                    raise SigilError("E_STRING", "Invalid JSON string escape or Unicode character.", line_no, pos + 1)
                kind, pos = "STRING", match.end()
            elif ch.isascii() and ch.isdigit():
                match = NUMBER.match(raw, pos)
                value = match.group()
                if len(value) > 100:
                    raise SigilError("E_LIMIT", "Numeric literal is too large.", line_no, pos + 1)
                value = float(value) if any(c in value for c in ".eE") else int(value)
                if not math.isfinite(value):
                    raise SigilError("E_NUMBER", "Numbers must be finite.", line_no, pos + 1)
                kind, pos = "NUMBER", match.end()
            elif IDENT.match(raw, pos):
                match = IDENT.match(raw, pos)
                value, pos = match.group(), match.end()
                kind = value if value in WORDS else "NAME"
            else:
                pair = raw[pos:pos + 2]
                if pair in {"==", "!=", "<=", ">=", "??", "->", "=>"}:
                    kind, value, pos = pair, pair, pos + 2
                elif ch in "()[]{}:,.=+-*/%<>|":
                    kind, value, pos = ch, ch, pos + 1
                else:
                    raise SigilError("E_TOKEN", f"Unexpected character {ch!r}.", line_no, pos + 1)
                if kind in {"(", "[", "{"}:
                    brackets.append(kind)
                    if len(brackets) > 48:
                        raise SigilError("E_LIMIT", "Expression nesting exceeds 48 levels.", line_no, pos)
                elif kind in {")", "]", "}"}:
                    if not brackets or brackets.pop() != {")": "(", "]": "[", "}": "{"}[kind]:
                        raise SigilError("E_SYNTAX", f"Unmatched {kind!r}.", line_no, pos)
            tokens.append(Token(kind, value, line_no, start + 1))
            if len(tokens) > 20000:
                raise SigilError("E_LIMIT", "Program exceeds the token limit.", line_no, start + 1)
        if not brackets:
            tokens.append(Token("NEWLINE", None, line_no, len(raw) + 1))
    if brackets:
        raise SigilError("E_SYNTAX", "Unclosed bracket or parenthesis.", len(lines), 1)
    tokens.extend(Token("DEDENT", None, len(lines), 1) for _ in levels[1:])
    tokens.append(Token("EOF", None, len(lines), 1))
    return tokens


class Parser:
    def __init__(self, source):
        self.tokens = lex(source)
        self.index = 0

    @property
    def current(self):
        return self.tokens[self.index]

    def take(self):
        token = self.current
        self.index += 1
        return token

    def accept(self, kind):
        return self.take() if self.current.kind == kind else None

    def need(self, kind):
        if self.current.kind != kind:
            actual = self.current.value or self.current.kind.lower()
            fail(self.current, "E_SYNTAX", f"Expected {kind!r}, found {actual!r}.")
        return self.take()

    def program(self):
        result = []
        while self.current.kind != "EOF":
            result.append(self.statement())
        return tuple(result)

    def suite(self):
        self.need(":")
        self.need("NEWLINE")
        self.need("INDENT")
        body = []
        while self.current.kind not in {"DEDENT", "EOF"}:
            body.append(self.statement())
        self.need("DEDENT")
        if not body:
            fail(self.current, "E_SYNTAX", "A block needs at least one statement.")
        return tuple(body)

    def statement(self):
        token = self.take()
        kind = token.kind
        exported = kind == "export"
        if exported:
            if self.current.kind != "fn":
                fail(token, "E_IMPORT", "Only a named function can be exported: export fn name(...):")
            self.take()
            kind = "fn"
        if kind in {"let", "var", "set"}:
            name = self.need("NAME")
            annotation = self.annotation() if kind != "set" else None
            self.need("=")
            parts = (name, self.expression(), annotation)
        elif kind in {"say", "return", "emit"}:
            parts = (self.expression(),)
        elif kind in {"break", "continue"}:
            parts = ()
        elif kind == "use":
            parts = (self.need("STRING").value,)
            if self.accept("as"):
                parts += (self.need("NAME"),)
        elif kind == "while":
            condition = self.expression()
            return Node(kind, token, (condition, self.suite()))
        elif kind == "require":
            condition = self.expression()
            self.need(",")
            parts = (condition, self.expression())
        elif kind == "propose":
            name = self.need("NAME")
            self.need("(")
            fields = self.fields(")")
            if not fields:
                fail(token, "E_SYNTAX", "A proposal needs at least one named field.")
            parts = (name.value, fields)
        elif kind == "when":
            condition = self.expression()
            yes = self.suite()
            no = self.suite() if self.accept("otherwise") else ()
            return Node(kind, token, (condition, yes, no))
        elif kind == "for":
            name = self.need("NAME")
            self.need("in")
            iterable = self.expression()
            return Node(kind, token, (name, iterable, self.suite()))
        elif kind in {"rule", "test"}:
            name = self.need("STRING")
            return Node(kind, token, (name.value, self.suite()))
        elif kind == "fn":
            name = self.need("NAME")
            parameters, annotations, return_type = self.parameters()
            parts = (name, parameters, self.suite(), annotations, return_type)
            return Node(kind, token, parts + ((True,) if exported else ()))
        else:
            fail(token, "E_SYNTAX", "Expected let, say, when, for, fn, return, rule, require, or propose.")
        self.need("NEWLINE")
        return Node(kind, token, parts)

    def parameters(self):
        self.need("(")
        parameters, annotations = [], []
        if self.current.kind != ")":
            while True:
                parameters.append(self.need("NAME"))
                annotations.append(self.annotation())
                if not self.accept(",") or self.current.kind == ")":
                    break
        self.need(")")
        return_type = self.need_type() if self.accept("->") else None
        return tuple(parameters), tuple(annotations), return_type

    def need_type(self):
        self.type_nodes = 0
        return self.type_union(0)

    def type_union(self, depth):
        if depth > 16:
            fail(self.current, "E_LIMIT", "Type annotations may nest at most 16 levels.")
        alternatives = [self.type_atom(depth)]
        while self.accept("|"):
            if len(alternatives) >= 8:
                fail(self.current, "E_LIMIT", "A union may contain at most eight alternatives.")
            alternatives.append(self.type_atom(depth))
        return alternatives[0] if len(alternatives) == 1 else ("union", tuple(alternatives))

    def type_atom(self, depth):
        token = self.take()
        from .typesys import TYPE_NAMES
        self.type_nodes += 1
        if self.type_nodes > 64:
            fail(token, "E_LIMIT", "An annotation may contain at most 64 type names.")
        if token.kind not in {"NAME", "null"} or token.value not in TYPE_NAMES:
            fail(token, "E_TYPE", "Unknown annotation; use " + ", ".join(sorted(TYPE_NAMES)) + ".")
        if self.accept("<"):
            if token.value not in {"list", "record"}:
                fail(token, "E_TYPE", "Only list and record annotations accept an element type.")
            element = self.type_union(depth + 1)
            self.type_closer()
            return (token.value, element)
        return token.value

    def type_closer(self):
        # Inside an annotation, a closing > belongs to its generic type even
        # when immediately followed by = or =>. Elsewhere >= stays comparison.
        if self.current.kind == ">=":
            token = self.take()
            self.tokens[self.index - 1] = Token(">", ">", token.line, token.column, token.source_name)
            following = self.current
            if following.kind == ">" and following.line == token.line and following.column == token.column + 2:
                self.tokens[self.index] = Token("=>", "=>", token.line, token.column + 1, token.source_name)
            else:
                self.tokens.insert(self.index, Token("=", "=", token.line, token.column + 1, token.source_name))
        else:
            self.need(">")

    def annotation(self):
        return self.need_type() if self.accept(":") else None

    def fields(self, closer):
        fields, names = [], set()
        if self.current.kind != closer:
            while True:
                key = self.take()
                if key.kind not in {"NAME", "STRING"}:
                    fail(key, "E_SYNTAX", "Expected a field name or quoted key.")
                if key.value in names:
                    fail(key, "E_DUPLICATE", f"Field {key.value!r} is repeated.")
                names.add(key.value)
                self.need(":")
                fields.append((key.value, self.expression()))
                if not self.accept(",") or self.current.kind == closer:
                    break
        self.need(closer)
        return tuple(fields)

    def expression(self, minimum=0):
        token = self.take()
        kind = token.kind
        if kind in {"STRING", "NUMBER"}:
            left = Node("literal", token, (token.value,))
        elif kind in {"true", "false", "null"}:
            left = Node("literal", token, ({"true": True, "false": False, "null": None}[kind],))
        elif kind == "NAME":
            left = Node("name", token, (token.value,))
        elif kind in {"-", "+", "not"}:
            left = Node("unary", token, (kind, self.expression(25 if kind == "not" else 60)))
        elif kind == "fn":
            parameters, annotations, return_type = self.parameters()
            self.need("=>")
            left = Node("lambda", token, (parameters, self.expression(), annotations, return_type))
        elif kind == "choose":
            condition = self.expression()
            self.need("then")
            yes = self.expression()
            self.need("otherwise")
            left = Node("choose", token, (condition, yes, self.expression()))
        elif kind == "(":
            left = self.expression()
            self.need(")")
        elif kind == "[":
            items = []
            if self.current.kind != "]":
                while True:
                    items.append(self.expression())
                    if not self.accept(",") or self.current.kind == "]":
                        break
            self.need("]")
            left = Node("list", token, (tuple(items),))
        elif kind == "{":
            left = Node("record", token, (self.fields("}"),))
        else:
            fail(token, "E_SYNTAX", "Expected a value, variable, or expression.")
        comparison = False
        while True:
            kind = self.current.kind
            if kind == "not" and self.tokens[self.index + 1].kind == "in":
                kind = "not in"
            if kind == ".":
                dot = self.take()
                field = self.need("NAME")
                left = Node("field", dot, (left, field.value))
            elif kind == "[":
                bracket = self.take()
                start = None if self.current.kind == ":" else self.expression()
                if self.accept(":"):
                    stop = None if self.current.kind == "]" else self.expression()
                    self.need("]")
                    left = Node("slice", bracket, (left, start, stop))
                else:
                    self.need("]")
                    left = Node("index", bracket, (left, start))
            elif kind == "(":
                call = self.take()
                args = []
                if self.current.kind != ")":
                    while True:
                        args.append(self.expression())
                        if not self.accept(",") or self.current.kind == ")":
                            break
                self.need(")")
                left = Node("call", left.token, (left, tuple(args)))
            elif kind in PRECEDENCE and PRECEDENCE[kind] >= minimum:
                op = self.take()
                if kind == "not in":
                    self.need("in")
                if PRECEDENCE[kind] == 30:
                    if comparison:
                        fail(op, "E_SYNTAX", "Use 'and' between comparisons, such as 1 < x and x < 10.")
                    comparison = True
                right = self.expression(PRECEDENCE[kind] + 1)
                left = Node("binary", op, (kind, left, right))
            else:
                return left


def parse(source):
    try:
        return Parser(source).program()
    except RecursionError:
        raise SigilError("E_LIMIT", "Program nesting is too deep; simplify the expression or blocks.")
