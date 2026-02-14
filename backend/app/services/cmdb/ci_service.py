"""
Overview: Configuration Item service — CRUD, lifecycle management, and relationship operations.
Architecture: Tenant-scoped service for CI management with audit integration (Section 8)
Dependencies: sqlalchemy, app.models.cmdb.*, app.services.cmdb.validation_service
Concepts: CIs go through lifecycle states (planned→active→maintenance→retired→deleted). Each
    mutation creates a snapshot and logs an audit event. Attributes are validated against the
    CI class schema before persistence.
"""

import contextlib
import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.cmdb.ci import ConfigurationItem
from app.models.cmdb.ci_class import CIClass
from app.models.cmdb.ci_relationship import CIRelationship
from app.models.cmdb.ci_snapshot import CISnapshot
from app.models.cmdb.relationship_type import RelationshipType
from app.schemas.cmdb import LIFECYCLE_TRANSITIONS
from app.services.cmdb.validation_service import (
    ValidationError,
    merge_schemas,
    validate_ci_attributes,
)

logger = logging.getLogger(__name__)


class CIServiceError(Exception):
    def __init__(self, message: str, code: str = "CI_ERROR"):
        self.message = message
        self.code = code
        super().__init__(message)


class CIService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ── CI CRUD ───────────────────────────────────────────────────────

    async def create_ci(
        self,
        tenant_id: str,
        data: dict,
        user_id: str | None = None,
    ) -> ConfigurationItem:
        """Create a CI, validate attributes, create initial snapshot."""
        ci_class = await self._get_class(data["ci_class_id"])
        if not ci_class:
            raise CIServiceError("CI class not found", "CLASS_NOT_FOUND")

        attributes = data.get("attributes") or {}
        effective_schema = self._get_effective_schema(ci_class)
        result = validate_ci_attributes(
            attributes,
            effective_schema,
            list(ci_class.attribute_definitions) if ci_class.attribute_definitions else None,
        )
        if not result.is_valid:
            raise ValidationError(
                f"Attribute validation failed: {result.errors}",
                code="VALIDATION_FAILED",
            )

        ci = ConfigurationItem(
            tenant_id=tenant_id,
            ci_class_id=data["ci_class_id"],
            compartment_id=data.get("compartment_id"),
            name=data["name"],
            description=data.get("description"),
            lifecycle_state=data.get("lifecycle_state", "planned"),
            attributes=attributes,
            tags=data.get("tags") or {},
            cloud_resource_id=data.get("cloud_resource_id"),
            pulumi_urn=data.get("pulumi_urn"),
        )
        self.db.add(ci)
        await self.db.flush()

        await self._create_snapshot(
            ci, tenant_id, user_id, "create", "Initial creation"
        )

        return ci

    async def update_ci(
        self,
        ci_id: str,
        tenant_id: str,
        data: dict,
        user_id: str | None = None,
        reason: str | None = None,
    ) -> ConfigurationItem:
        """Update a CI, validate attributes, create snapshot."""
        ci = await self.get_ci(ci_id, tenant_id)
        if not ci:
            raise CIServiceError("CI not found", "CI_NOT_FOUND")

        if "attributes" in data and data["attributes"] is not None:
            ci_class = await self._get_class(ci.ci_class_id)
            effective_schema = self._get_effective_schema(ci_class) if ci_class else None
            merged_attrs = {**ci.attributes, **data["attributes"]}
            attr_defs = (
                list(ci_class.attribute_definitions)
                if ci_class and ci_class.attribute_definitions
                else None
            )
            result = validate_ci_attributes(
                merged_attrs, effective_schema, attr_defs,
            )
            if not result.is_valid:
                raise ValidationError(
                    f"Attribute validation failed: {result.errors}",
                    code="VALIDATION_FAILED",
                )
            ci.attributes = merged_attrs

        for field in ("name", "description", "tags", "cloud_resource_id", "pulumi_urn"):
            if field in data and data[field] is not None:
                setattr(ci, field, data[field])

        await self.db.flush()
        await self._create_snapshot(ci, tenant_id, user_id, "update", reason)

        return ci

    async def delete_ci(
        self,
        ci_id: str,
        tenant_id: str,
        user_id: str | None = None,
    ) -> bool:
        """Soft-delete a CI and create final snapshot."""
        ci = await self.get_ci(ci_id, tenant_id)
        if not ci:
            raise CIServiceError("CI not found", "CI_NOT_FOUND")

        ci.deleted_at = datetime.now(UTC)
        ci.lifecycle_state = "deleted"
        await self.db.flush()
        await self._create_snapshot(ci, tenant_id, user_id, "delete", "Deleted")
        return True

    async def get_ci(
        self,
        ci_id: str,
        tenant_id: str,
        version: int | None = None,
    ) -> ConfigurationItem | None:
        """Get a CI by ID. If version is specified, return snapshot data."""
        if version is not None:
            snapshot = await self.db.execute(
                select(CISnapshot).where(
                    CISnapshot.ci_id == ci_id,
                    CISnapshot.tenant_id == tenant_id,
                    CISnapshot.version_number == version,
                )
            )
            snap = snapshot.scalar_one_or_none()
            if not snap:
                return None
            ci = await self.db.execute(
                select(ConfigurationItem)
                .where(ConfigurationItem.id == ci_id, ConfigurationItem.tenant_id == tenant_id)
                .options(selectinload(ConfigurationItem.ci_class))
            )
            ci_obj = ci.scalar_one_or_none()
            if ci_obj and snap.snapshot_data:
                for key, val in snap.snapshot_data.items():
                    if hasattr(ci_obj, key) and key not in ("id", "tenant_id", "ci_class_id"):
                        with contextlib.suppress(AttributeError, TypeError):
                            setattr(ci_obj, key, val)
            return ci_obj

        result = await self.db.execute(
            select(ConfigurationItem)
            .where(
                ConfigurationItem.id == ci_id,
                ConfigurationItem.tenant_id == tenant_id,
                ConfigurationItem.deleted_at.is_(None),
            )
            .options(selectinload(ConfigurationItem.ci_class))
        )
        return result.scalar_one_or_none()

    async def list_cis(
        self,
        tenant_id: str,
        ci_class_id: str | None = None,
        compartment_id: str | None = None,
        backend_id: str | None = None,
        lifecycle_state: str | None = None,
        search: str | None = None,
        tags: dict | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[ConfigurationItem], int]:
        """List CIs with filtering and pagination."""
        stmt = select(ConfigurationItem).where(
            ConfigurationItem.tenant_id == tenant_id,
            ConfigurationItem.deleted_at.is_(None),
        )

        if ci_class_id:
            stmt = stmt.where(ConfigurationItem.ci_class_id == ci_class_id)
        if compartment_id:
            stmt = stmt.where(ConfigurationItem.compartment_id == compartment_id)
        if backend_id:
            stmt = stmt.where(ConfigurationItem.backend_id == backend_id)
        if lifecycle_state:
            stmt = stmt.where(ConfigurationItem.lifecycle_state == lifecycle_state)
        if search:
            pattern = f"%{search}%"
            stmt = stmt.where(
                or_(
                    ConfigurationItem.name.ilike(pattern),
                    ConfigurationItem.description.ilike(pattern),
                )
            )
        if tags:
            for key, value in tags.items():
                stmt = stmt.where(
                    ConfigurationItem.tags[key].astext == str(value)
                )

        count_stmt = select(func.count()).select_from(stmt.subquery())
        count_result = await self.db.execute(count_stmt)
        total = count_result.scalar() or 0

        stmt = stmt.options(selectinload(ConfigurationItem.ci_class))
        stmt = stmt.order_by(ConfigurationItem.name)
        stmt = stmt.offset(offset).limit(limit)
        result = await self.db.execute(stmt)
        items = list(result.scalars().unique().all())

        return items, total

    async def move_ci(
        self,
        ci_id: str,
        tenant_id: str,
        compartment_id: str | None,
        user_id: str | None = None,
    ) -> ConfigurationItem:
        """Move a CI to a different compartment."""
        ci = await self.get_ci(ci_id, tenant_id)
        if not ci:
            raise CIServiceError("CI not found", "CI_NOT_FOUND")

        ci.compartment_id = compartment_id
        await self.db.flush()
        await self._create_snapshot(
            ci, tenant_id, user_id, "move",
            f"Moved to compartment {compartment_id}",
        )
        return ci

    async def change_lifecycle(
        self,
        ci_id: str,
        tenant_id: str,
        new_state: str,
        user_id: str | None = None,
    ) -> ConfigurationItem:
        """Change the lifecycle state of a CI with transition validation."""
        ci = await self.get_ci(ci_id, tenant_id)
        if not ci:
            raise CIServiceError("CI not found", "CI_NOT_FOUND")

        allowed = LIFECYCLE_TRANSITIONS.get(ci.lifecycle_state, [])
        if new_state not in allowed:
            raise CIServiceError(
                f"Invalid transition: {ci.lifecycle_state} → {new_state}. "
                f"Allowed: {allowed}",
                "INVALID_TRANSITION",
            )

        old_state = ci.lifecycle_state
        ci.lifecycle_state = new_state
        await self.db.flush()
        await self._create_snapshot(
            ci, tenant_id, user_id, "lifecycle_change",
            f"State changed: {old_state} → {new_state}",
        )
        return ci

    # ── Relationships ─────────────────────────────────────────────────

    async def add_relationship(
        self,
        tenant_id: str,
        source_ci_id: str,
        target_ci_id: str,
        relationship_type_id: str,
        attributes: dict | None = None,
    ) -> CIRelationship:
        """Create a relationship between two CIs with constraint validation."""
        # Load relationship type
        rt_result = await self.db.execute(
            select(RelationshipType).where(
                RelationshipType.id == relationship_type_id,
                RelationshipType.deleted_at.is_(None),
            )
        )
        rel_type = rt_result.scalar_one_or_none()
        if not rel_type:
            raise CIServiceError("Relationship type not found", "RELTYPE_NOT_FOUND")

        # Load source and target CIs with class + semantic type
        source_ci = await self._load_ci_with_class(source_ci_id, tenant_id)
        target_ci = await self._load_ci_with_class(target_ci_id, tenant_id)

        # Validate constraints
        self._validate_relationship_constraints(rel_type, source_ci, target_ci)

        rel = CIRelationship(
            tenant_id=tenant_id,
            source_ci_id=source_ci_id,
            target_ci_id=target_ci_id,
            relationship_type_id=relationship_type_id,
            attributes=attributes,
        )
        self.db.add(rel)
        await self.db.flush()
        return rel

    async def _load_ci_with_class(self, ci_id: str, tenant_id: str) -> ConfigurationItem:
        """Load a CI with its class and class's semantic type eagerly."""
        result = await self.db.execute(
            select(ConfigurationItem)
            .options(selectinload(ConfigurationItem.ci_class))
            .where(
                ConfigurationItem.id == ci_id,
                ConfigurationItem.tenant_id == tenant_id,
                ConfigurationItem.deleted_at.is_(None),
            )
        )
        ci = result.scalar_one_or_none()
        if not ci:
            raise CIServiceError(f"CI {ci_id} not found", "CI_NOT_FOUND")
        return ci

    def _validate_relationship_constraints(
        self,
        rel_type: RelationshipType,
        source_ci: ConfigurationItem,
        target_ci: ConfigurationItem,
    ) -> None:
        """Validate that source/target CIs satisfy relationship type constraints."""
        # Entity type check — both sides must be 'ci' or 'any'
        if rel_type.source_entity_type not in ("ci", "any"):
            raise CIServiceError(
                f"Relationship '{rel_type.name}' requires source entity type "
                f"'{rel_type.source_entity_type}', not 'ci'",
                "CONSTRAINT_VIOLATION",
            )
        if rel_type.target_entity_type not in ("ci", "any"):
            raise CIServiceError(
                f"Relationship '{rel_type.name}' requires target entity type "
                f"'{rel_type.target_entity_type}', not 'ci'",
                "CONSTRAINT_VIOLATION",
            )

        # Source semantic category constraint
        if rel_type.source_semantic_categories:
            src_cat = self._get_ci_semantic_category(source_ci)
            if src_cat and src_cat not in rel_type.source_semantic_categories:
                raise CIServiceError(
                    f"Source CI category '{src_cat}' not in allowed: "
                    f"{rel_type.source_semantic_categories}",
                    "CONSTRAINT_VIOLATION",
                )

        # Target semantic category constraint
        if rel_type.target_semantic_categories:
            tgt_cat = self._get_ci_semantic_category(target_ci)
            if tgt_cat and tgt_cat not in rel_type.target_semantic_categories:
                raise CIServiceError(
                    f"Target CI category '{tgt_cat}' not in allowed: "
                    f"{rel_type.target_semantic_categories}",
                    "CONSTRAINT_VIOLATION",
                )

        # Source semantic type constraint
        if rel_type.source_semantic_types:
            src_type = str(source_ci.ci_class.semantic_type_id) if source_ci.ci_class and source_ci.ci_class.semantic_type_id else None
            if src_type and src_type not in [str(t) for t in rel_type.source_semantic_types]:
                raise CIServiceError(
                    f"Source CI semantic type not in allowed types",
                    "CONSTRAINT_VIOLATION",
                )

        # Target semantic type constraint
        if rel_type.target_semantic_types:
            tgt_type = str(target_ci.ci_class.semantic_type_id) if target_ci.ci_class and target_ci.ci_class.semantic_type_id else None
            if tgt_type and tgt_type not in [str(t) for t in rel_type.target_semantic_types]:
                raise CIServiceError(
                    f"Target CI semantic type not in allowed types",
                    "CONSTRAINT_VIOLATION",
                )

    @staticmethod
    def _get_ci_semantic_category(ci: ConfigurationItem) -> str | None:
        """Extract the semantic category name from a CI's class semantic type."""
        if not ci.ci_class or not ci.ci_class.semantic_type_id:
            return None
        # The semantic category is looked up via the class's semantic_type → category
        # For constraint checking we rely on the category name stored in the type's category FK
        st = getattr(ci.ci_class, "semantic_type", None)
        if st and hasattr(st, "category") and st.category:
            return st.category.name if hasattr(st.category, "name") else None
        return None

    async def remove_relationship(
        self,
        relationship_id: str,
        tenant_id: str,
    ) -> bool:
        """Soft-delete a CI relationship."""
        result = await self.db.execute(
            select(CIRelationship).where(
                CIRelationship.id == relationship_id,
                CIRelationship.tenant_id == tenant_id,
                CIRelationship.deleted_at.is_(None),
            )
        )
        rel = result.scalar_one_or_none()
        if not rel:
            raise CIServiceError("Relationship not found", "RELATIONSHIP_NOT_FOUND")

        rel.deleted_at = datetime.now(UTC)
        await self.db.flush()
        return True

    async def get_relationships(
        self,
        ci_id: str,
        tenant_id: str,
        relationship_type_id: str | None = None,
        direction: str = "both",
    ) -> list[CIRelationship]:
        """Get relationships for a CI, optionally filtered by type and direction."""
        conditions = [
            CIRelationship.tenant_id == tenant_id,
            CIRelationship.deleted_at.is_(None),
        ]

        if direction == "outgoing":
            conditions.append(CIRelationship.source_ci_id == ci_id)
        elif direction == "incoming":
            conditions.append(CIRelationship.target_ci_id == ci_id)
        else:
            conditions.append(
                or_(
                    CIRelationship.source_ci_id == ci_id,
                    CIRelationship.target_ci_id == ci_id,
                )
            )

        if relationship_type_id:
            conditions.append(
                CIRelationship.relationship_type_id == relationship_type_id
            )

        result = await self.db.execute(
            select(CIRelationship)
            .where(*conditions)
            .options(
                selectinload(CIRelationship.source_ci),
                selectinload(CIRelationship.target_ci),
                selectinload(CIRelationship.relationship_type),
            )
        )
        return list(result.scalars().unique().all())

    async def list_relationship_types(self) -> list[RelationshipType]:
        """List all active relationship types."""
        result = await self.db.execute(
            select(RelationshipType).where(
                RelationshipType.deleted_at.is_(None)
            ).order_by(RelationshipType.name)
        )
        return list(result.scalars().all())

    # ── Explorer ───────────────────────────────────────────────────────

    async def get_explorer_summary(
        self,
        tenant_id: str,
        compartment_id: str | None = None,
        backend_id: str | None = None,
    ):
        """Get aggregated CI counts grouped by semantic category/type and backend."""
        from app.api.graphql.types.cmdb import (
            ExplorerBackendSummary,
            ExplorerCategorySummary,
            ExplorerSummaryType,
            ExplorerTypeSummary,
        )
        from app.models.cloud_backend import CloudBackend
        from app.models.semantic_type import SemanticCategory, SemanticResourceType

        # Base filter for CIs
        base_conditions = [
            ConfigurationItem.tenant_id == tenant_id,
            ConfigurationItem.deleted_at.is_(None),
        ]
        if compartment_id:
            base_conditions.append(
                ConfigurationItem.compartment_id == compartment_id
            )
        if backend_id:
            base_conditions.append(
                ConfigurationItem.backend_id == backend_id
            )

        # Total count
        total_stmt = select(func.count()).select_from(
            select(ConfigurationItem.id).where(*base_conditions).subquery()
        )
        total_result = await self.db.execute(total_stmt)
        total_cis = total_result.scalar() or 0

        # Count CIs per class (join to get semantic info)
        count_stmt = (
            select(
                CIClass.id.label("class_id"),
                CIClass.name.label("class_name"),
                CIClass.display_name.label("class_display_name"),
                CIClass.icon.label("class_icon"),
                CIClass.semantic_type_id,
                func.count(ConfigurationItem.id).label("ci_count"),
            )
            .select_from(ConfigurationItem)
            .join(CIClass, ConfigurationItem.ci_class_id == CIClass.id)
            .where(*base_conditions)
            .group_by(
                CIClass.id,
                CIClass.name,
                CIClass.display_name,
                CIClass.icon,
                CIClass.semantic_type_id,
            )
        )
        count_result = await self.db.execute(count_stmt)
        class_counts = count_result.all()

        # Load semantic types and categories for mapping
        semantic_type_ids = {
            row.semantic_type_id for row in class_counts if row.semantic_type_id
        }
        type_to_category: dict[str, tuple[str, str, str | None]] = {}
        if semantic_type_ids:
            st_stmt = (
                select(
                    SemanticResourceType.id,
                    SemanticResourceType.name,
                    SemanticResourceType.display_name,
                    SemanticCategory.id.label("cat_id"),
                    SemanticCategory.name.label("cat_name"),
                    SemanticCategory.display_name.label("cat_display_name"),
                    SemanticCategory.icon.label("cat_icon"),
                )
                .join(
                    SemanticCategory,
                    SemanticResourceType.category_id == SemanticCategory.id,
                )
                .where(SemanticResourceType.id.in_(semantic_type_ids))
            )
            st_result = await self.db.execute(st_stmt)
            for st_row in st_result.all():
                type_to_category[str(st_row.id)] = (
                    str(st_row.cat_id),
                    st_row.cat_display_name or st_row.cat_name,
                    st_row.cat_icon,
                )

        # Build category → types hierarchy
        categories_map: dict[str, dict] = {}
        for row in class_counts:
            st_id = str(row.semantic_type_id) if row.semantic_type_id else None
            if st_id and st_id in type_to_category:
                cat_id, cat_name, cat_icon = type_to_category[st_id]
            else:
                cat_id = "__uncategorized__"
                cat_name = "Uncategorized"
                cat_icon = None

            if cat_id not in categories_map:
                categories_map[cat_id] = {
                    "category_id": cat_id if cat_id != "__uncategorized__" else None,
                    "category_name": cat_name,
                    "category_icon": cat_icon,
                    "types": [],
                    "total_count": 0,
                }

            # Load the semantic type display name
            st_name = row.class_display_name or row.class_name
            if st_id and st_id in type_to_category:
                # Get actual semantic type name
                st_name_stmt = select(
                    SemanticResourceType.display_name,
                    SemanticResourceType.name,
                ).where(SemanticResourceType.id == st_id)
                st_name_result = await self.db.execute(st_name_stmt)
                st_name_row = st_name_result.one_or_none()
                if st_name_row:
                    st_name = st_name_row.display_name or st_name_row.name

            categories_map[cat_id]["types"].append(
                ExplorerTypeSummary(
                    semantic_type_id=st_id,
                    semantic_type_name=st_name,
                    ci_class_id=str(row.class_id),
                    ci_class_name=row.class_display_name or row.class_name,
                    ci_class_icon=row.class_icon,
                    count=row.ci_count,
                )
            )
            categories_map[cat_id]["total_count"] += row.ci_count

        categories = [
            ExplorerCategorySummary(**cat_data)
            for cat_data in sorted(
                categories_map.values(), key=lambda c: c["category_name"]
            )
        ]

        # Backend counts
        backend_stmt = (
            select(
                CloudBackend.id.label("backend_id"),
                CloudBackend.name.label("backend_name"),
                func.count(ConfigurationItem.id).label("ci_count"),
            )
            .select_from(ConfigurationItem)
            .join(CloudBackend, ConfigurationItem.backend_id == CloudBackend.id)
            .where(*base_conditions)
            .group_by(CloudBackend.id, CloudBackend.name)
        )
        backend_result = await self.db.execute(backend_stmt)
        backends = [
            ExplorerBackendSummary(
                backend_id=str(row.backend_id),
                backend_name=row.backend_name,
                provider_name="",
                ci_count=row.ci_count,
            )
            for row in backend_result.all()
        ]

        return ExplorerSummaryType(
            total_cis=total_cis,
            categories=categories,
            backends=backends,
        )

    # ── Private helpers ───────────────────────────────────────────────

    async def _get_class(self, class_id: uuid.UUID | str) -> CIClass | None:
        result = await self.db.execute(
            select(CIClass)
            .where(CIClass.id == class_id, CIClass.deleted_at.is_(None))
            .options(selectinload(CIClass.attribute_definitions))
        )
        return result.scalar_one_or_none()

    def _get_effective_schema(self, ci_class: CIClass) -> dict | None:
        """Get the merged schema for a class (including parent chain)."""
        if not ci_class.parent_class:
            return ci_class.schema
        parent_schema = self._get_effective_schema(ci_class.parent_class)
        return merge_schemas(parent_schema, ci_class.schema)

    async def _create_snapshot(
        self,
        ci: ConfigurationItem,
        tenant_id: str,
        user_id: str | None,
        change_type: str,
        reason: str | None,
    ) -> CISnapshot:
        """Create a versioned snapshot of the CI's current state."""
        count_result = await self.db.execute(
            select(func.count()).select_from(
                select(CISnapshot).where(CISnapshot.ci_id == ci.id).subquery()
            )
        )
        version = (count_result.scalar() or 0) + 1

        snapshot = CISnapshot(
            ci_id=ci.id,
            tenant_id=tenant_id,
            version_number=version,
            snapshot_data={
                "name": ci.name,
                "description": ci.description,
                "lifecycle_state": ci.lifecycle_state,
                "attributes": ci.attributes,
                "tags": ci.tags,
                "compartment_id": str(ci.compartment_id) if ci.compartment_id else None,
                "cloud_resource_id": ci.cloud_resource_id,
                "pulumi_urn": ci.pulumi_urn,
            },
            changed_by=user_id,
            change_reason=reason,
            change_type=change_type,
        )
        self.db.add(snapshot)
        await self.db.flush()
        return snapshot
