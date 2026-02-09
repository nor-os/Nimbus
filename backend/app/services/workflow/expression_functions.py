"""
Overview: Built-in functions for the workflow expression engine.
Architecture: Safe, allowlisted function library for expression evaluation (Section 5)
Dependencies: None (pure Python, datetime)
Concepts: String functions, date functions, type functions, JSON path, coalesce
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any


def fn_len(value: Any) -> int:
    """Return length of string, list, or dict."""
    if isinstance(value, (str, list, dict, tuple)):
        return len(value)
    raise ValueError(f"len() requires string/list/dict, got {type(value).__name__}")


def fn_contains(haystack: Any, needle: Any) -> bool:
    """Check if haystack contains needle (string or list)."""
    if isinstance(haystack, str) and isinstance(needle, str):
        return needle in haystack
    if isinstance(haystack, (list, tuple)):
        return needle in haystack
    raise ValueError("contains() requires string or list as first argument")


def fn_starts_with(text: str, prefix: str) -> bool:
    return str(text).startswith(str(prefix))


def fn_ends_with(text: str, suffix: str) -> bool:
    return str(text).endswith(str(suffix))


def fn_lower(text: str) -> str:
    return str(text).lower()


def fn_upper(text: str) -> str:
    return str(text).upper()


def fn_trim(text: str) -> str:
    return str(text).strip()


def fn_now() -> str:
    """Return current UTC timestamp as ISO string."""
    return datetime.now(UTC).isoformat()


def fn_format_date(iso_str: str, fmt: str) -> str:
    """Format an ISO date string using strftime format."""
    dt = datetime.fromisoformat(str(iso_str))
    return dt.strftime(str(fmt))


def fn_parse_int(value: Any) -> int:
    return int(value)


def fn_parse_float(value: Any) -> float:
    return float(value)


def fn_json_path(data: Any, path: str) -> Any:
    """Simple dot-notation JSON path access (e.g., 'a.b.c')."""
    current = data
    for segment in str(path).split("."):
        if isinstance(current, dict):
            if segment not in current:
                return None
            current = current[segment]
        elif isinstance(current, (list, tuple)):
            try:
                idx = int(segment)
                current = current[idx]
            except (ValueError, IndexError):
                return None
        else:
            return None
    return current


def fn_coalesce(*args: Any) -> Any:
    """Return the first non-null argument."""
    for arg in args:
        if arg is not None:
            return arg
    return None


def fn_type_of(value: Any) -> str:
    """Return the type name of a value."""
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "float"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    return type(value).__name__


def fn_to_json(value: Any) -> str:
    """Convert a value to JSON string."""
    return json.dumps(value)


def fn_from_json(text: str) -> Any:
    """Parse a JSON string to a value."""
    return json.loads(str(text))


def fn_split(text: str, delimiter: str) -> list[str]:
    """Split a string by delimiter."""
    return str(text).split(str(delimiter))


def fn_join(items: list, delimiter: str) -> str:
    """Join list items with delimiter."""
    return str(delimiter).join(str(item) for item in items)


def fn_abs(value: int | float) -> int | float:
    """Return absolute value."""
    return abs(value)


def fn_min(*args: Any) -> Any:
    """Return minimum value."""
    return min(args)


def fn_max(*args: Any) -> Any:
    """Return maximum value."""
    return max(args)


# ── Registry ─────────────────────────────────────────────

BUILTIN_FUNCTIONS: dict[str, Any] = {
    "len": fn_len,
    "contains": fn_contains,
    "startsWith": fn_starts_with,
    "endsWith": fn_ends_with,
    "lower": fn_lower,
    "upper": fn_upper,
    "trim": fn_trim,
    "now": fn_now,
    "formatDate": fn_format_date,
    "parseInt": fn_parse_int,
    "parseFloat": fn_parse_float,
    "jsonPath": fn_json_path,
    "coalesce": fn_coalesce,
    "typeOf": fn_type_of,
    "toJson": fn_to_json,
    "fromJson": fn_from_json,
    "split": fn_split,
    "join": fn_join,
    "abs": fn_abs,
    "min": fn_min,
    "max": fn_max,
}
