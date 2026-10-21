"""Bounded tree-walking interpreter with transactional preview results."""
import hashlib
import json
import math
from fractions import Fraction
from .checker import BUILTINS
from .errors import SigilError, fail
from .typesys import Closure, FunctionRef, NamespaceRef, enforce
from .modules import function_identity, module_scopes

MAX_JSON_BYTES = 1_048_576


def is_number(value):
    return type(value) in (int, float)


def validate_value(value, token=None):
    """Walk before serialization so deeply shared values cannot expand unchecked."""
    stack, count, characters = [(value, 0)], 0, 0
    while stack:
        item, depth = stack.pop()
        count += 1
        message = None
        if count > 20000 or depth > 32:
            message = "Value exceeds the 20,000-node or 32-level nesting limit."
        elif item is None or type(item) is bool:
            pass
        elif is_number(item):
            if abs(item) > 1e100 or not math.isfinite(item):
                message = "Numbers must be finite and have magnitude at most 1e100."
        elif type(item) is str:
            try:
                characters += len(item.encode("utf-8"))
            except UnicodeError:
                message = "Strings must contain valid Unicode characters."
            if len(item) > 65536 or characters > MAX_JSON_BYTES:
                message = "Text exceeds the value size limit."
        elif type(item) is list:
            if len(item) > 10000:
                message = "Lists may contain at most 10,000 items."
            else:
                stack.extend((child, depth + 1) for child in item)
        elif type(item) is dict:
            if len(item) > 10000 or any(type(key) is not str for key in item):
                message = "Records need string keys and at most 10,000 fields."
            else:
                stack.extend((child, depth + 1) for pair in item.items() for child in pair)
        else:
            message = "Only JSON values are supported."
        if message:
            if token:
                fail(token, "E_VALUE", message)
            raise SigilError("E_INPUT", message)


def compact(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)


class Returned(Exception):
    def __init__(self, value):
        self.value = value


class LoopSignal(Exception):
    def __init__(self, kind):
        self.kind = kind


class Runtime:
    def __init__(self, program, data, max_steps=100000):
        self.functions = {function_identity(node): node for node in program if node.kind == "fn"}
        self.module_scopes = module_scopes(program)
        self.program, self.data = program, data
        self.max_steps, self.steps, self.depth = max_steps, 0, 0
        self.proposals, self.notes, self.seen = [], [], set()
        self.values = []
        self.mutable, self.annotations = {}, {}
        self.duplicates, self.output_bytes = 0, 0
        self.lambda_names = {}
        self.capture_nodes, self.capture_bytes = 0, 0

    def environment(self, token):
        return self.module_scopes.get(token.source_name or '<program>', {'functions': {}, 'namespaces': {}})

    @staticmethod
    def is_callable(value):
        return type(value) is FunctionRef

    def validate_callable(self, value, arity, token):
        if not self.is_callable(value):
            fail(token, "E_TYPE", "Expected a function reference.")
        expected = self.callable_arity(value)
        accepted = (expected,) if type(expected) is int else expected
        if arity not in accepted:
            fail(token, "E_ARITY", f"Callback {value.name} must accept {arity} argument(s); it accepts {expected}.")
        return value

    def callable_arity(self, value):
        if value.closure is not None:
            return len(value.closure.node.parts[0])
        return BUILTINS[value.name] if value.name in BUILTINS else len(self.functions[value.name].parts[1])

    def annotated(self, value, annotation, token, label):
        return enforce(value, annotation, token, label, tick=lambda: self.tick(token))

    def free_names(self, node):
        key = id(node)
        if key in self.lambda_names:
            return self.lambda_names[key]
        names = {}
        pending = [(node.parts[1], frozenset(param.value for param in node.parts[0]))]
        while pending:
            expression, bound = pending.pop()
            self.tick(expression.token)
            kind, parts = expression.kind, expression.parts
            if kind == "name":
                name = parts[0]
                environment = self.environment(expression.token)
                if name not in bound and name not in BUILTINS and name not in environment['functions'] and name not in environment['namespaces']:
                    names.setdefault(name, expression.token)
            elif kind == "lambda":
                pending.append((parts[1], bound | {param.value for param in parts[0]}))
            elif kind == "call":
                pending.extend((child, bound) for child in (parts[0],) + parts[1])
            elif kind == "list":
                pending.extend((child, bound) for child in parts[0])
            elif kind == "record":
                pending.extend((child, bound) for _, child in parts[0])
            elif kind == "unary":
                pending.append((parts[1], bound))
            elif kind == "field":
                pending.append((parts[0], bound))
            elif kind in {"binary", "index", "slice", "choose"}:
                pending.extend((child, bound) for child in (parts[1:] if kind == "binary" else parts)
                               if child is not None)
        self.lambda_names[key] = tuple(names.items())
        return self.lambda_names[key]

    def capture_charge(self, value, token):
        # Environments hold immutable references, not deep copies. Cumulative
        # accounting still bounds retained chains and repeatedly captured data.
        pending = [value]
        while pending:
            item = pending.pop()
            self.tick(token)
            self.capture_nodes += 1
            if type(item) is str:
                self.capture_bytes += len(item.encode("utf-8"))
            elif type(item) in (int, float, bool) or item is None:
                self.capture_bytes += len(str(item))
            elif type(item) is list:
                pending.extend(item)
            elif type(item) is dict:
                pending.extend(child for pair in item.items() for child in pair)
            # Previously created closures were charged at creation; count their
            # reference once, without revisiting their entire environment graph.
            if self.capture_nodes > 20000 or self.capture_bytes > MAX_JSON_BYTES:
                fail(token, "E_LIMIT", "Closure captures exceed the cumulative 20,000-node or 1 MiB limit.")

    def make_closure(self, node, scopes):
        self.capture_charge(None, node.token)  # Each closure itself occupies a node.
        captures = []
        for name, token in self.free_names(node):
            scope = next((scope for scope in reversed(scopes) if name in scope), None)
            if scope is None:
                fail(token, "E_NAME", f"Unknown variable {name!r} at closure creation.")
            self.capture_charge(name, node.token)
            self.capture_charge(scope[name], node.token)
            captures.append((name, scope[name]))
        location = f"{node.token.line}:{node.token.column}"
        if node.token.source_name:
            location = node.token.source_name + ":" + location
        return FunctionRef("fn@" + location, Closure(node, tuple(captures)))

    def tick(self, token):
        self.steps += 1
        if self.steps > self.max_steps:
            fail(token, "E_LIMIT", "Execution step limit reached; use a smaller input or simpler program.")

    def numeric(self, value, token):
        if not is_number(value):
            fail(token, "E_TYPE", "Expected a number; booleans and strings are not numbers.")
        return value

    def boolean(self, value, token):
        if type(value) is not bool:
            fail(token, "E_TYPE", "A condition must be true or false; use an explicit comparison.")
        return value

    def bounded(self, value, token):
        validate_value(value, token)
        return value

    def record_key(self, record, key, token):
        if type(record) is not dict or type(key) is not str:
            fail(token, "E_TYPE", "Record access requires a record and a string field name.")

    def field(self, record, key, token):
        if type(record) is NamespaceRef:
            identity = record.member(key)
            if identity is None:
                fail(token, "E_IMPORT", f"Module {record.path!r} has no exported function {key!r}.")
            return FunctionRef(identity)
        self.record_key(record, key, token)
        if key not in record:
            identity = record.get("sku", record.get("id"))
            context = f" on record {identity!r}" if isinstance(identity, (str, int)) else ""
            fail(token, "E_FIELD", f"Missing field {key!r}{context}. Use has() or get() for optional fields.")
        return record[key]

    def equal(self, a, b, token):
        self.tick(token)
        if is_number(a) and is_number(b):
            return a == b
        if type(a) is not type(b):
            return False
        if type(a) is NamespaceRef:
            return a.path == b.path
        if type(a) is list:
            return len(a) == len(b) and all(self.equal(x, y, token) for x, y in zip(a, b))
        if type(a) is dict:
            return a.keys() == b.keys() and all(self.equal(a[k], b[k], token) for k in a)
        return a == b

    def expr(self, node, scopes):
        self.tick(node.token)
        kind, parts, token = node.kind, node.parts, node.token
        if kind == "literal":
            return self.bounded(parts[0], token)
        if kind == "name":
            for scope in reversed(scopes):
                if parts[0] in scope:
                    return scope[parts[0]]
            environment = self.environment(token)
            if parts[0] in environment['namespaces']:
                return environment['namespaces'][parts[0]]
            if parts[0] in environment['functions']:
                return FunctionRef(environment['functions'][parts[0]])
            if parts[0] in BUILTINS:
                return FunctionRef(parts[0])
            fail(token, "E_NAME", f"Unknown variable {parts[0]!r}.")
        if kind == "lambda":
            return self.make_closure(node, scopes)
        if kind == "list":
            return self.bounded([self.expr(x, scopes) for x in parts[0]], token)
        if kind == "record":
            return self.bounded({key: self.expr(value, scopes) for key, value in parts[0]}, token)
        if kind == "field":
            return self.field(self.expr(parts[0], scopes), parts[1], token)
        if kind == "index":
            value, index = [self.expr(x, scopes) for x in parts]
            if type(value) is dict:
                return self.field(value, index, token)
            if type(value) not in (list, str) or type(index) is not int:
                fail(token, "E_TYPE", "Index a list or string with a nonnegative integer, or a record with a string.")
            if index < 0 or index >= len(value):
                fail(token, "E_INDEX", f"Index {index} is outside a sequence of length {len(value)}.")
            return value[index]
        if kind == "slice":
            value = self.expr(parts[0], scopes)
            if type(value) not in (list, str):
                fail(token, "E_TYPE", "Slice a list or string.")
            bounds = [self.expr(x, scopes) if x is not None else None for x in parts[1:]]
            if any(x is not None and (type(x) is not int or x < 0) for x in bounds):
                fail(token, "E_INDEX", "Slice bounds must be nonnegative integers.")
            return self.bounded(value[bounds[0]:bounds[1]], token)
        if kind == "choose":
            condition = self.boolean(self.expr(parts[0], scopes), token)
            return self.expr(parts[1] if condition else parts[2], scopes)
        if kind == "unary":
            op, expression = parts
            value = self.expr(expression, scopes)
            if op == "not":
                return not self.boolean(value, token)
            value = self.numeric(value, token)
            return -value if op == "-" else value
        if kind == "binary":
            op, lhs, rhs = parts
            a = self.expr(lhs, scopes)
            if op == "??":
                return self.expr(rhs, scopes) if a is None else a
            if op in {"and", "or"}:
                self.boolean(a, token)
                if (op == "and" and not a) or (op == "or" and a):
                    return a
                return self.boolean(self.expr(rhs, scopes), token)
            b = self.expr(rhs, scopes)
            if op in {"in", "not in"}:
                if type(b) is list:
                    result = any(self.equal(a, item, token) for item in b)
                elif type(b) in (dict, str) and type(a) is str:
                    result = a in b
                else:
                    fail(token, "E_TYPE", "Membership requires a list, or a string key/subsequence in a record/string.")
                return result if op == "in" else not result
            if op in {"==", "!="}:
                equal = self.equal(a, b, token)
                return equal if op == "==" else not equal
            if op in {"<", "<=", ">", ">="}:
                if not ((is_number(a) and is_number(b)) or (type(a) is str and type(b) is str)):
                    fail(token, "E_TYPE", "Compare two numbers or two strings; types must match.")
                return {"<": lambda: a < b, "<=": lambda: a <= b,
                        ">": lambda: a > b, ">=": lambda: a >= b}[op]()
            if op == "+" and type(a) is type(b) and type(a) in (str, list):
                return self.bounded(a + b, token)
            self.numeric(a, token)
            self.numeric(b, token)
            if op in {"/", "%"} and b == 0:
                fail(token, "E_ZERO", "Cannot divide by zero. Check the value before dividing.")
            try:
                result = {"+": lambda: a + b, "-": lambda: a - b, "*": lambda: a * b,
                          "/": lambda: a / b, "%": lambda: a % b}[op]()
            except OverflowError:
                fail(token, "E_VALUE", "Arithmetic result is too large.")
            return self.bounded(result, token)
        if kind == "call":
            callee, args = parts
            function = self.expr(callee, scopes)
            values = [self.expr(arg, scopes) for arg in args]
            return self.call_value(function, values, token)
        raise AssertionError(f"Unhandled expression {kind}")

    def call_value(self, callee, values, token):
        self.tick(token)
        if not self.is_callable(callee):
            fail(token, "E_CALL", "This value is not a function.")
        name = callee.name
        arity = self.callable_arity(callee)
        accepted = (arity,) if type(arity) is int else arity
        if len(values) not in accepted:
            fail(token, "E_ARITY", f"{name} expects {arity} argument(s), received {len(values)}.")
        self.depth += 1
        try:
            if self.depth > 48:
                fail(token, "E_LIMIT", "Function call depth exceeds 48; check recursive calls.")
            if callee.closure is None and name in BUILTINS:
                return self.builtin(name, values, token)
            closure = callee.closure
            function = closure.node if closure is not None else self.functions[name]
            if closure is not None:
                parameters, body, annotations, return_annotation = function.parts
                outer = [dict(closure.captures)]
            else:
                _, parameters, body = function.parts[:3]
                annotations = function.parts[3] if len(function.parts) > 3 else (None,) * len(parameters)
                return_annotation = function.parts[4] if len(function.parts) > 4 else None
                outer = []
            scope = {param.value: self.annotated(value, annotation, token, f"Parameter {param.value!r}")
                     for param, value, annotation in zip(parameters, values, annotations)}
            result = None
            try:
                if closure is not None:
                    result = self.expr(body, outer + [scope])
                else:
                    self.block(body, [scope], None)
            except Returned as returned:
                result = returned.value
            finally:
                self.clear_scope(scope)
            return self.annotated(result, return_annotation, token, f"Return value of {name!r}")
        except SigilError as error:
            # Each unwinding call adds one source frame, preserving the actual failure.
            frame = {"function": name, "line": token.line, "column": token.column}
            if getattr(token, "source_name", ""):
                frame["source_name"] = token.source_name
            error.call_trace = error.call_trace + (frame,)
            raise
        finally:
            self.depth -= 1

    def builtin(self, name, values, token):
        if name == "type_of" and type(values[0]) is NamespaceRef:
            return "namespace"
        from .stdlib import ARITIES, invoke
        if name in ARITIES:
            return self.bounded(invoke(self, name, values, token), token)
        value = values[0]
        if name == "len":
            if type(value) not in (list, dict, str):
                fail(token, "E_TYPE", "len() expects a list, record, or string.")
            return len(value)
        if name in {"has", "get"}:
            self.record_key(value, values[1], token)
            return values[1] in value if name == "has" else value.get(values[1], values[2])
        if name == "text":
            self.bounded(value, token)
            return self.bounded(value if type(value) is str else compact(value), token)
        for item in values:
            self.numeric(item, token)
        if name == "round":
            if type(values[1]) is not int or not 0 <= values[1] <= 10:
                fail(token, "E_VALUE", "round() requires a whole number of decimal places from 0 to 10.")
            return self.bounded(round(value, values[1]), token)
        if name == "fraction":
            ratio = Fraction(str(value))
            return self.bounded({"numerator": ratio.numerator, "denominator": ratio.denominator}, token)
        if name == "ceil_div":
            if any(type(item) is not int for item in values):
                fail(token, "E_TYPE", "ceil_div() requires two integers.")
            if values[1] == 0:
                fail(token, "E_ZERO", "Cannot divide by zero.")
            return self.bounded(-(-value // values[1]), token)
        result = {"ceil": lambda: math.ceil(value), "floor": lambda: math.floor(value),
                  "abs": lambda: abs(value), "min": lambda: min(values),
                  "max": lambda: max(values)}[name]()
        return self.bounded(result, token)

    def output(self, value, token):
        self.bounded(value, token)
        self.output_bytes += len(compact(value).encode("utf-8"))
        if self.output_bytes > MAX_JSON_BYTES or len(self.proposals) + len(self.notes) + len(self.values) >= 1000:
            fail(token, "E_LIMIT", "Preview output limit reached (1 MiB or 1,000 entries).")

    def clear_scope(self, scope):
        self.mutable.pop(id(scope), None)
        self.annotations.pop(id(scope), None)

    def child_block(self, body, scopes, rule, initial=None):
        scope = initial if initial is not None else {}
        try:
            self.block(body, scopes + [scope], rule)
        finally:
            self.clear_scope(scope)

    def block(self, body, scopes, rule):
        for node in body:
            if node.kind == "module_scope":
                continue
            self.tick(node.token)
            kind, parts, token = node.kind, node.parts, node.token
            if kind in {"let", "var"}:
                annotation = parts[2] if len(parts) > 2 else None
                name = parts[0].value
                scopes[-1][name] = self.annotated(self.expr(parts[1], scopes), annotation, token, f"Binding {name!r}")
                self.mutable.setdefault(id(scopes[-1]), set())
                if kind == "var":
                    self.mutable[id(scopes[-1])].add(name)
                self.annotations.setdefault(id(scopes[-1]), {})[name] = annotation
            elif kind == "set":
                name = parts[0].value
                scope = next((s for s in reversed(scopes) if name in s), None)
                if scope is None or name not in self.mutable.get(id(scope), ()):
                    fail(token, "E_MUTABILITY", "Only a 'var' binding can be changed with 'set'.")
                scope[name] = self.annotated(self.expr(parts[1], scopes), self.annotations.get(id(scope), {}).get(name), token, f"Binding {name!r}")
            elif kind in {"break", "continue"}:
                raise LoopSignal(kind)
            elif kind == "emit":
                value = self.expr(parts[0], scopes)
                self.output(value, token)
                self.values.append(value)
            elif kind == "require":
                condition = self.boolean(self.expr(parts[0], scopes), token)
                if not condition:
                    message = self.expr(parts[1], scopes)
                    if type(message) is not str:
                        fail(token, "E_TYPE", "A require failure message must be a string.")
                    fail(token, "E_REQUIRE", message)
            elif kind == "return":
                raise Returned(self.expr(parts[0], scopes))
            elif kind == "say":
                value = self.expr(parts[0], scopes)
                if type(value) is not str:
                    fail(token, "E_TYPE", "say expects a string; use text(value) to convert a value.")
                note = {"message": value, "rule": rule, "line": token.line}
                self.output(note, token)
                self.notes.append(note)
            elif kind == "when":
                condition = self.boolean(self.expr(parts[0], scopes), token)
                self.child_block(parts[1] if condition else parts[2], scopes, rule)
            elif kind == "for":
                iterable = self.expr(parts[1], scopes)
                if type(iterable) is not list:
                    fail(token, "E_TYPE", "for expects a list.")
                for value in iterable:
                    self.tick(token)
                    try:
                        self.child_block(parts[2], scopes, rule, {parts[0].value: value})
                    except LoopSignal as signal:
                        if signal.kind == "break":
                            break
            elif kind == "while":
                while self.boolean(self.expr(parts[0], scopes), token):
                    self.tick(token)
                    try:
                        self.child_block(parts[1], scopes, rule)
                    except LoopSignal as signal:
                        if signal.kind == "break":
                            break
            elif kind == "rule":
                self.child_block(parts[1], scopes, parts[0])
            elif kind == "propose":
                fields = {name: self.expr(value, scopes) for name, value in parts[1]}
                envelope = {"action": parts[0], "fields": fields, "rule": rule}
                self.bounded(envelope, token)
                identity = hashlib.sha256(compact(envelope).encode("utf-8")).hexdigest()
                if identity in self.seen:
                    self.duplicates += 1
                    continue
                proposal = dict(envelope, id=identity, requires_review=True,
                                source={"line": token.line, "column": token.column})
                self.output(proposal, token)
                self.seen.add(identity)
                self.proposals.append(proposal)
            # Function declarations are registered before execution.

    def execute(self):
        self.block(self.program, [self.data.copy()], None)
        return {"ok": True, "version": "0.4.0", "mode": "preview", "proposals": self.proposals,
                "notes": self.notes, "values": self.values, "diagnostics": [],
                "stats": {"steps": self.steps, "duplicates_collapsed": self.duplicates}}
