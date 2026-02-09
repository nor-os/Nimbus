"""
Overview: Tests for the semantic mapping engine — resolution strategies, resource mapping,
    unmapped handling, and provider/type lookups.
Architecture: Unit tests for the mapping engine (Section 5)
Dependencies: pytest, app.services.semantic.mapping_engine, app.services.semantic.data_classes
Concepts: Exact match, pattern match, unmapped fallback, provider ↔ type lookups
"""

from app.services.semantic.data_classes import ProviderResource, SemanticResource
from app.services.semantic.mapping_engine import UNMAPPED_TYPE, MappingEngine
from app.services.semantic.registry import (
    CATEGORIES,
    PROVIDERS,
    PROVIDER_RESOURCE_TYPES,
    RELATIONSHIP_KINDS,
    SEMANTIC_TYPES,
    TYPE_MAPPINGS,
    get_category,
    get_provider,
    get_provider_resource_types,
    get_type,
    get_type_mappings_for_provider,
    get_types_by_category,
)


class TestRegistry:
    """Verify the registry has all expected data."""

    def test_seven_categories(self):
        assert len(CATEGORIES) == 7

    def test_category_names(self):
        names = {c.name for c in CATEGORIES}
        assert names == {
            "compute", "network", "storage", "database",
            "security", "monitoring", "application",
        }

    def test_all_types_have_category(self):
        category_names = {c.name for c in CATEGORIES}
        for stype in SEMANTIC_TYPES:
            assert stype.category in category_names, (
                f"Type {stype.name} references unknown category {stype.category}"
            )

    def test_all_types_have_properties(self):
        for stype in SEMANTIC_TYPES:
            assert len(stype.properties) > 0, (
                f"Type {stype.name} has no properties"
            )

    def test_type_count_at_least_30(self):
        assert len(SEMANTIC_TYPES) >= 30

    def test_eight_relationship_kinds(self):
        assert len(RELATIONSHIP_KINDS) == 8

    def test_relationship_inverse_names(self):
        for rel in RELATIONSHIP_KINDS:
            assert rel.inverse_name, f"Relationship {rel.name} has no inverse_name"

    def test_five_providers(self):
        assert len(PROVIDERS) == 5
        provider_names = {p.name for p in PROVIDERS}
        assert provider_names == {"proxmox", "aws", "azure", "gcp", "oci"}

    def test_provider_resource_types_exist(self):
        assert len(PROVIDER_RESOURCE_TYPES) > 0

    def test_type_mappings_exist(self):
        assert len(TYPE_MAPPINGS) > 0

    def test_all_mappings_reference_valid_types(self):
        type_names = {t.name for t in SEMANTIC_TYPES}
        for mapping in TYPE_MAPPINGS:
            assert mapping.semantic_type_name in type_names, (
                f"Mapping {mapping.provider_name}/{mapping.api_type} "
                f"references unknown type {mapping.semantic_type_name}"
            )

    def test_five_providers_covered_in_mappings(self):
        providers = {m.provider_name for m in TYPE_MAPPINGS}
        assert providers == {"proxmox", "aws", "azure", "gcp", "oci"}

    def test_lookup_helpers(self):
        assert get_category("compute") is not None
        assert get_category("nonexistent") is None
        assert get_type("VirtualMachine") is not None
        assert get_type("Nonexistent") is None
        assert len(get_types_by_category("compute")) >= 3

    def test_provider_lookup_helpers(self):
        assert get_provider("aws") is not None
        assert get_provider("nonexistent") is None
        prts = get_provider_resource_types("aws")
        assert len(prts) > 0
        assert all(prt.provider_name == "aws" for prt in prts)
        mappings = get_type_mappings_for_provider("aws")
        assert len(mappings) > 0
        assert all(m.provider_name == "aws" for m in mappings)


class TestMappingEngineResolve:
    """Test MappingEngine.resolve() — type resolution."""

    def setup_method(self):
        self.engine = MappingEngine()

    def test_exact_match_aws_ec2(self):
        result = self.engine.resolve("aws", "ec2:instance")
        assert result is not None
        assert result.name == "VirtualMachine"

    def test_exact_match_case_insensitive(self):
        result = self.engine.resolve("AWS", "EC2:Instance")
        assert result is not None
        assert result.name == "VirtualMachine"

    def test_exact_match_proxmox_qemu(self):
        result = self.engine.resolve("proxmox", "qemu")
        assert result is not None
        assert result.name == "VirtualMachine"

    def test_exact_match_azure_vm(self):
        result = self.engine.resolve("azure", "Microsoft.Compute/virtualMachines")
        assert result is not None
        assert result.name == "VirtualMachine"

    def test_exact_match_gcp_instance(self):
        result = self.engine.resolve("gcp", "compute.googleapis.com/Instance")
        assert result is not None
        assert result.name == "VirtualMachine"

    def test_exact_match_oci_instance(self):
        result = self.engine.resolve("oci", "core/instance")
        assert result is not None
        assert result.name == "VirtualMachine"

    def test_unknown_returns_none(self):
        result = self.engine.resolve("aws", "totally:unknown:thing")
        assert result is None

    def test_unknown_provider_returns_none(self):
        result = self.engine.resolve("linode", "instance")
        assert result is None

    def test_resolve_various_types(self):
        """Test a sampling of types across categories."""
        test_cases = [
            ("aws", "s3:bucket", "ObjectStorage"),
            ("aws", "rds:db", "RelationalDatabase"),
            ("aws", "lambda:function", "ServerlessFunction"),
            ("azure", "Microsoft.Network/virtualNetworks", "VirtualNetwork"),
            ("gcp", "storage.googleapis.com/Bucket", "ObjectStorage"),
            ("proxmox", "lxc", "Container"),
            ("oci", "core/vcn", "VirtualNetwork"),
        ]
        for provider, resource_type, expected_name in test_cases:
            result = self.engine.resolve(provider, resource_type)
            assert result is not None, f"Failed to resolve {provider}/{resource_type}"
            assert result.name == expected_name, (
                f"{provider}/{resource_type}: expected {expected_name}, got {result.name}"
            )


class TestMappingEngineMapResource:
    """Test MappingEngine.map_resource() — full resource conversion."""

    def setup_method(self):
        self.engine = MappingEngine()

    def test_map_known_resource(self):
        resource = ProviderResource(
            provider_name="aws",
            resource_type="ec2:instance",
            resource_id="i-123456",
            name="web-server-01",
            region="us-east-1",
            raw_attributes={
                "cpu_count": 4,
                "memory_gb": 16.0,
                "state": "running",
                "os_type": "linux",
            },
        )
        result = self.engine.map_resource(resource)
        assert result.semantic_type == "VirtualMachine"
        assert result.provider_resource_id == "i-123456"
        assert result.attributes["cpu_count"] == 4
        assert result.attributes["memory_gb"] == 16.0
        assert result.attributes["state"] == "running"

    def test_map_unknown_resource_returns_unmapped(self):
        resource = ProviderResource(
            provider_name="aws",
            resource_type="custom:unknown",
            resource_id="res-999",
            name="mystery",
            raw_attributes={"foo": "bar"},
        )
        result = self.engine.map_resource(resource)
        assert result.semantic_type == UNMAPPED_TYPE
        assert result.attributes == {"foo": "bar"}

    def test_map_resource_preserves_extra_attributes(self):
        resource = ProviderResource(
            provider_name="aws",
            resource_type="ec2:instance",
            resource_id="i-999",
            name="test",
            raw_attributes={
                "cpu_count": 2,
                "state": "stopped",
                "custom_tag": "my-tag",
            },
        )
        result = self.engine.map_resource(resource)
        assert result.semantic_type == "VirtualMachine"
        # Extra attributes go under _extra key
        assert "_extra" in result.attributes
        assert result.attributes["_extra"]["custom_tag"] == "my-tag"


class TestMappingEngineLookups:
    """Test MappingEngine provider/type lookup methods."""

    def setup_method(self):
        self.engine = MappingEngine()

    def test_get_mappings_for_provider(self):
        aws_mappings = self.engine.get_mappings_for_provider("aws")
        assert len(aws_mappings) > 0
        assert all(m.provider_name == "aws" for m in aws_mappings)

    def test_get_mappings_for_nonexistent_provider(self):
        mappings = self.engine.get_mappings_for_provider("linode")
        assert len(mappings) == 0

    def test_get_provider_resource_types(self):
        aws_prts = self.engine.get_provider_resource_types("aws")
        assert len(aws_prts) > 0
        assert all(prt.provider_name == "aws" for prt in aws_prts)

    def test_get_provider_resource_types_nonexistent(self):
        prts = self.engine.get_provider_resource_types("linode")
        assert len(prts) == 0
