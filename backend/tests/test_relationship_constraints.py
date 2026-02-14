"""
Overview: Tests for relationship type constraint validation in CIService.add_relationship().
Architecture: Unit tests for CI relationship constraint enforcement (Section 8)
Dependencies: pytest, unittest.mock, app.services.cmdb.ci_service
Concepts: Constraint validation — entity type, semantic category, semantic type checks
"""

import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.cmdb.ci import ConfigurationItem
from app.models.cmdb.ci_class import CIClass
from app.models.cmdb.ci_relationship import CIRelationship
from app.models.cmdb.relationship_type import RelationshipType
from app.services.cmdb.ci_service import CIService, CIServiceError


def _make_relationship_type(
    name: str = "contains",
    domain: str = "infrastructure",
    source_entity_type: str = "ci",
    target_entity_type: str = "ci",
    source_semantic_categories: list | None = None,
    target_semantic_categories: list | None = None,
    source_semantic_types: list | None = None,
    target_semantic_types: list | None = None,
) -> RelationshipType:
    rt = RelationshipType()
    rt.id = uuid.uuid4()
    rt.name = name
    rt.display_name = name.replace("_", " ").title()
    rt.inverse_name = f"inverse_{name}"
    rt.description = None
    rt.domain = domain
    rt.source_entity_type = source_entity_type
    rt.target_entity_type = target_entity_type
    rt.source_semantic_categories = source_semantic_categories
    rt.target_semantic_categories = target_semantic_categories
    rt.source_semantic_types = source_semantic_types
    rt.target_semantic_types = target_semantic_types
    rt.source_class_ids = None
    rt.target_class_ids = None
    rt.is_system = True
    rt.deleted_at = None
    rt.created_at = datetime.utcnow()
    rt.updated_at = datetime.utcnow()
    return rt


def _make_ci(
    ci_class_name: str = "virtual_machine",
    semantic_type_id: uuid.UUID | None = None,
) -> ConfigurationItem:
    ci = MagicMock(spec=ConfigurationItem)
    ci.id = uuid.uuid4()
    ci.tenant_id = uuid.uuid4()
    ci.name = f"test-{ci_class_name}"
    ci.deleted_at = None

    ci_class = MagicMock(spec=CIClass)
    ci_class.id = uuid.uuid4()
    ci_class.name = ci_class_name
    ci_class.semantic_type_id = semantic_type_id
    ci_class.semantic_type = None  # No eager-loaded category for unit tests
    ci.ci_class = ci_class
    return ci


class TestRelationshipConstraintValidation:
    """Tests for _validate_relationship_constraints."""

    def test_null_constraints_pass(self):
        """Null constraint arrays mean any-to-any — should pass."""
        rt = _make_relationship_type(
            source_semantic_categories=None,
            target_semantic_categories=None,
        )
        src = _make_ci("virtual_machine")
        tgt = _make_ci("database")
        svc = CIService(AsyncMock())
        # Should not raise
        svc._validate_relationship_constraints(rt, src, tgt)

    def test_entity_type_ci_passes(self):
        """When entity types are 'ci' and both endpoints are CIs, should pass."""
        rt = _make_relationship_type(
            source_entity_type="ci",
            target_entity_type="ci",
        )
        src = _make_ci()
        tgt = _make_ci()
        svc = CIService(AsyncMock())
        svc._validate_relationship_constraints(rt, src, tgt)

    def test_entity_type_any_passes(self):
        """When entity types are 'any', CIs should be accepted."""
        rt = _make_relationship_type(
            source_entity_type="any",
            target_entity_type="any",
        )
        src = _make_ci()
        tgt = _make_ci()
        svc = CIService(AsyncMock())
        svc._validate_relationship_constraints(rt, src, tgt)

    def test_entity_type_activity_rejects_ci(self):
        """When source entity type is 'activity', a CI source should be rejected."""
        rt = _make_relationship_type(
            source_entity_type="activity",
            target_entity_type="ci",
        )
        src = _make_ci()
        tgt = _make_ci()
        svc = CIService(AsyncMock())
        with pytest.raises(CIServiceError) as exc_info:
            svc._validate_relationship_constraints(rt, src, tgt)
        assert "CONSTRAINT_VIOLATION" in exc_info.value.code

    def test_source_semantic_category_violation(self):
        """When source category doesn't match constraint, should fail."""
        rt = _make_relationship_type(
            source_semantic_categories=["security"],
        )
        src = _make_ci("virtual_machine")
        # Set up a mock category on the semantic type
        src_type = MagicMock()
        src_type.category = MagicMock()
        src_type.category.name = "compute"
        src.ci_class.semantic_type = src_type
        src.ci_class.semantic_type_id = uuid.uuid4()

        tgt = _make_ci()
        svc = CIService(AsyncMock())
        with pytest.raises(CIServiceError) as exc_info:
            svc._validate_relationship_constraints(rt, src, tgt)
        assert "CONSTRAINT_VIOLATION" in exc_info.value.code

    def test_source_semantic_category_match_passes(self):
        """When source category matches constraint, should pass."""
        rt = _make_relationship_type(
            source_semantic_categories=["security", "monitoring"],
        )
        src = _make_ci("firewall")
        src_type = MagicMock()
        src_type.category = MagicMock()
        src_type.category.name = "security"
        src.ci_class.semantic_type = src_type
        src.ci_class.semantic_type_id = uuid.uuid4()

        tgt = _make_ci()
        svc = CIService(AsyncMock())
        svc._validate_relationship_constraints(rt, src, tgt)

    def test_target_semantic_category_violation(self):
        """When target category doesn't match constraint, should fail."""
        rt = _make_relationship_type(
            target_semantic_categories=["compute", "database"],
        )
        src = _make_ci()
        tgt = _make_ci("network_switch")
        tgt_type = MagicMock()
        tgt_type.category = MagicMock()
        tgt_type.category.name = "network"
        tgt.ci_class.semantic_type = tgt_type
        tgt.ci_class.semantic_type_id = uuid.uuid4()

        svc = CIService(AsyncMock())
        with pytest.raises(CIServiceError) as exc_info:
            svc._validate_relationship_constraints(rt, src, tgt)
        assert "CONSTRAINT_VIOLATION" in exc_info.value.code

    def test_no_semantic_type_passes_category_check(self):
        """CIs without a semantic type should pass category constraint (no category to check)."""
        rt = _make_relationship_type(
            source_semantic_categories=["security"],
        )
        src = _make_ci()
        src.ci_class.semantic_type_id = None
        src.ci_class.semantic_type = None

        tgt = _make_ci()
        svc = CIService(AsyncMock())
        # No semantic type means no category to check — should pass
        svc._validate_relationship_constraints(rt, src, tgt)
