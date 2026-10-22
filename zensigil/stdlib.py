"""Pure, bounded standard functions. This module never performs host I/O."""
import json
import math
import re
from decimal import Decimal, DecimalException, ROUND_HALF_EVEN, localcontext
from functools import cmp_to_key
from .errors import fail
from .jsonio import loads

ARITIES = {
    "range": (1, 2, 3), "enumerate": 1, "zip": 2, "sum": 1,
    "sorted": 1, "reverse": 1, "unique": 1, "contains": 2,
    "record_keys": 1, "record_values": 1, "record_entries": 1, "record_merge": 2,
    "map": 2, "filter": 2, "fold": 3, "any": 2, "all": 2, "sort_by": 2,
    "group_by": 2, "count_by": 2, "partition": 2, "flat_map": 2,
    "find": 3, "find_index": 2, "take": 2, "drop": 2, "chunk": 2,
    "record_pick": 2, "record_omit": 2, "clamp": 3,
    "scan": 3, "min_by": 2, "max_by": 2, "sum_by": 2, "unique_by": 2,
    "frequencies": 1, "flatten": 1, "record_from_entries": 1,
    "type_of": 1, "lower": 1, "upper": 1, "trim": 1, "split": 2,
    "join": 2, "replace": 3, "starts_with": 2, "ends_with": 2,
    "parse_number": 1, "parse_json": 1, "json_text": 1,
    "dec": 1, "dec_add": 2, "dec_sub": 2, "dec_mul": 2,
    "dec_div": 3, "dec_round": 2, "dec_compare": 2,
}
_NUMBER = re.compile(r"-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?\Z")
_DECIMAL = re.compile(r"-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?\Z")


def _expect(value, kind, name, token):
    if type(value) is not kind:
        fail(token, "E_TYPE", f"{name}() expects {kind.__name__} values.")
    return value


def _places(value, name, token):
    if type(value) is not int or not 0 <= value <= 18:
        fail(token, "E_VALUE", f"{name}() decimal places must be an integer from 0 to 18.")
    return value


def _decimal(value, name, token):
    _expect(value, str, name, token)
    if len(value) > 102 or not _DECIMAL.fullmatch(value) or sum(c.isdigit() for c in value) > 100:
        fail(token, "E_VALUE", f"{name}() expects decimal text without exponents, with at most 100 digits.")
    return Decimal(value)


def _decimal_text(value, token):
    if not value.is_finite() or abs(value) > Decimal("1e100"):
        fail(token, "E_VALUE", "Decimal result must be finite with magnitude at most 1e100.")
    if value == 0:
        return "0"
    result = format(value, "f")
    if "." in result:
        result = result.rstrip("0").rstrip(".")
    if sum(c.isdigit() for c in result) > 100:
        fail(token, "E_VALUE", "Decimal result exceeds the 100-digit decimal-text limit.")
    return result


def _ordered_category(value, category, token, name):
    kind = "number" if type(value) in (int, float) else "string" if type(value) is str else None
    if kind is None or category is not None and category != kind:
        fail(token, "E_TYPE", f"{name}() requires all numbers or all strings.")
    return kind


def _ordered_keys(runtime, values, token, name):
    """Check before sorting, including singleton lists (bool is never numeric)."""
    category = None
    for value in values:
        runtime.tick(token)
        category = _ordered_category(value, category, token, name)


def _compare(runtime, token):
    def compare(a, b):
        runtime.tick(token)
        return (a > b) - (a < b)
    return compare


class _OutputBudget:
    """Account for a growing JSON result before adding its next piece.

    The root container is already counted. Shared subtrees are counted every
    time, as they will be when serialized; each visited node costs a step.
    Runtime validation remains authoritative for individual value types/limits.
    """
    def __init__(self, runtime, token, root_nodes=1):
        self.runtime, self.token = runtime, token
        self.nodes, self.characters = root_nodes, 0

    def add(self, value, depth):
        self.runtime.bounded(value, self.token)
        stack = [(value, depth)]
        while stack:
            item, level = stack.pop()
            self.runtime.tick(self.token)
            self.nodes += 1
            if self.nodes > 20000 or level > 32:
                fail(self.token, "E_VALUE", "Result exceeds the 20,000-node or 32-level nesting limit.")
            if type(item) is str:
                self.characters += len(item.encode("utf-8"))
                if self.characters > 1048576:
                    fail(self.token, "E_VALUE", "Result text exceeds the value size limit.")
            elif type(item) is list:
                stack.extend((child, level + 1) for child in item)
            elif type(item) is dict:
                stack.extend((child, level + 1) for pair in item.items() for child in pair)


def _count(value, name, token, positive=False):
    _expect(value, int, name, token)
    if value < (1 if positive else 0):
        qualifier = "positive" if positive else "nonnegative"
        fail(token, "E_VALUE", f"{name}() count must be a {qualifier} integer.")
    return value


def _collection_v05(runtime, name, values, token):
    items = _expect(values[0], list, name, token)
    if name in {"take", "drop", "chunk"}:
        count = _count(values[1], name, token, positive=name == "chunk")
        result, budget = [], _OutputBudget(runtime, token)
        if name == "chunk":
            for start in range(0, len(items), count):
                runtime.tick(token)
                budget.add([], 1)
                batch = []
                for index in range(start, min(start + count, len(items))):
                    budget.add(items[index], 2)
                    batch.append(items[index])
                result.append(batch)
        else:
            start, stop = (0, min(count, len(items))) if name == "take" else (min(count, len(items)), len(items))
            for index in range(start, stop):
                budget.add(items[index], 1)
                result.append(items[index])
        return runtime.bounded(result, token)

    callback = runtime.validate_callable(values[1], 1, token)
    if name == "find":
        runtime.bounded(values[2], token)
    if name in {"find", "find_index"}:
        for index, item in enumerate(items):
            runtime.tick(token)
            if runtime.boolean(runtime.call_value(callback, [item], token), token):
                return item if name == "find" else index
        return values[2] if name == "find" else -1

    budget = _OutputBudget(runtime, token)
    if name == "partition":
        result = {"matched": [], "unmatched": []}
        for key in result:
            budget.add(key, 1)
            budget.add([], 1)
    else:
        result = [] if name == "flat_map" else {}
    for item in items:
        runtime.tick(token)
        mapped = runtime.call_value(callback, [item], token)
        if name == "flat_map":
            _expect(mapped, list, name, token)
            if len(result) + len(mapped) > 10000:
                fail(token, "E_LIMIT", "flat_map() may produce at most 10,000 items.")
            for child in mapped:
                budget.add(child, 1)
            result.extend(mapped)
        elif name == "partition":
            key = "matched" if runtime.boolean(mapped, token) else "unmatched"
            budget.add(item, 2)
            result[key].append(item)
        else:
            key = _expect(mapped, str, name, token)
            if key not in result:
                if len(result) >= 10000:
                    fail(token, "E_LIMIT", f"{name}() may produce at most 10,000 fields.")
                budget.add(key, 1)
                budget.add([] if name == "group_by" else 0, 1)
                result[key] = [] if name == "group_by" else 0
            if name == "group_by":
                budget.add(item, 2)
                result[key].append(item)
            else:
                result[key] += 1
    return runtime.bounded(result, token)


def _collection_v06(runtime, name, values, token):
    items = _expect(values[0], list, name, token)
    budget = _OutputBudget(runtime, token)
    if name in {"flatten", "frequencies", "record_from_entries"}:
        result = [] if name == "flatten" else {}
        for item in items:
            runtime.tick(token)
            if name == "flatten":
                _expect(item, list, name, token)
                if len(result) + len(item) > 10000:
                    fail(token, "E_LIMIT", "flatten() may produce at most 10,000 items.")
                for child in item:
                    budget.add(child, 1)
                result.extend(item)
            else:
                if name == "frequencies":
                    key = _expect(item, str, name, token)
                    if key in result:
                        result[key] += 1
                        continue
                    child = 1
                else:
                    _expect(item, list, name, token)
                    if len(item) != 2:
                        fail(token, "E_VALUE", "record_from_entries() entries must be two-item [key, value] lists.")
                    key, child = item
                    _expect(key, str, name, token)
                    if key in result:
                        fail(token, "E_DUPLICATE", f"record_from_entries() repeats key {key!r}.")
                budget.add(key, 1)
                budget.add(child, 1)
                result[key] = child
        return runtime.bounded(result, token)

    callback = values[2] if name == "scan" else values[1]
    runtime.validate_callable(callback, 2 if name == "scan" else 1, token)
    if name == "scan":
        accumulator, result = runtime.bounded(values[1], token), []
        _OutputBudget(runtime, token, root_nodes=0).add(accumulator, 0)
        for item in items:
            runtime.tick(token)
            accumulator = runtime.call_value(callback, [accumulator, item], token)
            budget.add(accumulator, 1)
            result.append(accumulator)
        return runtime.bounded(result, token)
    if name == "unique_by":
        result, seen = [], []
        # Key storage also grows independently of output; bound it before retention.
        keys_budget = _OutputBudget(runtime, token)
        for item in items:
            runtime.tick(token)
            key = runtime.bounded(runtime.call_value(callback, [item], token), token)
            if not any(runtime.equal(key, previous, token) for previous in seen):
                keys_budget.add(key, 1)
                budget.add(item, 1)
                seen.append(key)
                result.append(item)
        return runtime.bounded(result, token)
    if name == "sum_by":
        result = 0
        for item in items:
            runtime.tick(token)
            mapped = runtime.numeric(runtime.call_value(callback, [item], token), token)
            result = runtime.bounded(result + mapped, token)
        return result
    best, best_key, category = None, None, None
    for item in items:
        runtime.tick(token)
        key = runtime.call_value(callback, [item], token)
        kind = "number" if type(key) in (int, float) else "string" if type(key) is str else None
        if kind is None or category is not None and kind != category:
            fail(token, "E_TYPE", f"{name}() requires all numeric or all string keys.")
        runtime.bounded(key, token)
        if category is None or (key < best_key if name == "min_by" else key > best_key):
            best, best_key = item, key
        category = kind
    return best


def invoke(runtime, name, values, token):
    """Dispatch only names in ARITIES; caller performs arity checking."""
    value = values[0]
    if name in {"scan", "min_by", "max_by", "sum_by", "unique_by", "frequencies", "flatten", "record_from_entries"}:
        return _collection_v06(runtime, name, values, token)
    if name in {"group_by", "count_by", "partition", "flat_map", "find", "find_index", "take", "drop", "chunk"}:
        return _collection_v05(runtime, name, values, token)
    if name in {"record_pick", "record_omit"}:
        _expect(value, dict, name, token)
        _expect(values[1], list, name, token)
        keys = set()
        for key in values[1]:
            runtime.tick(token)
            keys.add(_expect(key, str, name, token))
        result, budget = {}, _OutputBudget(runtime, token)
        for key, item in value.items():
            runtime.tick(token)
            if (key in keys) == (name == "record_pick"):
                budget.add(key, 1)
                budget.add(item, 1)
                result[key] = item
        return runtime.bounded(result, token)
    if name == "clamp":
        number, low, high = (runtime.numeric(item, token) for item in values)
        if low > high:
            fail(token, "E_VALUE", "clamp() lower bound cannot exceed its upper bound.")
        return low if number < low else high if number > high else number
    if name == "type_of":
        if runtime.is_callable(value):
            return "function"
        return {type(None): "null", bool: "boolean", int: "number", float: "number",
                str: "string", list: "list", dict: "record"}[type(value)]
    if name == "range":
        if any(type(item) is not int for item in values):
            fail(token, "E_TYPE", "range() needs integer bounds and step.")
        start, stop, step = (0, value, 1) if len(values) == 1 else (value, values[1], values[2] if len(values) == 3 else 1)
        if step == 0:
            fail(token, "E_VALUE", "range() step cannot be zero.")
        count = max(0, (stop - start + step - 1) // step) if step > 0 else max(0, (start - stop - step - 1) // (-step))
        if count > 10000:
            fail(token, "E_LIMIT", "range() may produce at most 10,000 items.")
        result = []
        for item in range(start, stop, step):
            runtime.tick(token)
            result.append(item)
        return runtime.bounded(result, token)
    if name in {"record_keys", "record_values", "record_entries", "record_merge"}:
        _expect(value, dict, name, token)
        budget = _OutputBudget(runtime, token)
        if name == "record_merge":
            _expect(values[1], dict, name, token)
            if len(value.keys() | values[1].keys()) > 10000:
                fail(token, "E_LIMIT", "record_merge() may produce at most 10,000 fields.")
            result = {}
            # Count only final fields. A large replaced value does not consume
            # the final result budget. Preserve the first record's key order.
            for key in dict.fromkeys((*value, *values[1])):
                runtime.tick(token)
                item = values[1][key] if key in values[1] else value[key]
                budget.add(key, 1)
                budget.add(item, 1)
                result[key] = item
        else:
            result = []
            for key, item in value.items():
                runtime.tick(token)
                entry = key if name == "record_keys" else item if name == "record_values" else {"key": key, "value": item}
                budget.add(entry, 1)
                result.append(entry)
        return runtime.bounded(result, token)
    if name == "contains":
        other = values[1]
        if type(value) is str:
            _expect(other, str, name, token)
            return other in value
        if type(value) is dict:
            _expect(other, str, name, token)
            return other in value
        _expect(value, list, name, token)
        return any(runtime.equal(item, other, token) for item in value)
    if name in {"enumerate", "zip", "sum", "sorted", "unique", "map", "filter", "fold", "any", "all", "sort_by"}:
        _expect(value, list, name, token)
        if name == "zip":
            _expect(values[1], list, name, token)
            result, budget = [], _OutputBudget(runtime, token)
            for left, right in zip(value, values[1]):
                runtime.tick(token)
                pair = [left, right]
                budget.add(pair, 1)
                result.append(pair)
            return runtime.bounded(result, token)
        if name == "enumerate":
            result, budget = [], _OutputBudget(runtime, token)
            for index, item in enumerate(value):
                runtime.tick(token)
                entry = {"index": index, "value": item}
                budget.add(entry, 1)
                result.append(entry)
            return runtime.bounded(result, token)
        if name == "sum":
            result = 0
            for item in value:
                runtime.tick(token)
                result = runtime.bounded(result + runtime.numeric(item, token), token)
            return result
        if name == "sorted":
            _ordered_keys(runtime, value, token, name)
            return runtime.bounded(sorted(value, key=cmp_to_key(_compare(runtime, token))), token)
        if name == "unique":
            result = []
            for item in value:
                runtime.tick(token)
                if not any(runtime.equal(item, seen, token) for seen in result):
                    result.append(item)
            return runtime.bounded(result, token)
        callback = values[2] if name == "fold" else values[1]
        runtime.validate_callable(callback, 2 if name == "fold" else 1, token)
        if name == "fold":
            result = values[1]
            for item in value:
                runtime.tick(token)
                result = runtime.bounded(runtime.call_value(callback, [result, item], token), token)
            return result
        result, decorated = [], []
        budget = _OutputBudget(runtime, token)
        keys_budget, key_category = _OutputBudget(runtime, token), None
        for index, item in enumerate(value):
            runtime.tick(token)
            mapped = runtime.call_value(callback, [item], token)
            if name in {"filter", "any", "all"}:
                predicate = runtime.boolean(mapped, token)
                if name == "any" and predicate:
                    return True
                if name == "all" and not predicate:
                    return False
                if name == "filter" and predicate:
                    result.append(item)
            elif name == "sort_by":
                # Validate each key before calling the next item. Retained keys
                # have a separate budget because they are not output values.
                key_category = _ordered_category(mapped, key_category, token, name)
                keys_budget.add(mapped, 1)
                decorated.append((mapped, index, item))
            else:
                budget.add(mapped, 1)
                result.append(mapped)
        if name == "any":
            return False
        if name == "all":
            return True
        if name == "sort_by":
            compare = _compare(runtime, token)
            decorated.sort(key=cmp_to_key(lambda left, right: compare(left[0], right[0])))
            result = [entry[2] for entry in decorated]
        return runtime.bounded(result, token)
    if name == "reverse":
        if type(value) not in (list, str):
            fail(token, "E_TYPE", "reverse() expects a list or string.")
        for _ in value:
            runtime.tick(token)
        return runtime.bounded(value[::-1], token)
    if name in {"lower", "upper", "trim", "split", "join", "replace", "starts_with", "ends_with"}:
        if name == "join":
            _expect(value, list, name, token)
            separator = _expect(values[1], str, name, token)
            size = max(0, len(value) - 1) * len(separator)
            for item in value:
                runtime.tick(token)
                _expect(item, str, name, token)
                size += len(item)
            if size > 65536:
                fail(token, "E_VALUE", "join() result exceeds 65,536 characters.")
            return runtime.bounded(separator.join(value), token)
        _expect(value, str, name, token)
        for other in values[1:]:
            _expect(other, str, name, token)
        if name in {"split", "replace"} and values[1] == "":
            fail(token, "E_VALUE", f"{name}() separator or search text cannot be empty.")
        if name == "split":
            if value.count(values[1]) >= 10000:
                fail(token, "E_LIMIT", "split() may produce at most 10,000 items.")
            result = value.split(values[1])
        elif name == "replace":
            size = len(value) + value.count(values[1]) * (len(values[2]) - len(values[1]))
            if size > 65536:
                fail(token, "E_VALUE", "replace() result exceeds 65,536 characters.")
            result = value.replace(values[1], values[2])
        else:
            result = {"lower": lambda: value.lower(), "upper": lambda: value.upper(),
                      "trim": lambda: value.strip(), "starts_with": lambda: value.startswith(values[1]),
                      "ends_with": lambda: value.endswith(values[1])}[name]()
        return runtime.bounded(result, token)
    if name == "parse_number":
        _expect(value, str, name, token)
        if len(value) > 256 or not _NUMBER.fullmatch(value):
            fail(token, "E_VALUE", "parse_number() expects complete JSON number text of at most 256 characters.")
        result = float(value) if any(c in value for c in ".eE") else int(value)
        return runtime.bounded(result, token)
    if name == "parse_json":
        _expect(value, str, name, token)
        try:
            result = loads(value)
        except (ValueError, RecursionError) as error:
            fail(token, "E_VALUE", f"parse_json() invalid JSON: {str(error)[:200]}")
        return runtime.bounded(result, token)
    if name == "json_text":
        runtime.bounded(value, token)
        return runtime.bounded(json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")), token)
    if name.startswith("dec"):
        a = _decimal(value, name, token)
        try:
            with localcontext() as context:
                context.prec = 240
                context.rounding = ROUND_HALF_EVEN
                if name == "dec":
                    result = a
                elif name == "dec_round":
                    places = _places(values[1], name, token)
                    result = a.quantize(Decimal(1).scaleb(-places))
                else:
                    b = _decimal(values[1], name, token)
                    if name == "dec_compare":
                        return (a > b) - (a < b)
                    if name == "dec_div":
                        places = _places(values[2], name, token)
                        if b == 0:
                            fail(token, "E_ZERO", "dec_div() cannot divide by zero.")
                        result = (a / b).quantize(Decimal(1).scaleb(-places))
                    else:
                        result = {"dec_add": lambda: a + b, "dec_sub": lambda: a - b,
                                  "dec_mul": lambda: a * b}[name]()
                return runtime.bounded(_decimal_text(result, token), token)
        except DecimalException:
            fail(token, "E_VALUE", f"{name}() result exceeds decimal arithmetic limits.")
    raise AssertionError(f"Unknown standard function {name}")
