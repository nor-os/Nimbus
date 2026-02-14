"""
Overview: Tests for CI class ↔ activity association FK-based creation and backward compat.
Architecture: Unit tests for association service FK support (Section 8)
Dependencies: pytest, unittest.mock, app.services.cmdb.ci_class_activity_service
Concepts: FK-based association, backward compat with legacy string, operational relationship types
"""

import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.cmdb.ci_class_activity_association import CIClassActivityAssociation
from app.models.cmdb.relationship_type import RelationshipType
from app.services.cmdb.ci_class_activity_service import (
    CIClassActivityService,
    CIClassActivityServiceError,
)


def _make_assoc(
    relationship_type: str | None = None,
    relationship_type_id: uuid.UUID | None = None,
) -> CIClassActivityAssociation:
    assoc = CIClassActivityAssociation()
    assoc.id = uuid.uuid4()
    assoc.tenant_id = uuid.uuid4()
    assoc.ci_class_id = uuid.uuid4()
    assoc.activity_template_id = uuid.uuid4()
    assoc.relationship_type = relationship_type
    assoc.relationship_type_id = relationship_type_id
    assoc.created_at = datetime.utcnow()
    assoc.updated_at = datetime.utcnow()
    assoc.deleted_at = None
    return assoc


class TestAssociationFKCreation:
    """Tests for association creation with FK relationship_type_id."""

    @pytest.mark.asyncio
    async def test_create_with_fk(self):
        """Creating with relationship_type_id should succeed."""
        db = AsyncMock()
        # Duplicate check returns None
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        db.execute.return_value = result_mock
        db.flush = AsyncMock()

        rel_type_id = str(uuid.uuid4())
        tenant_id = str(uuid.uuid4())

        svc = CIClassActivityService(db)
        assoc = await svc.create_association(tenant_id, {
            "ci_class_id": str(uuid.uuid4()),
            "activity_template_id": str(uuid.uuid4()),
            "relationship_type_id": rel_type_id,
        })
        assert assoc.relationship_type_id == rel_type_id
        db.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_with_legacy_string(self):
        """Creating with legacy relationship_type string should still work."""
        db = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        db.execute.return_value = result_mock
        db.flush = AsyncMock()

        tenant_id = str(uuid.uuid4())

        svc = CIClassActivityService(db)
        assoc = await svc.create_association(tenant_id, {
            "ci_class_id": str(uuid.uuid4()),
            "activity_template_id": str(uuid.uuid4()),
            "relationship_type": "performed_on",
        })
        assert assoc.relationship_type == "performed_on"
        assert assoc.relationship_type_id is None

    @pytest.mark.asyncio
    async def test_create_with_both_fk_and_string(self):
        """Creating with both FK and string should set both."""
        db = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        db.execute.return_value = result_mock
        db.flush = AsyncMock()

        rel_type_id = str(uuid.uuid4())
        tenant_id = str(uuid.uuid4())

        svc = CIClassActivityService(db)
        assoc = await svc.create_association(tenant_id, {
            "ci_class_id": str(uuid.uuid4()),
            "activity_template_id": str(uuid.uuid4()),
            "relationship_type": "performed_on",
            "relationship_type_id": rel_type_id,
        })
        assert assoc.relationship_type == "performed_on"
        assert assoc.relationship_type_id == rel_type_id


class TestOperationalRelationshipTypes:
    """Tests for listing operational relationship types."""

    @pytest.mark.asyncio
    async def test_list_operational_types(self):
        """Should return relationship types with domain IN (operational, both)."""
        rt1 = RelationshipType()
        rt1.id = uuid.uuid4()
        rt1.name = "performed_on"
        rt1.domain = "operational"
        rt1.deleted_at = None

        rt2 = RelationshipType()
        rt2.id = uuid.uuid4()
        rt2.name = "contains"
        rt2.domain = "infrastructure"
        rt2.deleted_at = None

        db = AsyncMock()
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = [rt1]
        result_mock = MagicMock()
        result_mock.scalars.return_value = scalars_mock
        db.execute.return_value = result_mock

        svc = CIClassActivityService(db)
        results = await svc.list_operational_relationship_types()
        assert len(results) == 1
        assert results[0].name == "performed_on"
