"""
Overview: SCIM filter expression parser producing SQLAlchemy filter conditions.
Architecture: Filter parsing for SCIM list operations (Section 5.1)
Dependencies: sqlalchemy
Concepts: SCIM filtering, expression parsing, eq/ne/co/sw/ew operators
"""

import re

from sqlalchemy import and_, or_
from sqlalchemy.orm import InstrumentedAttribute


class SCIMFilterError(Exception):
    pass


# SCIM attribute name → SQLAlchemy column mapping (set per-resource)
_USER_ATTR_MAP: dict[str, str] = {
    "userName": "email",
    "displayName": "display_name",
    "active": "is_active",
    "externalId": "external_id",
    "emails.value": "email",
}

_GROUP_ATTR_MAP: dict[str, str] = {
    "displayName": "name",
}


def parse_scim_filter(filter_str: str, model, attr_map: dict[str, str] | None = None):
    """Parse a SCIM filter string into SQLAlchemy filter conditions.

    Supports: eq, ne, co, sw, ew, and, or
    """
    if not filter_str or not filter_str.strip():
        return None

    if attr_map is None:
        attr_map = _USER_ATTR_MAP

    return _parse_expression(filter_str.strip(), model, attr_map)


def _parse_expression(expr: str, model, attr_map: dict[str, str]):
    """Recursively parse filter expressions."""
    expr = expr.strip()

    # Handle 'and' / 'or' (case-insensitive, split on outermost)
    for op_name, op_func in [(" or ", or_), (" and ", and_)]:
        parts = _split_on_operator(expr, op_name)
        if len(parts) > 1:
            conditions = [_parse_expression(p, model, attr_map) for p in parts]
            return op_func(*conditions)

    # Handle parentheses
    if expr.startswith("(") and expr.endswith(")"):
        return _parse_expression(expr[1:-1], model, attr_map)

    # Parse comparison: attr op value
    match = re.match(
        r'(\S+)\s+(eq|ne|co|sw|ew)\s+"([^"]*)"',
        expr,
        re.IGNORECASE,
    )
    if not match:
        # Try boolean value
        match = re.match(
            r"(\S+)\s+(eq|ne)\s+(true|false)",
            expr,
            re.IGNORECASE,
        )
        if not match:
            raise SCIMFilterError(f"Cannot parse filter: {expr}")
        attr_name, operator, value = match.groups()
        value = value.lower() == "true"
    else:
        attr_name, operator, value = match.groups()

    # Map SCIM attribute to model column
    col_name = attr_map.get(attr_name)
    if not col_name:
        raise SCIMFilterError(f"Unknown attribute: {attr_name}")

    column = getattr(model, col_name, None)
    if column is None:
        raise SCIMFilterError(f"Column not found: {col_name}")

    operator = operator.lower()
    if operator == "eq":
        return column == value
    elif operator == "ne":
        return column != value
    elif operator == "co":
        return column.ilike(f"%{value}%")
    elif operator == "sw":
        return column.ilike(f"{value}%")
    elif operator == "ew":
        return column.ilike(f"%{value}")
    else:
        raise SCIMFilterError(f"Unsupported operator: {operator}")


def _split_on_operator(expr: str, operator: str) -> list[str]:
    """Split expression on top-level operator (not inside parentheses)."""
    parts = []
    depth = 0
    current = ""
    i = 0
    op_lower = operator.lower()

    while i < len(expr):
        if expr[i] == "(":
            depth += 1
        elif expr[i] == ")":
            depth -= 1

        if depth == 0 and expr[i:i + len(operator)].lower() == op_lower:
            parts.append(current.strip())
            current = ""
            i += len(operator)
            continue

        current += expr[i]
        i += 1

    if current.strip():
        parts.append(current.strip())

    return parts


def get_user_attr_map() -> dict[str, str]:
    return _USER_ATTR_MAP.copy()


def get_group_attr_map() -> dict[str, str]:
    return _GROUP_ATTR_MAP.copy()
