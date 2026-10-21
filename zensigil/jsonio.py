"""Strict JSON at file/HTTP boundaries: reject duplicates and non-finite numbers."""
import json


def _constant(value):
    raise ValueError(f"JSON does not support {value}.")


def _integer(value):
    if len(value.lstrip("-")) > 101:
        raise ValueError("JSON integer is too large.")
    return int(value)


def _object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"JSON field {key!r} is repeated.")
        result[key] = value
    return result


def loads(raw):
    return json.loads(raw, parse_constant=_constant, parse_int=_integer, object_pairs_hook=_object)
