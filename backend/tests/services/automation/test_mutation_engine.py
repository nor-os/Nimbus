"""
Overview: Unit tests for the config mutation engine.
Architecture: Test layer for activity catalog (Section 11.5)
Dependencies: pytest, app.services.automation.mutation_engine
Concepts: Config mutations, JSONB path traversal, rollback
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from app.services.automation.mutation_engine import MutationEngine, _get_nested, _set_nested, _delete_nested


class TestPathHelpers:
    """Test dot-notation path traversal helpers."""

    def test_get_nested_simple(self):
        data = {"a": {"b": {"c": 42}}}
        assert _get_nested(data, "a.b.c") == 42

    def test_get_nested_missing(self):
        data = {"a": {"b": 1}}
        assert _get_nested(data, "a.c") is None

    def test_get_nested_top_level(self):
        data = {"key": "value"}
        assert _get_nested(data, "key") == "value"

    def test_set_nested_creates_path(self):
        data = {}
        _set_nested(data, "a.b.c", 99)
        assert data == {"a": {"b": {"c": 99}}}

    def test_set_nested_overwrites(self):
        data = {"a": {"b": 1}}
        _set_nested(data, "a.b", 2)
        assert data["a"]["b"] == 2

    def test_delete_nested(self):
        data = {"a": {"b": 1, "c": 2}}
        _delete_nested(data, "a.b")
        assert data == {"a": {"c": 2}}

    def test_delete_nested_missing(self):
        data = {"a": 1}
        _delete_nested(data, "b")  # Should not raise


class TestMutationEngineValidation:
    """Test mutation validation logic."""

    def test_validate_valid_mutations(self):
        rules = [
            {"mutation_type": "SET", "parameter_path": "a.b", "value": 42},
            {"mutation_type": "INCREMENT", "parameter_path": "count", "amount": 1},
        ]
        errors = MutationEngine.validate_mutations(rules)
        assert errors == []

    def test_validate_missing_type(self):
        rules = [{"parameter_path": "a.b", "value": 42}]
        errors = MutationEngine.validate_mutations(rules)
        assert len(errors) > 0

    def test_validate_missing_path(self):
        rules = [{"mutation_type": "SET", "value": 42}]
        errors = MutationEngine.validate_mutations(rules)
        assert len(errors) > 0

    def test_validate_invalid_type(self):
        rules = [{"mutation_type": "INVALID", "parameter_path": "a.b"}]
        errors = MutationEngine.validate_mutations(rules)
        assert len(errors) > 0
