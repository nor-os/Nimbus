"""
Overview: Activity template, definition, and service process service — CRUD for activity templates,
    definitions, processes, process-activity links, and service-to-process assignments.
Architecture: Service delivery process management (Section 8)
Dependencies: sqlalchemy, app.models.cmdb.activity
Concepts: Activity templates group process steps. Definitions specify effort per staff profile.
    Processes group activity templates. Assignments link service offerings to processes.
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.cmdb.activity import (
    ActivityDefinition,
    ActivityTemplate,
    ProcessActivityLink,
    ServiceProcess,
    ServiceProcessAssignment,
)

logger = logging.getLogger(__name__)


class ActivityServiceError(Exception):
    def __init__(self, message: str, code: str = "ACTIVITY_ERROR"):
        self.message = message
        self.code = code
        super().__init__(message)


class ActivityService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ── Templates ────────────────────────────────────────────────────

    async def get_template(self, template_id: str) -> ActivityTemplate | None:
        result = await self.db.execute(
            select(ActivityTemplate)
            .where(
                ActivityTemplate.id == template_id,
                ActivityTemplate.deleted_at.is_(None),
            )
            .options(selectinload(ActivityTemplate.definitions))
        )
        return result.scalar_one_or_none()

    async def list_templates(
        self,
        tenant_id: str,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[ActivityTemplate], int]:
        stmt = select(ActivityTemplate).where(
            ActivityTemplate.tenant_id == tenant_id,
            ActivityTemplate.deleted_at.is_(None),
        )
        count_stmt = select(func.count()).select_from(stmt.subquery())
        count_result = await self.db.execute(count_stmt)
        total = count_result.scalar() or 0

        stmt = stmt.options(selectinload(ActivityTemplate.definitions))
        stmt = stmt.order_by(ActivityTemplate.name)
        stmt = stmt.offset(offset).limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().unique().all()), total

    async def create_template(
        self, tenant_id: str, data: dict
    ) -> ActivityTemplate:
        template = ActivityTemplate(
            tenant_id=tenant_id,
            name=data["name"],
            description=data.get("description"),
        )
        self.db.add(template)
        await self.db.flush()
        return template

    async def update_template(
        self, template_id: str, data: dict
    ) -> ActivityTemplate:
        template = await self.get_template(template_id)
        if not template:
            raise ActivityServiceError("Activity template not found", "NOT_FOUND")
        for key, val in data.items():
            if hasattr(template, key) and key not in ("id", "tenant_id"):
                setattr(template, key, val)
        template.version = (template.version or 1) + 1
        await self.db.flush()
        return template

    async def delete_template(self, template_id: str) -> bool:
        template = await self.get_template(template_id)
        if not template:
            raise ActivityServiceError("Activity template not found", "NOT_FOUND")
        template.deleted_at = datetime.now(UTC)
        await self.db.flush()
        return True

    async def clone_template(
        self, template_id: str, tenant_id: str, new_name: str
    ) -> ActivityTemplate:
        source = await self.get_template(template_id)
        if not source:
            raise ActivityServiceError("Source template not found", "NOT_FOUND")

        clone = ActivityTemplate(
            tenant_id=tenant_id,
            name=new_name,
            description=source.description,
        )
        self.db.add(clone)
        await self.db.flush()

        for defn in source.definitions or []:
            if defn.deleted_at:
                continue
            new_defn = ActivityDefinition(
                template_id=clone.id,
                name=defn.name,
                staff_profile_id=defn.staff_profile_id,
                estimated_hours=defn.estimated_hours,
                sort_order=defn.sort_order,
                is_optional=defn.is_optional,
            )
            self.db.add(new_defn)

        await self.db.flush()
        return clone

    # ── Definitions ──────────────────────────────────────────────────

    async def add_definition(
        self, template_id: str, data: dict
    ) -> ActivityDefinition:
        defn = ActivityDefinition(
            template_id=template_id,
            name=data["name"],
            staff_profile_id=data["staff_profile_id"],
            estimated_hours=data["estimated_hours"],
            sort_order=data.get("sort_order", 0),
            is_optional=data.get("is_optional", False),
        )
        self.db.add(defn)
        await self.db.flush()
        return defn

    async def update_definition(
        self, definition_id: str, data: dict
    ) -> ActivityDefinition:
        result = await self.db.execute(
            select(ActivityDefinition).where(
                ActivityDefinition.id == definition_id,
                ActivityDefinition.deleted_at.is_(None),
            )
        )
        defn = result.scalar_one_or_none()
        if not defn:
            raise ActivityServiceError("Activity definition not found", "NOT_FOUND")
        for key, val in data.items():
            if hasattr(defn, key):
                setattr(defn, key, val)
        await self.db.flush()
        return defn

    async def delete_definition(self, definition_id: str) -> bool:
        result = await self.db.execute(
            select(ActivityDefinition).where(
                ActivityDefinition.id == definition_id,
                ActivityDefinition.deleted_at.is_(None),
            )
        )
        defn = result.scalar_one_or_none()
        if not defn:
            raise ActivityServiceError("Activity definition not found", "NOT_FOUND")
        defn.deleted_at = datetime.now(UTC)
        await self.db.flush()
        return True

    async def list_definitions_by_staff_profile(
        self, staff_profile_id: str
    ) -> list[ActivityDefinition]:
        """List all activity definitions that reference a given staff profile."""
        result = await self.db.execute(
            select(ActivityDefinition).where(
                ActivityDefinition.staff_profile_id == staff_profile_id,
                ActivityDefinition.deleted_at.is_(None),
            )
        )
        return list(result.scalars().all())

    # ── Service Processes ────────────────────────────────────────────

    async def get_process(self, process_id: str) -> ServiceProcess | None:
        result = await self.db.execute(
            select(ServiceProcess)
            .where(
                ServiceProcess.id == process_id,
                ServiceProcess.deleted_at.is_(None),
            )
            .options(selectinload(ServiceProcess.activity_links))
        )
        return result.scalar_one_or_none()

    async def list_processes(
        self,
        tenant_id: str,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[ServiceProcess], int]:
        stmt = select(ServiceProcess).where(
            ServiceProcess.tenant_id == tenant_id,
            ServiceProcess.deleted_at.is_(None),
        )
        count_stmt = select(func.count()).select_from(stmt.subquery())
        count_result = await self.db.execute(count_stmt)
        total = count_result.scalar() or 0

        stmt = stmt.options(selectinload(ServiceProcess.activity_links))
        stmt = stmt.order_by(ServiceProcess.sort_order, ServiceProcess.name)
        stmt = stmt.offset(offset).limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().unique().all()), total

    async def create_process(
        self, tenant_id: str, data: dict
    ) -> ServiceProcess:
        process = ServiceProcess(
            tenant_id=tenant_id,
            name=data["name"],
            description=data.get("description"),
            sort_order=data.get("sort_order", 0),
        )
        self.db.add(process)
        await self.db.flush()
        return process

    async def update_process(
        self, process_id: str, data: dict
    ) -> ServiceProcess:
        process = await self.get_process(process_id)
        if not process:
            raise ActivityServiceError("Service process not found", "NOT_FOUND")
        for key, val in data.items():
            if hasattr(process, key) and key not in ("id", "tenant_id"):
                setattr(process, key, val)
        process.version = (process.version or 1) + 1
        await self.db.flush()
        return process

    async def delete_process(self, process_id: str) -> bool:
        process = await self.get_process(process_id)
        if not process:
            raise ActivityServiceError("Service process not found", "NOT_FOUND")
        process.deleted_at = datetime.now(UTC)
        await self.db.flush()
        return True

    # ── Process Activity Links ───────────────────────────────────────

    async def add_activity_to_process(
        self, process_id: str, data: dict
    ) -> ProcessActivityLink:
        link = ProcessActivityLink(
            process_id=process_id,
            activity_template_id=data["activity_template_id"],
            sort_order=data.get("sort_order", 0),
            is_required=data.get("is_required", True),
        )
        self.db.add(link)
        await self.db.flush()
        return link

    async def remove_activity_from_process(self, link_id: str) -> bool:
        result = await self.db.execute(
            select(ProcessActivityLink).where(
                ProcessActivityLink.id == link_id,
                ProcessActivityLink.deleted_at.is_(None),
            )
        )
        link = result.scalar_one_or_none()
        if not link:
            raise ActivityServiceError("Process activity link not found", "NOT_FOUND")
        link.deleted_at = datetime.now(UTC)
        await self.db.flush()
        return True

    # ── Service Process Assignments ──────────────────────────────────

    async def list_assignments(
        self, tenant_id: str, service_offering_id: str | None = None
    ) -> list[ServiceProcessAssignment]:
        stmt = select(ServiceProcessAssignment).where(
            ServiceProcessAssignment.tenant_id == tenant_id,
            ServiceProcessAssignment.deleted_at.is_(None),
        )
        if service_offering_id:
            stmt = stmt.where(
                ServiceProcessAssignment.service_offering_id == service_offering_id
            )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def create_assignment(
        self, tenant_id: str, data: dict
    ) -> ServiceProcessAssignment:
        assignment = ServiceProcessAssignment(
            tenant_id=tenant_id,
            service_offering_id=data["service_offering_id"],
            process_id=data["process_id"],
            coverage_model=data.get("coverage_model"),
            is_default=data.get("is_default", False),
        )
        self.db.add(assignment)
        await self.db.flush()
        return assignment

    async def delete_assignment(self, assignment_id: str) -> bool:
        result = await self.db.execute(
            select(ServiceProcessAssignment).where(
                ServiceProcessAssignment.id == assignment_id,
                ServiceProcessAssignment.deleted_at.is_(None),
            )
        )
        assignment = result.scalar_one_or_none()
        if not assignment:
            raise ActivityServiceError("Assignment not found", "NOT_FOUND")
        assignment.deleted_at = datetime.now(UTC)
        await self.db.flush()
        return True
