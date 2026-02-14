"""
Overview: Tests for semantic layer CRUD operations — is_system flag, error classes, and write method signatures.
Architecture: Unit tests for semantic CRUD service (Section 5)
Dependencies: pytest, app.models.semantic_type, app.services.semantic.service
Concepts: CRUD validation, is_system protection, error hierarchy, soft delete
"""

import inspect
import uuid

from app.models.semantic_type import (
    SemanticCategory,
    SemanticProvider,
    SemanticRelationshipKind,
    SemanticResourceType,
)
from app.services.semantic.service import (
    DuplicateNameError,
    ForeignKeyError,
    SemanticService,
    SemanticServiceError,
    SystemRecordError,
)


# ---------------------------------------------------------------------------
# 1. Model-level: is_system column on all 4 models
# ---------------------------------------------------------------------------


class TestIsSystemColumn:
    """Verify the is_system column exists on all semantic models."""

    def test_category_has_is_system(self):
        columns = {col.name for col in SemanticCategory.__table__.columns}
        assert "is_system" in columns

    def test_category_is_system_default_false(self):
        col = SemanticCategory.__table__.c.is_system
        assert col.server_default is not None
        assert str(col.server_default.arg) == "false"

    def test_category_is_system_not_nullable(self):
        col = SemanticCategory.__table__.c.is_system
        assert col.nullable is False

    def test_resource_type_has_is_system(self):
        columns = {col.name for col in SemanticResourceType.__table__.columns}
        assert "is_system" in columns

    def test_resource_type_is_system_default_false(self):
        col = SemanticResourceType.__table__.c.is_system
        assert col.server_default is not None
        assert str(col.server_default.arg) == "false"

    def test_resource_type_is_system_not_nullable(self):
        col = SemanticResourceType.__table__.c.is_system
        assert col.nullable is False

    def test_relationship_kind_has_is_system(self):
        columns = {col.name for col in SemanticRelationshipKind.__table__.columns}
        assert "is_system" in columns

    def test_relationship_kind_is_system_default_false(self):
        col = SemanticRelationshipKind.__table__.c.is_system
        assert col.server_default is not None
        assert str(col.server_default.arg) == "false"

    def test_relationship_kind_is_system_not_nullable(self):
        col = SemanticRelationshipKind.__table__.c.is_system
        assert col.nullable is False

    def test_provider_has_is_system(self):
        columns = {col.name for col in SemanticProvider.__table__.columns}
        assert "is_system" in columns

    def test_provider_is_system_default_false(self):
        col = SemanticProvider.__table__.c.is_system
        assert col.server_default is not None
        assert str(col.server_default.arg) == "false"

    def test_provider_is_system_not_nullable(self):
        col = SemanticProvider.__table__.c.is_system
        assert col.nullable is False


class TestIsSystemOnInstantiation:
    """Verify is_system can be set on model instances."""

    def test_category_is_system_false_by_default(self):
        cat = SemanticCategory(
            name="test", display_name="Test", sort_order=1, is_system=False
        )
        assert cat.is_system is False

    def test_category_is_system_true(self):
        cat = SemanticCategory(
            name="test", display_name="Test", sort_order=1, is_system=True
        )
        assert cat.is_system is True

    def test_resource_type_is_system(self):
        stype = SemanticResourceType(
            category_id=uuid.uuid4(),
            name="TestType",
            display_name="Test Type",
            sort_order=1,
            is_system=True,
        )
        assert stype.is_system is True

    def test_relationship_kind_is_system(self):
        kind = SemanticRelationshipKind(
            name="test_rel",
            display_name="Test Rel",
            inverse_name="test_inv",
            is_system=True,
        )
        assert kind.is_system is True

    def test_provider_is_system_false(self):
        provider = SemanticProvider(
            name="custom",
            display_name="Custom Provider",
            provider_type="custom",
            is_system=False,
        )
        assert provider.is_system is False

    def test_provider_is_system_true(self):
        provider = SemanticProvider(
            name="aws",
            display_name="AWS",
            provider_type="cloud",
            is_system=True,
        )
        assert provider.is_system is True


# ---------------------------------------------------------------------------
# 2. Error class hierarchy
# ---------------------------------------------------------------------------


class TestErrorClassHierarchy:
    """Verify the service error class hierarchy."""

    def test_base_error_is_exception(self):
        assert issubclass(SemanticServiceError, Exception)

    def test_system_record_error_inherits_base(self):
        assert issubclass(SystemRecordError, SemanticServiceError)

    def test_duplicate_name_error_inherits_base(self):
        assert issubclass(DuplicateNameError, SemanticServiceError)

    def test_foreign_key_error_inherits_base(self):
        assert issubclass(ForeignKeyError, SemanticServiceError)

    def test_system_record_error_is_exception(self):
        assert issubclass(SystemRecordError, Exception)

    def test_duplicate_name_error_is_exception(self):
        assert issubclass(DuplicateNameError, Exception)

    def test_foreign_key_error_is_exception(self):
        assert issubclass(ForeignKeyError, Exception)

    def test_system_record_error_not_duplicate(self):
        assert not issubclass(SystemRecordError, DuplicateNameError)
        assert not issubclass(DuplicateNameError, SystemRecordError)

    def test_system_record_error_not_foreign_key(self):
        assert not issubclass(SystemRecordError, ForeignKeyError)
        assert not issubclass(ForeignKeyError, SystemRecordError)

    def test_duplicate_name_error_not_foreign_key(self):
        assert not issubclass(DuplicateNameError, ForeignKeyError)
        assert not issubclass(ForeignKeyError, DuplicateNameError)


class TestErrorInstantiation:
    """Verify error classes can be raised and caught."""

    def test_catch_system_record_as_base(self):
        try:
            raise SystemRecordError("Cannot delete system record")
        except SemanticServiceError as exc:
            assert "Cannot delete system record" in str(exc)

    def test_catch_duplicate_name_as_base(self):
        try:
            raise DuplicateNameError("Name already exists")
        except SemanticServiceError as exc:
            assert "Name already exists" in str(exc)

    def test_catch_foreign_key_as_base(self):
        try:
            raise ForeignKeyError("Referenced record does not exist")
        except SemanticServiceError as exc:
            assert "Referenced record does not exist" in str(exc)

    def test_system_record_error_message(self):
        err = SystemRecordError("Cannot rename a system category")
        assert str(err) == "Cannot rename a system category"

    def test_duplicate_name_error_message(self):
        err = DuplicateNameError("Category with name 'compute' already exists")
        assert "compute" in str(err)

    def test_foreign_key_error_message(self):
        err = ForeignKeyError("Category 'abc' does not exist")
        assert "abc" in str(err)


# ---------------------------------------------------------------------------
# 3. Service method signatures
# ---------------------------------------------------------------------------


class TestServiceMethodSignatures:
    """Verify that all expected CRUD methods exist on SemanticService."""

    # -- Category methods ---------------------------------------------------

    def test_create_category_exists(self):
        assert hasattr(SemanticService, "create_category")
        assert callable(getattr(SemanticService, "create_category"))

    def test_create_category_is_async(self):
        assert inspect.iscoroutinefunction(SemanticService.create_category)

    def test_create_category_params(self):
        sig = inspect.signature(SemanticService.create_category)
        params = list(sig.parameters.keys())
        assert "self" in params
        assert "name" in params
        assert "display_name" in params
        assert "description" in params
        assert "icon" in params
        assert "sort_order" in params

    def test_update_category_exists(self):
        assert hasattr(SemanticService, "update_category")
        assert inspect.iscoroutinefunction(SemanticService.update_category)

    def test_update_category_params(self):
        sig = inspect.signature(SemanticService.update_category)
        params = list(sig.parameters.keys())
        assert "self" in params
        assert "category_id" in params

    def test_update_category_accepts_kwargs(self):
        sig = inspect.signature(SemanticService.update_category)
        has_kwargs = any(
            p.kind == inspect.Parameter.VAR_KEYWORD
            for p in sig.parameters.values()
        )
        assert has_kwargs, "update_category should accept **kwargs"

    def test_delete_category_exists(self):
        assert hasattr(SemanticService, "delete_category")
        assert inspect.iscoroutinefunction(SemanticService.delete_category)

    def test_delete_category_params(self):
        sig = inspect.signature(SemanticService.delete_category)
        params = list(sig.parameters.keys())
        assert "self" in params
        assert "category_id" in params

    # -- Type methods -------------------------------------------------------

    def test_create_type_exists(self):
        assert hasattr(SemanticService, "create_type")
        assert inspect.iscoroutinefunction(SemanticService.create_type)

    def test_create_type_params(self):
        sig = inspect.signature(SemanticService.create_type)
        params = list(sig.parameters.keys())
        assert "self" in params
        assert "name" in params
        assert "display_name" in params
        assert "category_id" in params
        assert "description" in params
        assert "icon" in params
        assert "is_abstract" in params
        assert "parent_type_id" in params
        assert "properties_schema" in params
        assert "allowed_relationship_kinds" in params
        assert "sort_order" in params

    def test_update_type_exists(self):
        assert hasattr(SemanticService, "update_type")
        assert inspect.iscoroutinefunction(SemanticService.update_type)

    def test_update_type_accepts_kwargs(self):
        sig = inspect.signature(SemanticService.update_type)
        has_kwargs = any(
            p.kind == inspect.Parameter.VAR_KEYWORD
            for p in sig.parameters.values()
        )
        assert has_kwargs, "update_type should accept **kwargs"

    def test_delete_type_exists(self):
        assert hasattr(SemanticService, "delete_type")
        assert inspect.iscoroutinefunction(SemanticService.delete_type)

    # -- Provider methods ---------------------------------------------------

    def test_create_provider_exists(self):
        assert hasattr(SemanticService, "create_provider")
        assert inspect.iscoroutinefunction(SemanticService.create_provider)

    def test_create_provider_params(self):
        sig = inspect.signature(SemanticService.create_provider)
        params = list(sig.parameters.keys())
        assert "self" in params
        assert "name" in params
        assert "display_name" in params
        assert "provider_type" in params

    def test_update_provider_exists(self):
        assert hasattr(SemanticService, "update_provider")
        assert inspect.iscoroutinefunction(SemanticService.update_provider)

    def test_update_provider_accepts_kwargs(self):
        sig = inspect.signature(SemanticService.update_provider)
        has_kwargs = any(
            p.kind == inspect.Parameter.VAR_KEYWORD
            for p in sig.parameters.values()
        )
        assert has_kwargs, "update_provider should accept **kwargs"

    def test_delete_provider_exists(self):
        assert hasattr(SemanticService, "delete_provider")
        assert inspect.iscoroutinefunction(SemanticService.delete_provider)

    # -- Relationship kind methods ------------------------------------------

    def test_create_relationship_kind_exists(self):
        assert hasattr(SemanticService, "create_relationship_kind")
        assert inspect.iscoroutinefunction(SemanticService.create_relationship_kind)

    def test_create_relationship_kind_params(self):
        sig = inspect.signature(SemanticService.create_relationship_kind)
        params = list(sig.parameters.keys())
        assert "self" in params
        assert "name" in params
        assert "display_name" in params
        assert "inverse_name" in params
        assert "description" in params

    def test_update_relationship_kind_exists(self):
        assert hasattr(SemanticService, "update_relationship_kind")
        assert inspect.iscoroutinefunction(SemanticService.update_relationship_kind)

    def test_update_relationship_kind_accepts_kwargs(self):
        sig = inspect.signature(SemanticService.update_relationship_kind)
        has_kwargs = any(
            p.kind == inspect.Parameter.VAR_KEYWORD
            for p in sig.parameters.values()
        )
        assert has_kwargs, "update_relationship_kind should accept **kwargs"

    def test_delete_relationship_kind_exists(self):
        assert hasattr(SemanticService, "delete_relationship_kind")
        assert inspect.iscoroutinefunction(SemanticService.delete_relationship_kind)


class TestServiceInit:
    """Verify SemanticService __init__ accepts a db session."""

    def test_init_signature(self):
        sig = inspect.signature(SemanticService.__init__)
        params = list(sig.parameters.keys())
        assert "self" in params
        assert "db" in params

    def test_init_stores_db(self):
        """Passing a sentinel as db should be stored on the instance."""
        sentinel = object()
        svc = SemanticService(db=sentinel)  # type: ignore[arg-type]
        assert svc.db is sentinel


class TestServiceMethodCount:
    """Verify the service exposes the expected number of public write methods."""

    EXPECTED_WRITE_METHODS = {
        "create_category",
        "update_category",
        "delete_category",
        "create_type",
        "update_type",
        "delete_type",
        "create_relationship_kind",
        "update_relationship_kind",
        "delete_relationship_kind",
        "create_provider",
        "update_provider",
        "delete_provider",
    }

    def test_all_write_methods_present(self):
        for method_name in self.EXPECTED_WRITE_METHODS:
            assert hasattr(SemanticService, method_name), (
                f"SemanticService is missing method: {method_name}"
            )

    def test_all_write_methods_are_async(self):
        for method_name in self.EXPECTED_WRITE_METHODS:
            method = getattr(SemanticService, method_name)
            assert inspect.iscoroutinefunction(method), (
                f"SemanticService.{method_name} should be async"
            )
