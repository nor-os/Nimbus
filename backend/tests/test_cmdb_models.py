"""
Overview: Tests for CMDB data models — table names, columns, soft deletes, relationships,
    and unique constraints for all Configuration Management Database entities.
Architecture: Unit tests for CMDB data layer (Section 8)
Dependencies: pytest, app.models.cmdb
Concepts: Model validation, table schema verification, relationship integrity, pricing,
    snapshots, versioning, service catalog
"""

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal

from app.models.cmdb import (
    CIAttributeDefinition,
    CIClass,
    CIRelationship,
    CISnapshot,
    CITemplate,
    ConfigurationItem,
    PriceList,
    PriceListItem,
    RelationshipType,
    SavedSearch,
    ServiceOffering,
    TenantPriceOverride,
)


class TestConfigurationItemModel:
    """Test ConfigurationItem model."""

    def test_tablename(self):
        assert ConfigurationItem.__tablename__ == "configuration_items"

    def test_creation(self):
        tenant_id = uuid.uuid4()
        ci_class_id = uuid.uuid4()
        compartment_id = uuid.uuid4()
        ci = ConfigurationItem(
            tenant_id=tenant_id,
            ci_class_id=ci_class_id,
            compartment_id=compartment_id,
            name="web-server-01",
            description="Production web server",
            lifecycle_state="active",
            attributes={"cpu": 4, "memory_gb": 16},
            tags={"env": "prod", "app": "web"},
            cloud_resource_id="i-0123456789abcdef0",
            pulumi_urn="urn:pulumi:prod::infra::aws:ec2/instance:Instance::web-01",
        )
        assert ci.tenant_id == tenant_id
        assert ci.ci_class_id == ci_class_id
        assert ci.compartment_id == compartment_id
        assert ci.name == "web-server-01"
        assert ci.description == "Production web server"
        assert ci.lifecycle_state == "active"
        assert ci.attributes["cpu"] == 4
        assert ci.tags["env"] == "prod"
        assert ci.cloud_resource_id == "i-0123456789abcdef0"
        assert "pulumi" in ci.pulumi_urn

    def test_has_soft_delete(self):
        columns = {col.name for col in ConfigurationItem.__table__.columns}
        assert "deleted_at" in columns

    def test_has_timestamps(self):
        columns = {col.name for col in ConfigurationItem.__table__.columns}
        assert "created_at" in columns
        assert "updated_at" in columns

    def test_has_id(self):
        columns = {col.name for col in ConfigurationItem.__table__.columns}
        assert "id" in columns

    def test_has_tenant_fk(self):
        columns = {col.name for col in ConfigurationItem.__table__.columns}
        assert "tenant_id" in columns

    def test_has_foreign_keys(self):
        columns = {col.name for col in ConfigurationItem.__table__.columns}
        assert "ci_class_id" in columns
        assert "compartment_id" in columns

    def test_has_expected_columns(self):
        columns = {col.name for col in ConfigurationItem.__table__.columns}
        expected = {
            "id",
            "tenant_id",
            "ci_class_id",
            "compartment_id",
            "name",
            "description",
            "lifecycle_state",
            "attributes",
            "tags",
            "cloud_resource_id",
            "pulumi_urn",
            "created_at",
            "updated_at",
            "deleted_at",
        }
        assert expected.issubset(columns)

    def test_lifecycle_state_default(self):
        lifecycle_col = ConfigurationItem.__table__.c.lifecycle_state
        assert lifecycle_col.server_default is not None


class TestCIClassModel:
    """Test CIClass model."""

    def test_tablename(self):
        assert CIClass.__tablename__ == "ci_classes"

    def test_creation(self):
        tenant_id = uuid.uuid4()
        parent_id = uuid.uuid4()
        semantic_type_id = uuid.uuid4()
        ci_class = CIClass(
            tenant_id=tenant_id,
            name="VirtualMachine",
            display_name="Virtual Machine",
            parent_class_id=parent_id,
            semantic_type_id=semantic_type_id,
            schema={"properties": {"cpu_count": {"type": "integer"}}},
            icon="server",
            is_system=True,
            is_active=True,
        )
        assert ci_class.tenant_id == tenant_id
        assert ci_class.name == "VirtualMachine"
        assert ci_class.display_name == "Virtual Machine"
        assert ci_class.parent_class_id == parent_id
        assert ci_class.semantic_type_id == semantic_type_id
        assert ci_class.schema["properties"]["cpu_count"]["type"] == "integer"
        assert ci_class.icon == "server"
        assert ci_class.is_system is True
        assert ci_class.is_active is True

    def test_has_soft_delete(self):
        columns = {col.name for col in CIClass.__table__.columns}
        assert "deleted_at" in columns

    def test_has_timestamps(self):
        columns = {col.name for col in CIClass.__table__.columns}
        assert "created_at" in columns
        assert "updated_at" in columns

    def test_has_id(self):
        columns = {col.name for col in CIClass.__table__.columns}
        assert "id" in columns

    def test_tenant_id_is_nullable(self):
        """CIClass tenant_id is nullable (system classes)."""
        tenant_col = CIClass.__table__.c.tenant_id
        assert tenant_col.nullable is True

    def test_has_foreign_keys(self):
        columns = {col.name for col in CIClass.__table__.columns}
        assert "parent_class_id" in columns
        assert "semantic_type_id" in columns

    def test_has_unique_constraint(self):
        """Verify (tenant_id, name) unique constraint exists."""
        constraints = CIClass.__table__.constraints
        unique_constraints = [c for c in constraints if hasattr(c, "columns")]
        constraint_names = {c.name for c in unique_constraints}
        assert "uq_ci_class_tenant_name" in constraint_names

    def test_has_expected_columns(self):
        columns = {col.name for col in CIClass.__table__.columns}
        expected = {
            "id",
            "tenant_id",
            "name",
            "display_name",
            "parent_class_id",
            "semantic_type_id",
            "schema",
            "icon",
            "is_system",
            "is_active",
            "created_at",
            "updated_at",
            "deleted_at",
        }
        assert expected.issubset(columns)


class TestCIAttributeDefinitionModel:
    """Test CIAttributeDefinition model."""

    def test_tablename(self):
        assert CIAttributeDefinition.__tablename__ == "ci_attribute_definitions"

    def test_creation(self):
        ci_class_id = uuid.uuid4()
        attr_def = CIAttributeDefinition(
            ci_class_id=ci_class_id,
            name="cpu_count",
            display_name="CPU Count",
            data_type="integer",
            is_required=True,
            default_value={"value": 2},
            validation_rules={"min": 1, "max": 128},
            sort_order=10,
        )
        assert attr_def.ci_class_id == ci_class_id
        assert attr_def.name == "cpu_count"
        assert attr_def.display_name == "CPU Count"
        assert attr_def.data_type == "integer"
        assert attr_def.is_required is True
        assert attr_def.default_value["value"] == 2
        assert attr_def.validation_rules["min"] == 1
        assert attr_def.sort_order == 10

    def test_has_soft_delete(self):
        columns = {col.name for col in CIAttributeDefinition.__table__.columns}
        assert "deleted_at" in columns

    def test_has_timestamps(self):
        columns = {col.name for col in CIAttributeDefinition.__table__.columns}
        assert "created_at" in columns
        assert "updated_at" in columns

    def test_has_id(self):
        columns = {col.name for col in CIAttributeDefinition.__table__.columns}
        assert "id" in columns

    def test_has_ci_class_fk(self):
        columns = {col.name for col in CIAttributeDefinition.__table__.columns}
        assert "ci_class_id" in columns

    def test_has_unique_constraint(self):
        """Verify (ci_class_id, name) unique constraint exists."""
        constraints = CIAttributeDefinition.__table__.constraints
        unique_constraints = [c for c in constraints if hasattr(c, "columns")]
        constraint_names = {c.name for c in unique_constraints}
        assert "uq_ci_attr_def_class_name" in constraint_names

    def test_has_expected_columns(self):
        columns = {col.name for col in CIAttributeDefinition.__table__.columns}
        expected = {
            "id",
            "ci_class_id",
            "name",
            "display_name",
            "data_type",
            "is_required",
            "default_value",
            "validation_rules",
            "sort_order",
            "created_at",
            "updated_at",
            "deleted_at",
        }
        assert expected.issubset(columns)


class TestCIRelationshipModel:
    """Test CIRelationship model."""

    def test_tablename(self):
        assert CIRelationship.__tablename__ == "ci_relationships"

    def test_creation(self):
        tenant_id = uuid.uuid4()
        source_id = uuid.uuid4()
        target_id = uuid.uuid4()
        rel_type_id = uuid.uuid4()
        rel = CIRelationship(
            tenant_id=tenant_id,
            source_ci_id=source_id,
            target_ci_id=target_id,
            relationship_type_id=rel_type_id,
            attributes={"bandwidth": "10Gbps"},
        )
        assert rel.tenant_id == tenant_id
        assert rel.source_ci_id == source_id
        assert rel.target_ci_id == target_id
        assert rel.relationship_type_id == rel_type_id
        assert rel.attributes["bandwidth"] == "10Gbps"

    def test_has_soft_delete(self):
        columns = {col.name for col in CIRelationship.__table__.columns}
        assert "deleted_at" in columns

    def test_has_timestamps(self):
        columns = {col.name for col in CIRelationship.__table__.columns}
        assert "created_at" in columns
        assert "updated_at" in columns

    def test_has_id(self):
        columns = {col.name for col in CIRelationship.__table__.columns}
        assert "id" in columns

    def test_has_foreign_keys(self):
        columns = {col.name for col in CIRelationship.__table__.columns}
        assert "tenant_id" in columns
        assert "source_ci_id" in columns
        assert "target_ci_id" in columns
        assert "relationship_type_id" in columns

    def test_has_unique_constraint(self):
        """Verify (source_ci_id, target_ci_id, relationship_type_id) unique constraint exists."""
        constraints = CIRelationship.__table__.constraints
        unique_constraints = [c for c in constraints if hasattr(c, "columns")]
        constraint_names = {c.name for c in unique_constraints}
        assert "uq_ci_relationship_src_tgt_type" in constraint_names

    def test_has_check_constraint(self):
        """Verify source_ci_id != target_ci_id check constraint exists."""
        constraints = CIRelationship.__table__.constraints
        check_constraints = [
            c for c in constraints if c.__class__.__name__ == "CheckConstraint"
        ]
        constraint_names = {c.name for c in check_constraints}
        assert "ck_ci_relationship_no_self_ref" in constraint_names

    def test_has_expected_columns(self):
        columns = {col.name for col in CIRelationship.__table__.columns}
        expected = {
            "id",
            "tenant_id",
            "source_ci_id",
            "target_ci_id",
            "relationship_type_id",
            "attributes",
            "created_at",
            "updated_at",
            "deleted_at",
        }
        assert expected.issubset(columns)


class TestRelationshipTypeModel:
    """Test RelationshipType model."""

    def test_tablename(self):
        assert RelationshipType.__tablename__ == "relationship_types"

    def test_creation(self):
        rel_type = RelationshipType(
            name="contains",
            display_name="Contains",
            inverse_name="contained_by",
            description="Parent contains child",
            source_class_ids=["vm-class-id", "container-class-id"],
            target_class_ids=["disk-class-id", "nic-class-id"],
            is_system=True,
        )
        assert rel_type.name == "contains"
        assert rel_type.display_name == "Contains"
        assert rel_type.inverse_name == "contained_by"
        assert rel_type.description == "Parent contains child"
        assert len(rel_type.source_class_ids) == 2
        assert len(rel_type.target_class_ids) == 2
        assert rel_type.is_system is True

    def test_has_soft_delete(self):
        columns = {col.name for col in RelationshipType.__table__.columns}
        assert "deleted_at" in columns

    def test_has_timestamps(self):
        columns = {col.name for col in RelationshipType.__table__.columns}
        assert "created_at" in columns
        assert "updated_at" in columns

    def test_has_id(self):
        columns = {col.name for col in RelationshipType.__table__.columns}
        assert "id" in columns

    def test_name_is_unique(self):
        name_col = RelationshipType.__table__.c.name
        assert name_col.unique is True

    def test_not_tenant_scoped(self):
        """RelationshipType is not tenant-scoped."""
        columns = {col.name for col in RelationshipType.__table__.columns}
        assert "tenant_id" not in columns

    def test_has_expected_columns(self):
        columns = {col.name for col in RelationshipType.__table__.columns}
        expected = {
            "id",
            "name",
            "display_name",
            "inverse_name",
            "description",
            "source_class_ids",
            "target_class_ids",
            "is_system",
            "created_at",
            "updated_at",
            "deleted_at",
        }
        assert expected.issubset(columns)


class TestCISnapshotModel:
    """Test CISnapshot model."""

    def test_tablename(self):
        assert CISnapshot.__tablename__ == "ci_snapshots"

    def test_creation(self):
        ci_id = uuid.uuid4()
        tenant_id = uuid.uuid4()
        user_id = uuid.uuid4()
        snapshot = CISnapshot(
            ci_id=ci_id,
            tenant_id=tenant_id,
            version_number=5,
            snapshot_data={
                "name": "web-server-01",
                "attributes": {"cpu": 4},
                "lifecycle_state": "active",
            },
            changed_by=user_id,
            changed_at=datetime.now(UTC),
            change_reason="Increased CPU count",
            change_type="update",
        )
        assert snapshot.ci_id == ci_id
        assert snapshot.tenant_id == tenant_id
        assert snapshot.version_number == 5
        assert snapshot.snapshot_data["name"] == "web-server-01"
        assert snapshot.changed_by == user_id
        assert snapshot.change_reason == "Increased CPU count"
        assert snapshot.change_type == "update"

    def test_no_soft_delete(self):
        """CISnapshot is immutable and does NOT have soft delete."""
        columns = {col.name for col in CISnapshot.__table__.columns}
        assert "deleted_at" not in columns

    def test_no_timestamps(self):
        """CISnapshot uses changed_at instead of created_at/updated_at."""
        columns = {col.name for col in CISnapshot.__table__.columns}
        assert "created_at" not in columns
        assert "updated_at" not in columns
        assert "changed_at" in columns

    def test_has_id(self):
        columns = {col.name for col in CISnapshot.__table__.columns}
        assert "id" in columns

    def test_has_foreign_keys(self):
        columns = {col.name for col in CISnapshot.__table__.columns}
        assert "ci_id" in columns
        assert "tenant_id" in columns
        assert "changed_by" in columns

    def test_has_unique_constraint(self):
        """Verify (ci_id, version_number) unique constraint exists."""
        constraints = CISnapshot.__table__.constraints
        unique_constraints = [c for c in constraints if hasattr(c, "columns")]
        constraint_names = {c.name for c in unique_constraints}
        assert "uq_ci_snapshot_ci_version" in constraint_names

    def test_has_expected_columns(self):
        columns = {col.name for col in CISnapshot.__table__.columns}
        expected = {
            "id",
            "ci_id",
            "tenant_id",
            "version_number",
            "snapshot_data",
            "changed_by",
            "changed_at",
            "change_reason",
            "change_type",
        }
        assert expected.issubset(columns)


class TestCITemplateModel:
    """Test CITemplate model."""

    def test_tablename(self):
        assert CITemplate.__tablename__ == "ci_templates"

    def test_creation(self):
        tenant_id = uuid.uuid4()
        ci_class_id = uuid.uuid4()
        template = CITemplate(
            tenant_id=tenant_id,
            name="Standard Web Server",
            description="Template for standard web server configuration",
            ci_class_id=ci_class_id,
            attributes={"cpu": 4, "memory_gb": 16},
            tags={"template": "web"},
            relationship_templates={"connects_to": ["db-template"]},
            constraints={"required_compartment": "prod"},
            is_active=True,
            version=2,
        )
        assert template.tenant_id == tenant_id
        assert template.name == "Standard Web Server"
        assert template.description == "Template for standard web server configuration"
        assert template.ci_class_id == ci_class_id
        assert template.attributes["cpu"] == 4
        assert template.tags["template"] == "web"
        assert template.relationship_templates["connects_to"][0] == "db-template"
        assert template.constraints["required_compartment"] == "prod"
        assert template.is_active is True
        assert template.version == 2

    def test_has_soft_delete(self):
        columns = {col.name for col in CITemplate.__table__.columns}
        assert "deleted_at" in columns

    def test_has_timestamps(self):
        columns = {col.name for col in CITemplate.__table__.columns}
        assert "created_at" in columns
        assert "updated_at" in columns

    def test_has_id(self):
        columns = {col.name for col in CITemplate.__table__.columns}
        assert "id" in columns

    def test_has_foreign_keys(self):
        columns = {col.name for col in CITemplate.__table__.columns}
        assert "tenant_id" in columns
        assert "ci_class_id" in columns

    def test_has_expected_columns(self):
        columns = {col.name for col in CITemplate.__table__.columns}
        expected = {
            "id",
            "tenant_id",
            "name",
            "description",
            "ci_class_id",
            "attributes",
            "tags",
            "relationship_templates",
            "constraints",
            "is_active",
            "version",
            "created_at",
            "updated_at",
            "deleted_at",
        }
        assert expected.issubset(columns)


class TestServiceOfferingModel:
    """Test ServiceOffering model."""

    def test_tablename(self):
        assert ServiceOffering.__tablename__ == "service_offerings"

    def test_creation(self):
        tenant_id = uuid.uuid4()
        ci_class_id = uuid.uuid4()
        offering = ServiceOffering(
            tenant_id=tenant_id,
            name="VM - Small",
            description="Small virtual machine",
            category="compute",
            measuring_unit="hour",
            ci_class_id=ci_class_id,
            is_active=True,
        )
        assert offering.tenant_id == tenant_id
        assert offering.name == "VM - Small"
        assert offering.description == "Small virtual machine"
        assert offering.category == "compute"
        assert offering.measuring_unit == "hour"
        assert offering.ci_class_id == ci_class_id
        assert offering.is_active is True

    def test_has_soft_delete(self):
        columns = {col.name for col in ServiceOffering.__table__.columns}
        assert "deleted_at" in columns

    def test_has_timestamps(self):
        columns = {col.name for col in ServiceOffering.__table__.columns}
        assert "created_at" in columns
        assert "updated_at" in columns

    def test_has_id(self):
        columns = {col.name for col in ServiceOffering.__table__.columns}
        assert "id" in columns

    def test_has_foreign_keys(self):
        columns = {col.name for col in ServiceOffering.__table__.columns}
        assert "tenant_id" in columns
        assert "ci_class_id" in columns

    def test_ci_class_id_is_nullable(self):
        """ServiceOffering ci_class_id is nullable."""
        ci_class_col = ServiceOffering.__table__.c.ci_class_id
        assert ci_class_col.nullable is True

    def test_has_expected_columns(self):
        columns = {col.name for col in ServiceOffering.__table__.columns}
        expected = {
            "id",
            "tenant_id",
            "name",
            "description",
            "category",
            "measuring_unit",
            "ci_class_id",
            "is_active",
            "created_at",
            "updated_at",
            "deleted_at",
        }
        assert expected.issubset(columns)


class TestPriceListModel:
    """Test PriceList model."""

    def test_tablename(self):
        assert PriceList.__tablename__ == "price_lists"

    def test_creation(self):
        tenant_id = uuid.uuid4()
        price_list = PriceList(
            tenant_id=tenant_id,
            name="Standard Pricing 2026",
            is_default=True,
            effective_from=date(2026, 1, 1),
            effective_to=date(2026, 12, 31),
        )
        assert price_list.tenant_id == tenant_id
        assert price_list.name == "Standard Pricing 2026"
        assert price_list.is_default is True
        assert price_list.effective_from == date(2026, 1, 1)
        assert price_list.effective_to == date(2026, 12, 31)

    def test_has_soft_delete(self):
        columns = {col.name for col in PriceList.__table__.columns}
        assert "deleted_at" in columns

    def test_has_timestamps(self):
        columns = {col.name for col in PriceList.__table__.columns}
        assert "created_at" in columns
        assert "updated_at" in columns

    def test_has_id(self):
        columns = {col.name for col in PriceList.__table__.columns}
        assert "id" in columns

    def test_tenant_id_is_nullable(self):
        """PriceList tenant_id is nullable (global price lists)."""
        tenant_col = PriceList.__table__.c.tenant_id
        assert tenant_col.nullable is True

    def test_has_expected_columns(self):
        columns = {col.name for col in PriceList.__table__.columns}
        expected = {
            "id",
            "tenant_id",
            "name",
            "is_default",
            "effective_from",
            "effective_to",
            "created_at",
            "updated_at",
            "deleted_at",
        }
        assert expected.issubset(columns)


class TestPriceListItemModel:
    """Test PriceListItem model."""

    def test_tablename(self):
        assert PriceListItem.__tablename__ == "price_list_items"

    def test_creation(self):
        price_list_id = uuid.uuid4()
        service_offering_id = uuid.uuid4()
        item = PriceListItem(
            price_list_id=price_list_id,
            service_offering_id=service_offering_id,
            price_per_unit=Decimal("49.95"),
            currency="USD",
            min_quantity=Decimal("1"),
            max_quantity=Decimal("100"),
        )
        assert item.price_list_id == price_list_id
        assert item.service_offering_id == service_offering_id
        assert item.price_per_unit == Decimal("49.95")
        assert item.currency == "USD"
        assert item.min_quantity == Decimal("1")
        assert item.max_quantity == Decimal("100")

    def test_has_soft_delete(self):
        columns = {col.name for col in PriceListItem.__table__.columns}
        assert "deleted_at" in columns

    def test_has_timestamps(self):
        columns = {col.name for col in PriceListItem.__table__.columns}
        assert "created_at" in columns
        assert "updated_at" in columns

    def test_has_id(self):
        columns = {col.name for col in PriceListItem.__table__.columns}
        assert "id" in columns

    def test_has_foreign_keys(self):
        columns = {col.name for col in PriceListItem.__table__.columns}
        assert "price_list_id" in columns
        assert "service_offering_id" in columns

    def test_has_expected_columns(self):
        columns = {col.name for col in PriceListItem.__table__.columns}
        expected = {
            "id",
            "price_list_id",
            "service_offering_id",
            "price_per_unit",
            "currency",
            "min_quantity",
            "max_quantity",
            "created_at",
            "updated_at",
            "deleted_at",
        }
        assert expected.issubset(columns)


class TestTenantPriceOverrideModel:
    """Test TenantPriceOverride model."""

    def test_tablename(self):
        assert TenantPriceOverride.__tablename__ == "tenant_price_overrides"

    def test_creation(self):
        tenant_id = uuid.uuid4()
        service_offering_id = uuid.uuid4()
        override = TenantPriceOverride(
            tenant_id=tenant_id,
            service_offering_id=service_offering_id,
            price_per_unit=Decimal("39.95"),
            discount_percent=Decimal("20.00"),
            effective_from=date(2026, 1, 1),
            effective_to=date(2026, 6, 30),
        )
        assert override.tenant_id == tenant_id
        assert override.service_offering_id == service_offering_id
        assert override.price_per_unit == Decimal("39.95")
        assert override.discount_percent == Decimal("20.00")
        assert override.effective_from == date(2026, 1, 1)
        assert override.effective_to == date(2026, 6, 30)

    def test_has_soft_delete(self):
        columns = {col.name for col in TenantPriceOverride.__table__.columns}
        assert "deleted_at" in columns

    def test_has_timestamps(self):
        columns = {col.name for col in TenantPriceOverride.__table__.columns}
        assert "created_at" in columns
        assert "updated_at" in columns

    def test_has_id(self):
        columns = {col.name for col in TenantPriceOverride.__table__.columns}
        assert "id" in columns

    def test_has_foreign_keys(self):
        columns = {col.name for col in TenantPriceOverride.__table__.columns}
        assert "tenant_id" in columns
        assert "service_offering_id" in columns

    def test_has_expected_columns(self):
        columns = {col.name for col in TenantPriceOverride.__table__.columns}
        expected = {
            "id",
            "tenant_id",
            "service_offering_id",
            "price_per_unit",
            "discount_percent",
            "effective_from",
            "effective_to",
            "created_at",
            "updated_at",
            "deleted_at",
        }
        assert expected.issubset(columns)


class TestSavedSearchModel:
    """Test SavedSearch model."""

    def test_tablename(self):
        assert SavedSearch.__tablename__ == "saved_searches"

    def test_creation(self):
        tenant_id = uuid.uuid4()
        user_id = uuid.uuid4()
        search = SavedSearch(
            tenant_id=tenant_id,
            user_id=user_id,
            name="Production VMs",
            query_text="lifecycle_state:active",
            filters={"tags.env": "prod", "ci_class_name": "VirtualMachine"},
            sort_config={"field": "name", "direction": "asc"},
            is_default=True,
        )
        assert search.tenant_id == tenant_id
        assert search.user_id == user_id
        assert search.name == "Production VMs"
        assert search.query_text == "lifecycle_state:active"
        assert search.filters["tags.env"] == "prod"
        assert search.sort_config["field"] == "name"
        assert search.is_default is True

    def test_has_soft_delete(self):
        columns = {col.name for col in SavedSearch.__table__.columns}
        assert "deleted_at" in columns

    def test_has_timestamps(self):
        columns = {col.name for col in SavedSearch.__table__.columns}
        assert "created_at" in columns
        assert "updated_at" in columns

    def test_has_id(self):
        columns = {col.name for col in SavedSearch.__table__.columns}
        assert "id" in columns

    def test_has_foreign_keys(self):
        columns = {col.name for col in SavedSearch.__table__.columns}
        assert "tenant_id" in columns
        assert "user_id" in columns

    def test_has_expected_columns(self):
        columns = {col.name for col in SavedSearch.__table__.columns}
        expected = {
            "id",
            "tenant_id",
            "user_id",
            "name",
            "query_text",
            "filters",
            "sort_config",
            "is_default",
            "created_at",
            "updated_at",
            "deleted_at",
        }
        assert expected.issubset(columns)
