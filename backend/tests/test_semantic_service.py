"""
Overview: Tests for semantic layer service — verifies query construction, registry completeness,
    and schema/enum consistency.
Architecture: Unit tests for semantic service layer (Section 5)
Dependencies: pytest, app.services.semantic, app.schemas.semantic, app.models.semantic_type
Concepts: Service instantiation, registry-schema alignment, Pydantic validation
"""

import uuid
from datetime import UTC, datetime

from app.models.semantic_type import (
    SemanticCategory,
    SemanticProvider,
    SemanticProviderResourceType,
    SemanticRelationshipKind,
    SemanticResourceType,
    SemanticTypeMapping,
)
from app.schemas.semantic import (
    ProviderResourceTypeStatusEnum,
    ProviderTypeEnum,
    SemanticCategoryResponse,
    SemanticProviderResourceTypeResponse,
    SemanticProviderResponse,
    SemanticRelationshipKindResponse,
    SemanticResourceTypeListResponse,
    SemanticResourceTypeResponse,
    SemanticTypeFilter,
    SemanticTypeMappingResponse,
)
from app.services.semantic.registry import (
    CATEGORIES,
    PROVIDER_RESOURCE_TYPES,
    PROVIDERS,
    RELATIONSHIP_KINDS,
    SEMANTIC_TYPES,
    TYPE_MAPPINGS,
    PropertyDataType,
)


class TestProviderTypeEnum:
    """Test ProviderTypeEnum Pydantic schema."""

    def test_values(self):
        assert set(ProviderTypeEnum) == {
            ProviderTypeEnum.CLOUD,
            ProviderTypeEnum.ON_PREM,
            ProviderTypeEnum.SAAS,
            ProviderTypeEnum.CUSTOM,
        }

    def test_is_str_enum(self):
        assert isinstance(ProviderTypeEnum.CLOUD, str)
        assert ProviderTypeEnum.CLOUD == "cloud"


class TestProviderResourceTypeStatusEnum:
    """Test ProviderResourceTypeStatusEnum Pydantic schema."""

    def test_values(self):
        assert set(ProviderResourceTypeStatusEnum) == {
            ProviderResourceTypeStatusEnum.AVAILABLE,
            ProviderResourceTypeStatusEnum.PREVIEW,
            ProviderResourceTypeStatusEnum.DEPRECATED,
        }

    def test_is_str_enum(self):
        assert isinstance(ProviderResourceTypeStatusEnum.AVAILABLE, str)
        assert ProviderResourceTypeStatusEnum.AVAILABLE == "available"


class TestPropertyDataType:
    """Test PropertyDataType enum from registry."""

    def test_values(self):
        assert set(PropertyDataType) == {
            PropertyDataType.STRING,
            PropertyDataType.INTEGER,
            PropertyDataType.FLOAT,
            PropertyDataType.BOOLEAN,
            PropertyDataType.JSON,
        }

    def test_all_types_use_valid_property_types(self):
        valid = {e.value for e in PropertyDataType}
        for stype in SEMANTIC_TYPES:
            for prop in stype.properties:
                assert prop.data_type in valid, (
                    f"Type {stype.name} property {prop.name} uses "
                    f"invalid data_type {prop.data_type}"
                )


class TestPydanticSchemas:
    """Test Pydantic schema validation."""

    def test_category_response_from_attributes(self):
        now = datetime.now(UTC)
        cat = SemanticCategory(
            id=uuid.uuid4(),
            name="compute",
            display_name="Compute",
            description="Test",
            icon="server",
            sort_order=1,
            is_system=False,
        )
        cat.created_at = now
        cat.updated_at = now
        resp = SemanticCategoryResponse.model_validate(cat)
        assert resp.name == "compute"
        assert resp.display_name == "Compute"

    def test_type_response_from_attributes(self):
        now = datetime.now(UTC)
        stype = SemanticResourceType(
            id=uuid.uuid4(),
            category_id=uuid.uuid4(),
            name="VirtualMachine",
            display_name="Virtual Machine",
            description="Test VM",
            icon="monitor",
            is_abstract=False,
            is_system=False,
            properties_schema=[{"name": "cpu_count", "data_type": "integer"}],
            allowed_relationship_kinds=["contains"],
            sort_order=1,
        )
        stype.created_at = now
        stype.updated_at = now
        resp = SemanticResourceTypeResponse.model_validate(stype)
        assert resp.name == "VirtualMachine"
        assert resp.is_abstract is False
        assert len(resp.properties_schema) == 1

    def test_relationship_kind_response(self):
        now = datetime.now(UTC)
        kind = SemanticRelationshipKind(
            id=uuid.uuid4(),
            name="contains",
            display_name="Contains",
            description="Parent contains child",
            inverse_name="contained_by",
            is_system=False,
        )
        kind.created_at = now
        kind.updated_at = now
        resp = SemanticRelationshipKindResponse.model_validate(kind)
        assert resp.name == "contains"
        assert resp.inverse_name == "contained_by"

    def test_provider_response(self):
        now = datetime.now(UTC)
        provider = SemanticProvider(
            id=uuid.uuid4(),
            name="aws",
            display_name="Amazon Web Services",
            description="AWS cloud platform",
            icon="cloud",
            provider_type="cloud",
            website_url="https://aws.amazon.com",
            documentation_url="https://docs.aws.amazon.com",
            is_system=True,
        )
        provider.created_at = now
        provider.updated_at = now
        resp = SemanticProviderResponse.model_validate(provider)
        assert resp.name == "aws"
        assert resp.provider_type == ProviderTypeEnum.CLOUD

    def test_provider_resource_type_response(self):
        now = datetime.now(UTC)
        prt = SemanticProviderResourceType(
            id=uuid.uuid4(),
            provider_id=uuid.uuid4(),
            api_type="ec2:instance",
            display_name="EC2 Instance",
            description="AWS compute instance",
            status="available",
            is_system=True,
        )
        prt.created_at = now
        prt.updated_at = now
        resp = SemanticProviderResourceTypeResponse.model_validate(prt)
        assert resp.api_type == "ec2:instance"
        assert resp.status == ProviderResourceTypeStatusEnum.AVAILABLE

    def test_type_mapping_response(self):
        now = datetime.now(UTC)
        mapping = SemanticTypeMapping(
            id=uuid.uuid4(),
            provider_resource_type_id=uuid.uuid4(),
            semantic_type_id=uuid.uuid4(),
            parameter_mapping={"vcpus": "cores"},
            notes="Test mapping",
            is_system=True,
        )
        mapping.created_at = now
        mapping.updated_at = now
        resp = SemanticTypeMappingResponse.model_validate(mapping)
        assert resp.parameter_mapping == {"vcpus": "cores"}
        assert resp.notes == "Test mapping"

    def test_list_response(self):
        resp = SemanticResourceTypeListResponse(items=[], total=0)
        assert resp.total == 0
        assert resp.items == []

    def test_type_filter(self):
        f = SemanticTypeFilter(category="compute", is_abstract=False, search="vm")
        assert f.category == "compute"
        assert f.is_abstract is False
        assert f.search == "vm"

    def test_type_filter_defaults(self):
        f = SemanticTypeFilter()
        assert f.category is None
        assert f.is_abstract is None
        assert f.search is None


class TestRegistryCompleteness:
    """Cross-check registry data for consistency."""

    def test_all_categories_have_types(self):
        """Every category should have at least one type."""
        category_names = {c.name for c in CATEGORIES}
        categories_with_types = {t.category for t in SEMANTIC_TYPES}
        for cat_name in category_names:
            assert cat_name in categories_with_types, (
                f"Category {cat_name} has no types"
            )

    def test_all_types_have_unique_names(self):
        names = [t.name for t in SEMANTIC_TYPES]
        assert len(names) == len(set(names)), "Duplicate type names found"

    def test_all_categories_have_unique_names(self):
        names = [c.name for c in CATEGORIES]
        assert len(names) == len(set(names)), "Duplicate category names found"

    def test_all_relationship_kinds_have_unique_names(self):
        names = [r.name for r in RELATIONSHIP_KINDS]
        assert len(names) == len(set(names)), "Duplicate relationship kind names found"

    def test_providers_have_unique_names(self):
        names = [p.name for p in PROVIDERS]
        assert len(names) == len(set(names)), "Duplicate provider names found"

    def test_provider_resource_types_have_unique_keys(self):
        keys = [(prt.provider_name, prt.api_type) for prt in PROVIDER_RESOURCE_TYPES]
        assert len(keys) == len(set(keys)), "Duplicate provider resource type keys found"

    def test_type_mappings_have_unique_keys(self):
        keys = [(m.provider_name, m.api_type) for m in TYPE_MAPPINGS]
        assert len(keys) == len(set(keys)), "Duplicate type mapping keys found"

    def test_all_type_mappings_reference_valid_types(self):
        type_names = {t.name for t in SEMANTIC_TYPES}
        for mapping in TYPE_MAPPINGS:
            assert mapping.semantic_type_name in type_names, (
                f"Mapping {mapping.provider_name}/{mapping.api_type} "
                f"references unknown type {mapping.semantic_type_name}"
            )

    def test_all_type_mappings_reference_valid_prts(self):
        prt_keys = {(prt.provider_name, prt.api_type) for prt in PROVIDER_RESOURCE_TYPES}
        for mapping in TYPE_MAPPINGS:
            assert (mapping.provider_name, mapping.api_type) in prt_keys, (
                f"Mapping {mapping.provider_name}/{mapping.api_type} "
                f"references unknown provider resource type"
            )

    def test_all_prts_reference_valid_providers(self):
        provider_names = {p.name for p in PROVIDERS}
        for prt in PROVIDER_RESOURCE_TYPES:
            assert prt.provider_name in provider_names, (
                f"PRT {prt.provider_name}/{prt.api_type} references unknown provider"
            )

    def test_categories_have_sort_order(self):
        for cat in CATEGORIES:
            assert cat.sort_order > 0, f"Category {cat.name} has no sort_order"

    def test_types_have_display_names(self):
        for stype in SEMANTIC_TYPES:
            assert stype.display_name, f"Type {stype.name} has no display_name"

    def test_five_providers(self):
        provider_names = {p.name for p in PROVIDERS}
        assert provider_names == {"proxmox", "aws", "azure", "gcp", "oci"}

    def test_five_providers_covered_in_mappings(self):
        providers = {m.provider_name for m in TYPE_MAPPINGS}
        assert providers == {"proxmox", "aws", "azure", "gcp", "oci"}
