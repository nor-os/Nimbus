"""
Overview: Tests for CMDB validation service — schema validation, type checking,
    range validation, pattern matching, enum constraints, and schema merging.
Architecture: Unit tests for CMDB validation engine (Section 8)
Dependencies: pytest, app.services.cmdb.validation_service
Concepts: JSON Schema-like validation, type checking, range/pattern/enum rules,
    attribute definitions, class schema inheritance
"""

from app.services.cmdb.validation_service import (
    ValidationError,
    ValidationResult,
    merge_schemas,
    validate_ci_attributes,
)


class SimpleAttrDef:
    """Minimal attribute definition for testing purposes."""

    def __init__(
        self, name, is_required=False, validation_rules=None, deleted_at=None
    ):
        self.name = name
        self.is_required = is_required
        self.validation_rules = validation_rules
        self.deleted_at = deleted_at


class TestValidationResult:
    """Tests for ValidationResult class."""

    def test_initial_is_valid(self):
        result = ValidationResult()
        assert result.is_valid is True

    def test_add_error_makes_invalid(self):
        result = ValidationResult()
        result.add_error("cpu", "Required field missing")
        assert result.is_valid is False

    def test_multiple_errors(self):
        result = ValidationResult()
        result.add_error("cpu", "Error 1")
        result.add_error("ram", "Error 2")
        assert len(result.errors) == 2
        assert result.is_valid is False


class TestValidationError:
    """Tests for ValidationError exception class."""

    def test_error_creation(self):
        error = ValidationError("Invalid value", field="cpu", code="TYPE_ERROR")
        assert error.message == "Invalid value"
        assert error.field == "cpu"
        assert error.code == "TYPE_ERROR"

    def test_default_code(self):
        error = ValidationError("Test message")
        assert error.code == "VALIDATION_ERROR"

    def test_is_exception(self):
        error = ValidationError("Test")
        assert isinstance(error, Exception)


class TestValidateCIAttributes:
    """Tests for validate_ci_attributes function."""

    def test_no_schema_returns_valid(self):
        result = validate_ci_attributes({"any": "thing", "other": 42}, None)
        assert result.is_valid is True
        assert len(result.errors) == 0

    def test_empty_schema_returns_valid(self):
        result = validate_ci_attributes({"any": "thing"}, {})
        assert result.is_valid is True
        assert len(result.errors) == 0

    def test_required_field_missing(self):
        schema = {
            "properties": {"cpu": {"type": "integer"}},
            "required": ["cpu"],
        }
        result = validate_ci_attributes({}, schema)
        assert result.is_valid is False
        assert len(result.errors) == 1
        assert result.errors[0]["field"] == "cpu"
        assert "required" in result.errors[0]["message"].lower()

    def test_required_field_present(self):
        schema = {
            "properties": {"cpu": {"type": "integer"}},
            "required": ["cpu"],
        }
        result = validate_ci_attributes({"cpu": 4}, schema)
        assert result.is_valid is True

    def test_required_field_none_value(self):
        schema = {
            "properties": {"cpu": {"type": "integer"}},
            "required": ["cpu"],
        }
        result = validate_ci_attributes({"cpu": None}, schema)
        assert result.is_valid is False
        assert result.errors[0]["field"] == "cpu"

    def test_type_string_valid(self):
        schema = {"properties": {"name": {"type": "string"}}}
        result = validate_ci_attributes({"name": "hello"}, schema)
        assert result.is_valid is True

    def test_type_string_invalid(self):
        schema = {"properties": {"name": {"type": "string"}}}
        result = validate_ci_attributes({"name": 42}, schema)
        assert result.is_valid is False
        assert result.errors[0]["field"] == "name"
        assert "type" in result.errors[0]["message"].lower()

    def test_type_integer_valid(self):
        schema = {"properties": {"cpu": {"type": "integer"}}}
        result = validate_ci_attributes({"cpu": 4}, schema)
        assert result.is_valid is True

    def test_type_integer_invalid(self):
        schema = {"properties": {"cpu": {"type": "integer"}}}
        result = validate_ci_attributes({"cpu": "four"}, schema)
        assert result.is_valid is False
        assert result.errors[0]["field"] == "cpu"

    def test_type_number_accepts_int(self):
        schema = {"properties": {"value": {"type": "number"}}}
        result = validate_ci_attributes({"value": 4}, schema)
        assert result.is_valid is True

    def test_type_number_accepts_float(self):
        schema = {"properties": {"value": {"type": "number"}}}
        result = validate_ci_attributes({"value": 4.5}, schema)
        assert result.is_valid is True

    def test_type_boolean_valid(self):
        schema = {"properties": {"enabled": {"type": "boolean"}}}
        result = validate_ci_attributes({"enabled": True}, schema)
        assert result.is_valid is True

    def test_type_boolean_invalid(self):
        schema = {"properties": {"enabled": {"type": "boolean"}}}
        result = validate_ci_attributes({"enabled": "true"}, schema)
        assert result.is_valid is False
        assert result.errors[0]["field"] == "enabled"

    def test_type_array_valid(self):
        schema = {"properties": {"tags": {"type": "array"}}}
        result = validate_ci_attributes({"tags": [1, 2, 3]}, schema)
        assert result.is_valid is True

    def test_type_object_valid(self):
        schema = {"properties": {"metadata": {"type": "object"}}}
        result = validate_ci_attributes({"metadata": {"a": 1}}, schema)
        assert result.is_valid is True

    def test_min_valid(self):
        schema = {"properties": {"cpu": {"type": "integer", "min": 1}}}
        result = validate_ci_attributes({"cpu": 2}, schema)
        assert result.is_valid is True

    def test_min_invalid(self):
        schema = {"properties": {"cpu": {"type": "integer", "min": 1}}}
        result = validate_ci_attributes({"cpu": 0}, schema)
        assert result.is_valid is False
        assert result.errors[0]["field"] == "cpu"
        assert "min" in result.errors[0]["message"].lower()

    def test_max_valid(self):
        schema = {"properties": {"cpu": {"type": "integer", "max": 10}}}
        result = validate_ci_attributes({"cpu": 5}, schema)
        assert result.is_valid is True

    def test_max_invalid(self):
        schema = {"properties": {"cpu": {"type": "integer", "max": 10}}}
        result = validate_ci_attributes({"cpu": 15}, schema)
        assert result.is_valid is False
        assert result.errors[0]["field"] == "cpu"
        assert "max" in result.errors[0]["message"].lower()

    def test_min_max_range(self):
        schema = {
            "properties": {"cpu": {"type": "integer", "min": 1, "max": 10}},
        }
        result = validate_ci_attributes({"cpu": 5}, schema)
        assert result.is_valid is True

    def test_pattern_valid(self):
        schema = {
            "properties": {"name": {"type": "string", "pattern": "^[a-z]+$"}},
        }
        result = validate_ci_attributes({"name": "hello"}, schema)
        assert result.is_valid is True

    def test_pattern_invalid(self):
        schema = {
            "properties": {"name": {"type": "string", "pattern": "^[a-z]+$"}},
        }
        result = validate_ci_attributes({"name": "Hello123"}, schema)
        assert result.is_valid is False
        assert result.errors[0]["field"] == "name"
        assert "pattern" in result.errors[0]["message"].lower()

    def test_enum_valid(self):
        schema = {
            "properties": {
                "status": {"type": "string", "enum": ["a", "b", "c"]},
            },
        }
        result = validate_ci_attributes({"status": "a"}, schema)
        assert result.is_valid is True

    def test_enum_invalid(self):
        schema = {
            "properties": {
                "status": {"type": "string", "enum": ["a", "b", "c"]},
            },
        }
        result = validate_ci_attributes({"status": "d"}, schema)
        assert result.is_valid is False
        assert result.errors[0]["field"] == "status"
        msg = result.errors[0]["message"].lower()
        assert "allowed" in msg or "enum" in msg

    def test_min_length_valid(self):
        schema = {
            "properties": {"name": {"type": "string", "minLength": 3}},
        }
        result = validate_ci_attributes({"name": "hello"}, schema)
        assert result.is_valid is True

    def test_min_length_invalid(self):
        schema = {
            "properties": {"name": {"type": "string", "minLength": 3}},
        }
        result = validate_ci_attributes({"name": "hi"}, schema)
        assert result.is_valid is False
        assert result.errors[0]["field"] == "name"
        assert "length" in result.errors[0]["message"].lower()

    def test_max_length_valid(self):
        schema = {
            "properties": {"name": {"type": "string", "maxLength": 5}},
        }
        result = validate_ci_attributes({"name": "hi"}, schema)
        assert result.is_valid is True

    def test_max_length_invalid(self):
        schema = {
            "properties": {"name": {"type": "string", "maxLength": 5}},
        }
        result = validate_ci_attributes({"name": "toolong"}, schema)
        assert result.is_valid is False
        assert result.errors[0]["field"] == "name"
        assert "length" in result.errors[0]["message"].lower()

    def test_extra_attributes_allowed(self):
        schema = {"properties": {"cpu": {"type": "integer"}}}
        result = validate_ci_attributes({"cpu": 4, "gpu": "nvidia"}, schema)
        assert result.is_valid is True

    def test_unknown_type_passes(self):
        schema = {"properties": {"value": {"type": "foobar"}}}
        result = validate_ci_attributes({"value": "anything"}, schema)
        assert result.is_valid is True

    def test_multiple_errors(self):
        schema = {
            "properties": {
                "cpu": {"type": "integer"},
                "ram": {"type": "integer"},
            },
            "required": ["cpu", "ram"],
        }
        result = validate_ci_attributes({}, schema)
        assert result.is_valid is False
        assert len(result.errors) == 2
        error_fields = {e["field"] for e in result.errors}
        assert "cpu" in error_fields
        assert "ram" in error_fields


class TestValidateWithAttributeDefinitions:
    """Tests for validation with attribute definitions."""

    def test_required_attr_def_missing(self):
        """Attr def validation requires a truthy class_schema."""
        schema = {"properties": {}}
        attr_defs = [SimpleAttrDef(name="ip", is_required=True)]
        result = validate_ci_attributes(
            {}, schema, attribute_definitions=attr_defs
        )
        assert result.is_valid is False
        assert len(result.errors) == 1
        assert result.errors[0]["field"] == "ip"
        assert "required" in result.errors[0]["message"].lower()

    def test_required_attr_def_present(self):
        schema = {"properties": {}}
        attr_defs = [SimpleAttrDef(name="ip", is_required=True)]
        result = validate_ci_attributes(
            {"ip": "10.0.0.1"}, schema, attribute_definitions=attr_defs
        )
        assert result.is_valid is True

    def test_attr_def_with_validation_rules(self):
        schema = {"properties": {}}
        attr_defs = [
            SimpleAttrDef(
                name="ip",
                is_required=True,
                validation_rules={
                    "type": "string",
                    "pattern": r"^\d+\.\d+\.\d+\.\d+$",
                },
            )
        ]
        result = validate_ci_attributes(
            {"ip": "10.0.0.1"}, schema, attribute_definitions=attr_defs
        )
        assert result.is_valid is True

        result = validate_ci_attributes(
            {"ip": "not-an-ip"}, schema, attribute_definitions=attr_defs
        )
        assert result.is_valid is False
        assert result.errors[0]["field"] == "ip"

    def test_attr_defs_skipped_when_no_schema(self):
        """When class_schema is None, attr defs are not validated."""
        attr_defs = [SimpleAttrDef(name="ip", is_required=True)]
        result = validate_ci_attributes(
            {}, None, attribute_definitions=attr_defs
        )
        assert result.is_valid is True

    def test_deleted_attr_def_skipped(self):
        from datetime import datetime

        schema = {"properties": {}}
        attr_defs = [
            SimpleAttrDef(
                name="ip",
                is_required=True,
                deleted_at=datetime.now(),
            )
        ]
        result = validate_ci_attributes(
            {}, schema, attribute_definitions=attr_defs
        )
        assert result.is_valid is True


class TestMergeSchemas:
    """Tests for schema merging functionality."""

    def test_both_none(self):
        result = merge_schemas(None, None)
        assert result == {}

    def test_parent_only(self):
        parent = {"properties": {"cpu": {"type": "integer"}}}
        result = merge_schemas(parent, None)
        assert result == parent

    def test_child_only(self):
        child = {"properties": {"ram": {"type": "integer"}}}
        result = merge_schemas(None, child)
        assert result == child

    def test_merge_properties(self):
        parent = {"properties": {"cpu": {"type": "integer"}}}
        child = {"properties": {"ram": {"type": "integer"}}}
        result = merge_schemas(parent, child)
        assert "cpu" in result["properties"]
        assert "ram" in result["properties"]

    def test_child_overrides_parent(self):
        parent = {"properties": {"cpu": {"type": "integer", "min": 1}}}
        child = {"properties": {"cpu": {"type": "integer", "min": 2}}}
        result = merge_schemas(parent, child)
        assert result["properties"]["cpu"]["min"] == 2

    def test_merge_required(self):
        parent = {
            "properties": {"cpu": {"type": "integer"}},
            "required": ["cpu"],
        }
        child = {
            "properties": {"ram": {"type": "integer"}},
            "required": ["ram"],
        }
        result = merge_schemas(parent, child)
        assert "cpu" in result["required"]
        assert "ram" in result["required"]
        assert len(result["required"]) == 2
