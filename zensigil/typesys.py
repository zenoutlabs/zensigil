"""Explicit, bounded runtime annotations; these do not claim static inference."""
from dataclasses import dataclass, field
from types import MappingProxyType
from .errors import fail

TYPE_NAMES = frozenset({'any', 'number', 'integer', 'string', 'boolean', 'list', 'record', 'null', 'function', 'namespace'})


@dataclass(frozen=True, eq=False)
class Closure:
    """Opaque immutable environment. Identity, not structural equality, is observable."""
    node: object
    captures: tuple


@dataclass(frozen=True)
class FunctionRef:
    name: str
    closure: object = field(default=None, repr=False)


@dataclass(frozen=True)
class NamespaceRef:
    """Opaque immutable module identity and exported function surface."""
    path: str
    members: tuple = field(repr=False)
    _lookup: object = field(init=False, repr=False, compare=False)

    def __post_init__(self):
        object.__setattr__(self, '_lookup', MappingProxyType(dict(self.members)))

    def member(self, name):
        return self._lookup.get(name)



def type_text(annotation):
    if type(annotation) is tuple:
        kind, inner = annotation
        if kind == 'union':
            return ' | '.join(type_text(item) for item in inner)
        return kind + '<' + type_text(inner) + '>'
    return annotation or 'any'


def matches(value, annotation, tick=None):
    if annotation is None:
        return True
    if tick is not None:
        tick()
    if type(annotation) is tuple:
        kind, inner = annotation
        if kind == 'union':
            return any(matches(value, item, tick) for item in inner)
        if kind == 'list':
            return type(value) is list and all(matches(item, inner, tick) for item in value)
        if kind == 'record':
            return type(value) is dict and all(type(key) is str and matches(item, inner, tick)
                                                for key, item in value.items())
        return False
    return annotation == 'any' or {
        'number': type(value) in (int, float), 'integer': type(value) is int,
        'string': type(value) is str, 'boolean': type(value) is bool,
        'list': type(value) is list, 'record': type(value) is dict,
        'null': value is None, 'function': type(value) is FunctionRef,
        'namespace': type(value) is NamespaceRef,
    }.get(annotation, False)


def enforce(value, annotation, token, label='Value', tick=None):
    if not matches(value, annotation, tick):
        fail(token, 'E_TYPE', f'{label} must have type {type_text(annotation)}.')
    return value
