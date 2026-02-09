"""
Overview: Test suite for CMDB GraphQL integration — validates type definitions and schema.
Architecture: Test coverage for GraphQL type definitions and schema validation (Section 8)
Dependencies: pytest, app.api.graphql.types.cmdb, app.api.graphql.types.catalog
Concepts: GraphQL type definitions, schema validation, Strawberry type introspection.
"""

from app.api.graphql.types.catalog import (
    PriceListItemType,
    ServiceOfferingListType,
    ServiceOfferingType,
)
from app.api.graphql.types.cmdb import CIClassType, LifecycleStateGQL, MeasuringUnitGQL


class TestCMDBGraphQLTypes:
    """Test CMDB GraphQL type definitions and structure."""

    def test_lifecycle_state_enum_importable(self):
        """LifecycleStateGQL enum is importable and has expected values."""
        assert hasattr(LifecycleStateGQL, "PLANNED")
        assert hasattr(LifecycleStateGQL, "ACTIVE")
        assert hasattr(LifecycleStateGQL, "MAINTENANCE")
        assert hasattr(LifecycleStateGQL, "RETIRED")
        assert hasattr(LifecycleStateGQL, "DELETED")

    def test_measuring_unit_enum_importable(self):
        """MeasuringUnitGQL enum is importable and has expected values."""
        assert hasattr(MeasuringUnitGQL, "HOUR")
        assert hasattr(MeasuringUnitGQL, "DAY")
        assert hasattr(MeasuringUnitGQL, "MONTH")
        assert hasattr(MeasuringUnitGQL, "GB")
        assert hasattr(MeasuringUnitGQL, "REQUEST")
        assert hasattr(MeasuringUnitGQL, "USER")
        assert hasattr(MeasuringUnitGQL, "INSTANCE")

    def test_ci_class_type_importable(self):
        """CIClassType is importable and has Strawberry definition."""
        assert hasattr(CIClassType, "__strawberry_definition__")
        definition = CIClassType.__strawberry_definition__
        assert definition is not None

    def test_ci_class_type_has_expected_fields(self):
        """CIClassType has expected field names in Strawberry definition."""
        definition = CIClassType.__strawberry_definition__
        field_names = {field.python_name for field in definition.fields}

        expected_fields = {
            "id",
            "tenant_id",
            "name",
            "display_name",
            "parent_class_id",
            "semantic_type_id",
            "schema_def",
            "icon",
        }

        # Check that all expected fields are present (there may be more)
        assert expected_fields.issubset(field_names)


class TestCatalogGraphQLTypes:
    """Test catalog GraphQL type definitions and structure."""

    def test_service_offering_type_importable(self):
        """ServiceOfferingType is importable and has Strawberry definition."""
        assert hasattr(ServiceOfferingType, "__strawberry_definition__")
        definition = ServiceOfferingType.__strawberry_definition__
        assert definition is not None

    def test_service_offering_type_has_expected_fields(self):
        """ServiceOfferingType has expected field names in Strawberry definition."""
        definition = ServiceOfferingType.__strawberry_definition__
        field_names = {field.python_name for field in definition.fields}

        expected_fields = {
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
        }

        assert expected_fields.issubset(field_names)

    def test_service_offering_list_type_importable(self):
        """ServiceOfferingListType is importable and has Strawberry definition."""
        assert hasattr(ServiceOfferingListType, "__strawberry_definition__")
        definition = ServiceOfferingListType.__strawberry_definition__
        assert definition is not None

    def test_price_list_item_type_importable(self):
        """PriceListItemType is importable and has Strawberry definition."""
        assert hasattr(PriceListItemType, "__strawberry_definition__")
        definition = PriceListItemType.__strawberry_definition__
        assert definition is not None

    def test_price_list_item_type_has_expected_fields(self):
        """PriceListItemType has expected field names in Strawberry definition."""
        definition = PriceListItemType.__strawberry_definition__
        field_names = {field.python_name for field in definition.fields}

        expected_fields = {
            "id",
            "price_list_id",
            "service_offering_id",
            "price_per_unit",
            "currency",
            "min_quantity",
            "max_quantity",
            "created_at",
            "updated_at",
        }

        assert expected_fields.issubset(field_names)
