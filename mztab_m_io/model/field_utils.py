import re
from typing import Annotated, Any, List, OrderedDict, Union, get_args, get_origin

from pydantic import BaseModel


def sanitize_str(val: Union[None, str]) -> str:
    if not val:
        return ""
    if not isinstance(val, str):
        sanitized = str(val)
    sanitized = re.sub(r"[\t\n\r]", " ", val)
    sanitized = re.sub(r" +", " ", sanitized)

    if any(c in sanitized for c in ["\t", "\n", "\r"]):
        sanitized = sanitized.replace('"', '""')
        return f'"{sanitized}"'
    return sanitized


def _is_union(t):
    """True for typing.Union[...] or PEP 604 T | U."""
    origin = get_origin(t)
    try:
        import types
        return origin is Union or origin is types.UnionType
    except Exception:
        return origin is Union


def _unwrap_annotated(t):
    while get_origin(t) is Annotated:
        t = get_args(t)[0]
    return t


def _is_none(t):
    return t is type(None)


def _choose_union(members):
    """Prefer int, else first concrete non-None, else Any."""
    for m in members:
        if isinstance(m, type) and issubclass(m, int):
            return int
    for m in members:
        if isinstance(m, type):
            return m
    return Any


def _resolve(annotation):
    annotation = _unwrap_annotated(annotation)

    # ---- Union / Optional ----
    if _is_union(annotation):
        args = get_args(annotation)
        non_none = [a for a in args if not _is_none(a)]

        if not non_none:
            return False, Any

        if len(non_none) == 1:
            return _resolve(non_none[0])

        return False, _choose_union(non_none)

    # ---- List[T] ----
    origin = get_origin(annotation)
    if origin in (list, List):
        (item,) = get_args(annotation)

        item = _unwrap_annotated(item)

        # item is a union?
        if _is_union(item):
            item_args = get_args(item)
            non_none = [a for a in item_args if not _is_none(a)]

            if not non_none:
                return True, Any
            if len(non_none) == 1:
                inner = non_none[0]
                return True, inner if isinstance(inner, type) else Any

            return True, _choose_union(non_none)

        return True, item if isinstance(item, type) else Any

    # ---- Concrete type ----
    return False, annotation if isinstance(annotation, type) else Any


def get_field_type_info(model: type[BaseModel], field_name: str):
    field = model.model_fields[field_name]
    return _resolve(field.annotation)


def to_plain_dict(obj):
    """
    Recursively convert OrderedDict → dict.
    Works for nested structures (dicts, lists, tuples, sets).
    Other types are returned unchanged.
    """
    if isinstance(obj, OrderedDict):
        obj = dict(obj)

    if isinstance(obj, dict):
        return {k: to_plain_dict(v) for k, v in obj.items()}

    elif isinstance(obj, list):
        return [to_plain_dict(v) for v in obj]

    elif isinstance(obj, tuple):
        return tuple(to_plain_dict(v) for v in obj)

    elif isinstance(obj, set):
        return {to_plain_dict(v) for v in obj}

    return obj
