"""
Overview: Tests for semantic layer data models — table names, columns, soft deletes,
    relationships, and unique constraints.
Architecture: Unit tests for semantic data layer (Section 5)
Dependencies: pytest, app.models.semantic_type
Concepts: Model validation, table schema verification, relationship integrity
"""

import uuid

from app.models.semantic_type import (
    SemanticCategory,
    SemanticProvider,
    SemanticRelationshipKind,
    SemanticResourceType,
)


class TestSemanticCategoryModel:
    """Test SemanticCategory model."""

    def test_tablename(self):
        assert SemanticCategory.__tablename__ == "semantic_categories"

    def test_creation(self):
        cat = SemanticCategory(
            name="compute",
            display_name="Compute",
            description="Virtual machines and containers",
            icon="server",
            sort_order=1,
        )
        assert cat.name == "compute"
        assert cat.display_name == "Compute"
        assert cat.sort_order == 1

    def test_has_soft_delete(self):
        columns = {col.name for col in SemanticCategory.__table__.columns}
        assert "deleted_at" in columns

    def test_has_timestamps(self):
        columns = {col.name for col in SemanticCategory.__table__.columns}
        assert "created_at" in columns
        assert "updated_at" in columns

    def test_has_id(self):
        columns = {col.name for col in SemanticCategory.__table__.columns}
        assert "id" in columns

    def test_name_is_unique(self):
        name_col = SemanticCategory.__table__.c.name
        assert name_col.unique is True


class TestSemanticResourceTypeModel:
    """Test SemanticResourceType model."""

    def test_tablename(self):
        assert SemanticResourceType.__tablename__ == "semantic_resource_types"

    def test_creation(self):
        category_id = uuid.uuid4()
        stype = SemanticResourceType(
            category_id=category_id,
            name="VirtualMachine",
            display_name="Virtual Machine",
            description="A virtual compute instance",
            icon="monitor",
            is_abstract=False,
            properties_schema=[{"name": "cpu_count", "data_type": "integer"}],
            allowed_relationship_kinds=["contains", "connects_to"],
            sort_order=1,
        )
        assert stype.name == "VirtualMachine"
        assert stype.category_id == category_id
        assert stype.is_abstract is False
        assert len(stype.properties_schema) == 1
        assert len(stype.allowed_relationship_kinds) == 2

    def test_has_soft_delete(self):
        columns = {col.name for col in SemanticResourceType.__table__.columns}
        assert "deleted_at" in columns

    def test_name_is_unique(self):
        name_col = SemanticResourceType.__table__.c.name
        assert name_col.unique is True

    def test_has_category_fk(self):
        columns = {col.name for col in SemanticResourceType.__table__.columns}
        assert "category_id" in columns

    def test_has_parent_type_fk(self):
        columns = {col.name for col in SemanticResourceType.__table__.columns}
        assert "parent_type_id" in columns

    def test_has_jsonb_columns(self):
        columns = {col.name for col in SemanticResourceType.__table__.columns}
        assert "properties_schema" in columns
        assert "allowed_relationship_kinds" in columns

    def test_not_tenant_scoped(self):
        """Semantic types are system-level, not tenant-scoped."""
        columns = {col.name for col in SemanticResourceType.__table__.columns}
        assert "tenant_id" not in columns


class TestSemanticRelationshipKindModel:
    """Test SemanticRelationshipKind model."""

    def test_tablename(self):
        assert SemanticRelationshipKind.__tablename__ == "semantic_relationship_kinds"

    def test_creation(self):
        kind = SemanticRelationshipKind(
            name="contains",
            display_name="Contains",
            description="Parent contains child",
            inverse_name="contained_by",
        )
        assert kind.name == "contains"
        assert kind.inverse_name == "contained_by"

    def test_name_is_unique(self):
        name_col = SemanticRelationshipKind.__table__.c.name
        assert name_col.unique is True

    def test_has_soft_delete(self):
        columns = {col.name for col in SemanticRelationshipKind.__table__.columns}
        assert "deleted_at" in columns


class TestSemanticProviderModel:
    """Test SemanticProvider model."""

    def test_tablename(self):
        assert SemanticProvider.__tablename__ == "semantic_providers"

    def test_creation(self):
        provider = SemanticProvider(
            name="proxmox",
            display_name="Proxmox VE",
            description="Open-source virtualization platform",
            icon="server",
            provider_type="on_prem",
            website_url="https://www.proxmox.com",
            documentation_url="https://pve.proxmox.com/pve-docs/",
            is_system=True,
        )
        assert provider.name == "proxmox"
        assert provider.display_name == "Proxmox VE"
        assert provider.provider_type == "on_prem"
        assert provider.is_system is True

    def test_has_soft_delete(self):
        columns = {col.name for col in SemanticProvider.__table__.columns}
        assert "deleted_at" in columns

    def test_has_timestamps(self):
        columns = {col.name for col in SemanticProvider.__table__.columns}
        assert "created_at" in columns
        assert "updated_at" in columns

    def test_name_is_unique(self):
        name_col = SemanticProvider.__table__.c.name
        assert name_col.unique is True

    def test_has_expected_columns(self):
        columns = {col.name for col in SemanticProvider.__table__.columns}
        expected = {
            "id", "name", "display_name", "description", "icon",
            "provider_type", "website_url", "documentation_url",
            "is_system", "created_at", "updated_at", "deleted_at",
        }
        assert expected.issubset(columns)

    def test_not_tenant_scoped(self):
        columns = {col.name for col in SemanticProvider.__table__.columns}
        assert "tenant_id" not in columns
