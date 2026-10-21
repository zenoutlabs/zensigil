"""Small, explicit input contracts. This is not an implementation of JSON Schema."""
import json
import math
import re

MAX_CONTRACT_BYTES = 262144
MAX_DIAGNOSTICS = 50
TYPES = {"object", "array", "string", "number", "integer", "boolean", "null"}
KEYWORDS = {"type", "properties", "required", "additionalProperties", "items", "minItems",
            "maxItems", "minLength", "maxLength", "minimum", "maximum", "enum", "title",
            "description", "uniqueBy"}


def diagnostic(code, path, message):
    return {"code": code, "message": message, "line": 1, "column": 1,
            "source_line": "", "data_path": path}


def field_path(path, key):
    if re.fullmatch(r"[A-Za-z_][A-Za-z_0-9]*", key):
        return f"{path}.{key}"
    return f"{path}[{json.dumps(key, ensure_ascii=True)}]"


def value_key(value):
    """Hashable structural value; numeric 1 equals 1.0, while true differs."""
    if type(value) in (int, float):
        return ("number", value)
    if type(value) is dict:
        return ("object", tuple(sorted((key, value_key(child)) for key, child in value.items())))
    if type(value) is list:
        return ("array", tuple(value_key(child) for child in value))
    return (type(value).__name__, value)


def matches(value, kind):
    return ((kind == "object" and type(value) is dict) or
            (kind == "array" and type(value) is list) or
            (kind == "string" and type(value) is str) or
            (kind == "number" and type(value) in (int, float)) or
            (kind == "integer" and type(value) is int) or
            (kind == "boolean" and type(value) is bool) or
            (kind == "null" and value is None))


def contract_diagnostics(contract):
    """Check the whole contract, including unused branches, before using it."""
    errors = []

    def add(path, message):
        if len(errors) < MAX_DIAGNOSTICS:
            errors.append(diagnostic("E_CONTRACT", path, message))

    # Bound and verify the entire JSON tree before recursive schema traversal.
    stack, count, characters = [(contract, 0)], 0, 0
    while stack:
        value, depth = stack.pop()
        count += 1
        if count > 10000 or depth > 32:
            return [diagnostic("E_CONTRACT", "$", "Contract exceeds 10,000 entries or 32 levels of nesting.")]
        if type(value) is dict:
            if any(type(key) is not str for key in value):
                return [diagnostic("E_CONTRACT", "$", "Contract field names must be strings.")]
            stack.extend((child, depth + 1) for pair in value.items() for child in pair)
        elif type(value) is list:
            stack.extend((child, depth + 1) for child in value)
        elif type(value) is str:
            try:
                characters += len(value.encode("utf-8"))
            except UnicodeError:
                return [diagnostic("E_CONTRACT", "$", "Contract must contain valid Unicode text.")]
            if characters > MAX_CONTRACT_BYTES:
                return [diagnostic("E_CONTRACT", "$", "Contract exceeds 256 KiB.")]
        elif value is None or type(value) is bool:
            pass
        elif type(value) in (int, float):
            if abs(value) > 1e100 or not math.isfinite(value):
                return [diagnostic("E_CONTRACT", "$", "Contract numbers must be finite and have magnitude at most 1e100.")]
        else:
            return [diagnostic("E_CONTRACT", "$", "Contract must contain only JSON values.")]
    if len(json.dumps(contract, ensure_ascii=True).encode("utf-8")) > MAX_CONTRACT_BYTES:
        return [diagnostic("E_CONTRACT", "$", "Contract exceeds 256 KiB.")]

    def visit(schema, path):
        if len(errors) >= MAX_DIAGNOSTICS:
            return
        if type(schema) is not dict:
            add(path, "Each contract must be an object, including items and property contracts.")
            return
        for key in schema:
            if key not in KEYWORDS:
                add(field_path(path, key), f"Unknown contract keyword {key!r}; this is the ZenSigil subset, not full JSON Schema.")
        if "type" in schema:
            kinds = schema["type"]
            kinds = kinds if type(kinds) is list else [kinds]
            if not kinds or any(type(k) is not str or k not in TYPES for k in kinds):
                add(field_path(path, "type"), "type must name a supported type or a nonempty list of supported types.")
            elif len(set(kinds)) != len(kinds):
                add(field_path(path, "type"), "type must not contain repeated types.")
        declared = schema.get("type")
        kinds = declared if type(declared) is list else [declared]
        if declared is not None and all(type(k) is str and k in TYPES for k in kinds):
            groups = (({"properties", "required", "additionalProperties"}, {"object"}),
                      ({"items", "minItems", "maxItems", "uniqueBy"}, {"array"}),
                      ({"minLength", "maxLength"}, {"string"}),
                      ({"minimum", "maximum"}, {"integer", "number"}))
            for keywords, applicable in groups:
                for key in sorted(keywords.intersection(schema)):
                    if not applicable.intersection(kinds):
                        add(field_path(path, key), f"{key} requires a compatible type: {' or '.join(sorted(applicable))}.")
        for key in ("title", "description"):
            if key in schema and type(schema[key]) is not str:
                add(field_path(path, key), f"{key} must be text.")
        if "properties" in schema:
            if type(schema["properties"]) is not dict:
                add(field_path(path, "properties"), "properties must map field names to contracts.")
            else:
                for key, child in schema["properties"].items():
                    visit(child, field_path(field_path(path, "properties"), key))
        if "required" in schema:
            value = schema["required"]
            if type(value) is not list or any(type(k) is not str for k in value):
                add(field_path(path, "required"), "required must be a list of field names.")
            elif len(set(value)) != len(value):
                add(field_path(path, "required"), "required must not repeat field names.")
            elif schema.get("additionalProperties") is False and type(schema.get("properties", {})) is dict:
                for key in value:
                    if key not in schema.get("properties", {}):
                        add(field_path(path, "required"), f"Required field {key!r} must appear in properties when additionalProperties is false.")
        if "additionalProperties" in schema and type(schema["additionalProperties"]) is not bool:
            add(field_path(path, "additionalProperties"), "additionalProperties must be true or false.")
        if "items" in schema:
            visit(schema["items"], field_path(path, "items"))
        for key in ("minItems", "maxItems", "minLength", "maxLength"):
            if key in schema and (type(schema[key]) is not int or schema[key] < 0):
                add(field_path(path, key), f"{key} must be a nonnegative integer.")
        for key in ("minimum", "maximum"):
            if key in schema and type(schema[key]) not in (int, float):
                add(field_path(path, key), f"{key} must be a number.")
        for low, high in (("minItems", "maxItems"), ("minLength", "maxLength"), ("minimum", "maximum")):
            if type(schema.get(low)) in (int, float) and type(schema.get(high)) in (int, float) and schema[low] > schema[high]:
                add(path, f"{low} must not exceed {high}.")
        if "enum" in schema and (type(schema["enum"]) is not list or not schema["enum"]):
            add(field_path(path, "enum"), "enum must be a nonempty list of permitted JSON values.")
        if "uniqueBy" in schema and (type(schema["uniqueBy"]) is not str or not schema["uniqueBy"]):
            add(field_path(path, "uniqueBy"), "uniqueBy must name a nonempty record field, such as sku or id.")

    visit(contract, "$")
    return errors


def input_diagnostics(data, contract):
    """Validate JSON data without modifying it; return up to 50 actionable errors."""
    errors = contract_diagnostics(contract)
    if errors:
        return errors

    return _validated_input_diagnostics(data, contract)


def _validated_input_diagnostics(data, contract, enum_values=None):
    """Match an already validated schema; share enum sets only within one run.

    Callers must validate the entire contract before using this internal helper.
    Diagnostics remain local to each value; the caller enforces any batch limit.
    """
    errors = []
    if enum_values is None:
        enum_values = {}

    def add(path, message, context):
        if len(errors) < MAX_DIAGNOSTICS:
            errors.append(diagnostic("E_INPUT_DATA", path, message + context))

    def visit(value, schema, path, context=""):
        if len(errors) >= MAX_DIAGNOSTICS:
            return
        if type(value) is dict:
            for key in ("sku", "id"):
                identifier = value.get(key)
                if type(identifier) in (str, int, float):
                    label = str(identifier)
                    context = f" (record {key}={label[:100]!r})"
                    break
        if "type" in schema:
            kinds = schema["type"] if type(schema["type"]) is list else [schema["type"]]
            if not any(matches(value, kind) for kind in kinds):
                actual = next(kind for kind in ("null", "boolean", "integer", "number", "string", "array", "object") if matches(value, kind))
                add(path, f"Expected {' or '.join(kinds)}; received {actual}. Fix the input value; values are not converted automatically.", context)
                return
        if "enum" in schema:
            if id(schema) not in enum_values:
                enum_values[id(schema)] = {value_key(option) for option in schema["enum"]}
            if value_key(value) not in enum_values[id(schema)]:
                choices = json.dumps(schema["enum"], ensure_ascii=True)
                add(path, f"Choose a permitted value from {choices[:200]}.", context)
        if type(value) is dict:
            properties = schema.get("properties", {})
            for key in schema.get("required", []):
                if key not in value:
                    add(field_path(path, key), f"Required field {key!r} is missing. Add it to this record.", context)
            for key, child in value.items():
                if key in properties:
                    visit(child, properties[key], field_path(path, key), context)
                elif schema.get("additionalProperties") is False:
                    add(field_path(path, key), f"Unexpected field {key!r}. Remove it or declare it in the contract.", context)
        elif type(value) is list:
            if "minItems" in schema and len(value) < schema["minItems"]:
                add(path, f"Expected at least {schema['minItems']} item(s); received {len(value)}.", context)
            if "maxItems" in schema and len(value) > schema["maxItems"]:
                add(path, f"Expected at most {schema['maxItems']} item(s); received {len(value)}.", context)
            seen = {}
            for index, child in enumerate(value):
                child_path = f"{path}[{index}]"
                if "items" in schema:
                    visit(child, schema["items"], child_path, context)
                if "uniqueBy" in schema:
                    key = schema["uniqueBy"]
                    identifier = child.get(key) if type(child) is dict else None
                    if identifier is None or type(identifier) not in (str, int, float, bool):
                        add(field_path(child_path, key), f"uniqueBy requires every item to be a record with a non-null string, number, or boolean {key!r}.", context)
                    else:
                        token = ("number" if type(identifier) in (int, float) else type(identifier).__name__, identifier)
                        if token in seen:
                            add(field_path(child_path, key), f"Duplicate {key} {identifier!r}; first appears at {path}[{seen[token]}]. Use a unique value for each record.", context)
                        else:
                            seen[token] = index
                if len(errors) >= MAX_DIAGNOSTICS:
                    break
        elif type(value) is str:
            if "minLength" in schema and len(value) < schema["minLength"]:
                add(path, f"Expected at least {schema['minLength']} character(s); received {len(value)}.", context)
            if "maxLength" in schema and len(value) > schema["maxLength"]:
                add(path, f"Expected at most {schema['maxLength']} character(s); received {len(value)}.", context)
        elif type(value) in (int, float):
            if "minimum" in schema and value < schema["minimum"]:
                add(path, f"Must be at least {schema['minimum']}; received {value}.", context)
            if "maximum" in schema and value > schema["maximum"]:
                add(path, f"Must be at most {schema['maximum']}; received {value}.", context)

    visit(data, contract, "$")
    return errors
