"""
Overview: CI attribute validation engine — validates CI attributes against class schemas.
Architecture: Schema-driven validation for CI create/update operations (Section 8)
Dependencies: app.models.cmdb.ci_class
Concepts: JSON Schema-like validation for CI attributes. Supports type checking, required fields,
    min/max ranges, regex patterns, and enum constraints. Class inheritance merges parent schemas.
"""

import logging
import re

logger = logging.getLogger(__name__)


class ValidationError(Exception):
    def __init__(self, message: str, field: str | None = None, code: str = "VALIDATION_ERROR"):
        self.message = message
        self.field = field
        self.code = code
        super().__init__(message)


class ValidationResult:
    def __init__(self) -> None:
        self.errors: list[dict] = []

    @property
    def is_valid(self) -> bool:
        return len(self.errors) == 0

    def add_error(self, field: str, message: str) -> None:
        self.errors.append({"field": field, "message": message})


def validate_ci_attributes(
    attributes: dict,
    class_schema: dict | None,
    attribute_definitions: list | None = None,
) -> ValidationResult:
    """Validate CI attributes against the class schema and attribute definitions.

    The class schema follows a simplified JSON Schema format:
    {
        "properties": {
            "field_name": {
                "type": "string|integer|number|boolean|array|object",
                "required": true/false,
                "min": ..., "max": ...,
                "pattern": "regex",
                "enum": [...],
                "description": "..."
            }
        },
        "required": ["field1", "field2"]
    }
    """
    result = ValidationResult()

    if not class_schema:
        return result

    properties = class_schema.get("properties", {})
    required_fields = class_schema.get("required", [])

    # Check required fields
    for field_name in required_fields:
        if field_name not in attributes or attributes[field_name] is None:
            result.add_error(field_name, f"Required field '{field_name}' is missing")

    # Validate each provided attribute
    for field_name, value in attributes.items():
        if field_name not in properties:
            continue  # Extra attributes are allowed

        prop = properties[field_name]
        _validate_field(result, field_name, value, prop)

    # Validate attribute definitions if provided
    if attribute_definitions:
        for attr_def in attribute_definitions:
            if hasattr(attr_def, "deleted_at") and attr_def.deleted_at is not None:
                continue
            name = attr_def.name if hasattr(attr_def, "name") else attr_def.get("name")
            is_required = (
                attr_def.is_required
                if hasattr(attr_def, "is_required")
                else attr_def.get("is_required", False)
            )
            if is_required and (name not in attributes or attributes.get(name) is None):
                result.add_error(name, f"Required attribute '{name}' is missing")

            if name in attributes and attributes[name] is not None:
                rules = (
                    attr_def.validation_rules
                    if hasattr(attr_def, "validation_rules")
                    else attr_def.get("validation_rules")
                )
                if rules:
                    _validate_field(result, name, attributes[name], rules)

    return result


def _validate_field(
    result: ValidationResult, field_name: str, value: object, prop: dict
) -> None:
    """Validate a single field value against its property definition."""
    expected_type = prop.get("type")
    if expected_type and not _check_type(value, expected_type):
        result.add_error(
            field_name,
            f"Expected type '{expected_type}' for '{field_name}', got {type(value).__name__}",
        )
        return

    if "min" in prop and isinstance(value, (int, float)) and value < prop["min"]:
        result.add_error(
            field_name,
            f"Value {value} is below minimum {prop['min']} for '{field_name}'",
        )

    if "max" in prop and isinstance(value, (int, float)) and value > prop["max"]:
        result.add_error(
            field_name,
            f"Value {value} exceeds maximum {prop['max']} for '{field_name}'",
        )

    if "pattern" in prop and isinstance(value, str) and not re.match(prop["pattern"], value):
        result.add_error(
            field_name,
            f"Value does not match pattern '{prop['pattern']}' for '{field_name}'",
        )

    if "enum" in prop and value not in prop["enum"]:
        result.add_error(
            field_name,
            f"Value '{value}' not in allowed values {prop['enum']} for '{field_name}'",
        )

    if "minLength" in prop and isinstance(value, str) and len(value) < prop["minLength"]:
        result.add_error(
            field_name,
            f"Length {len(value)} below minimum {prop['minLength']} for '{field_name}'",
        )

    if "maxLength" in prop and isinstance(value, str) and len(value) > prop["maxLength"]:
        result.add_error(
            field_name,
            f"Length {len(value)} exceeds maximum {prop['maxLength']} for '{field_name}'",
        )


def _check_type(value: object, expected_type: str) -> bool:
    """Check if a value matches the expected JSON Schema type."""
    type_map = {
        "string": str,
        "integer": int,
        "number": (int, float),
        "boolean": bool,
        "array": list,
        "object": dict,
    }
    expected = type_map.get(expected_type)
    if expected is None:
        return True
    return isinstance(value, expected)


def merge_schemas(parent_schema: dict | None, child_schema: dict | None) -> dict:
    """Merge parent and child class schemas. Child properties override parent."""
    if not parent_schema and not child_schema:
        return {}
    if not parent_schema:
        return child_schema or {}
    if not child_schema:
        return parent_schema

    merged = {
        "properties": {
            **parent_schema.get("properties", {}),
            **child_schema.get("properties", {}),
        },
        "required": list(
            set(parent_schema.get("required", []))
            | set(child_schema.get("required", []))
        ),
    }
    return merged
