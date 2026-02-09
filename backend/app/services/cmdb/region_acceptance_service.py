"""
Overview: Region acceptance service — CRUD for templates, rules, tenant acceptances,
    and effective region acceptance resolution with compliance enforcement.
Architecture: Service delivery compliance engine (Section 8)
Dependencies: sqlalchemy, app.models.cmdb.region_acceptance
Concepts: Region acceptance determines which delivery regions a tenant permits.
    Resolution: direct tenant override → assigned template → default accepted.
    Compliance enforcement blocks pricing and estimation creation for blocked regions.
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cmdb.region_acceptance import (
    RegionAcceptanceTemplate,
    RegionAcceptanceTemplateRule,
    TenantRegionAcceptance,
    TenantRegionTemplateAssignment,
)

logger = logging.getLogger(__name__)


class ComplianceViolationError(Exception):
    def __init__(self, message: str, region_id: str | None = None):
        self.message = message
        self.region_id = region_id
        super().__init__(message)


class RegionAcceptanceServiceError(Exception):
    def __init__(self, message: str, code: str = "ACCEPTANCE_ERROR"):
        self.message = message
        self.code = code
        super().__init__(message)


class RegionAcceptanceService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ── Templates ────────────────────────────────────────────────────

    async def get_template(self, template_id: str) -> RegionAcceptanceTemplate | None:
        result = await self.db.execute(
            select(RegionAcceptanceTemplate).where(
                RegionAcceptanceTemplate.id == template_id,
                RegionAcceptanceTemplate.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def list_templates(
        self, tenant_id: str | None = None
    ) -> list[RegionAcceptanceTemplate]:
        stmt = select(RegionAcceptanceTemplate).where(
            RegionAcceptanceTemplate.deleted_at.is_(None)
        )
        if tenant_id:
            stmt = stmt.where(
                (RegionAcceptanceTemplate.tenant_id == tenant_id)
                | (RegionAcceptanceTemplate.tenant_id.is_(None))
            )
        stmt = stmt.order_by(RegionAcceptanceTemplate.name)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def create_template(
        self, tenant_id: str | None, data: dict
    ) -> RegionAcceptanceTemplate:
        template = RegionAcceptanceTemplate(
            tenant_id=tenant_id,
            name=data["name"],
            description=data.get("description"),
            is_system=data.get("is_system", False),
        )
        self.db.add(template)
        await self.db.flush()
        return template

    async def delete_template(self, template_id: str) -> bool:
        template = await self.get_template(template_id)
        if not template:
            raise RegionAcceptanceServiceError("Template not found", "NOT_FOUND")
        if template.is_system:
            raise RegionAcceptanceServiceError(
                "Cannot delete system template", "SYSTEM_PROTECTED"
            )
        template.deleted_at = datetime.now(UTC)
        await self.db.flush()
        return True

    # ── Template Rules ───────────────────────────────────────────────

    async def list_template_rules(
        self, template_id: str
    ) -> list[RegionAcceptanceTemplateRule]:
        result = await self.db.execute(
            select(RegionAcceptanceTemplateRule).where(
                RegionAcceptanceTemplateRule.template_id == template_id,
                RegionAcceptanceTemplateRule.deleted_at.is_(None),
            )
        )
        return list(result.scalars().all())

    async def add_template_rule(
        self, template_id: str, data: dict
    ) -> RegionAcceptanceTemplateRule:
        rule = RegionAcceptanceTemplateRule(
            template_id=template_id,
            delivery_region_id=data["delivery_region_id"],
            acceptance_type=data["acceptance_type"],
            reason=data.get("reason"),
        )
        self.db.add(rule)
        await self.db.flush()
        return rule

    async def delete_template_rule(self, rule_id: str) -> bool:
        result = await self.db.execute(
            select(RegionAcceptanceTemplateRule).where(
                RegionAcceptanceTemplateRule.id == rule_id,
                RegionAcceptanceTemplateRule.deleted_at.is_(None),
            )
        )
        rule = result.scalar_one_or_none()
        if not rule:
            raise RegionAcceptanceServiceError("Template rule not found", "NOT_FOUND")
        rule.deleted_at = datetime.now(UTC)
        await self.db.flush()
        return True

    # ── Tenant Acceptances ───────────────────────────────────────────

    async def list_tenant_acceptances(
        self, tenant_id: str
    ) -> list[TenantRegionAcceptance]:
        result = await self.db.execute(
            select(TenantRegionAcceptance).where(
                TenantRegionAcceptance.tenant_id == tenant_id,
                TenantRegionAcceptance.deleted_at.is_(None),
            )
        )
        return list(result.scalars().all())

    async def set_tenant_acceptance(
        self, tenant_id: str, data: dict
    ) -> TenantRegionAcceptance:
        acceptance = TenantRegionAcceptance(
            tenant_id=tenant_id,
            delivery_region_id=data["delivery_region_id"],
            acceptance_type=data["acceptance_type"],
            reason=data.get("reason"),
            is_compliance_enforced=data.get("is_compliance_enforced", False),
        )
        self.db.add(acceptance)
        await self.db.flush()
        return acceptance

    async def delete_tenant_acceptance(
        self, acceptance_id: str, tenant_id: str
    ) -> bool:
        result = await self.db.execute(
            select(TenantRegionAcceptance).where(
                TenantRegionAcceptance.id == acceptance_id,
                TenantRegionAcceptance.tenant_id == tenant_id,
                TenantRegionAcceptance.deleted_at.is_(None),
            )
        )
        acceptance = result.scalar_one_or_none()
        if not acceptance:
            raise RegionAcceptanceServiceError("Acceptance not found", "NOT_FOUND")
        acceptance.deleted_at = datetime.now(UTC)
        await self.db.flush()
        return True

    # ── Template Assignments ─────────────────────────────────────────

    async def assign_template_to_tenant(
        self, tenant_id: str, template_id: str
    ) -> TenantRegionTemplateAssignment:
        assignment = TenantRegionTemplateAssignment(
            tenant_id=tenant_id,
            template_id=template_id,
        )
        self.db.add(assignment)
        await self.db.flush()
        return assignment

    async def get_tenant_template_assignment(
        self, tenant_id: str
    ) -> TenantRegionTemplateAssignment | None:
        result = await self.db.execute(
            select(TenantRegionTemplateAssignment).where(
                TenantRegionTemplateAssignment.tenant_id == tenant_id,
                TenantRegionTemplateAssignment.deleted_at.is_(None),
            ).order_by(TenantRegionTemplateAssignment.created_at.desc())
        )
        return result.scalar_one_or_none()

    # ── Effective Resolution ─────────────────────────────────────────

    async def get_effective_region_acceptance(
        self, tenant_id: str, region_id: str
    ) -> dict:
        """Resolve effective acceptance for a tenant+region.

        Priority: direct tenant override → assigned template → default accepted.
        Returns dict with acceptance_type, reason, is_compliance_enforced, source.
        """
        # 1. Direct tenant override
        result = await self.db.execute(
            select(TenantRegionAcceptance).where(
                TenantRegionAcceptance.tenant_id == tenant_id,
                TenantRegionAcceptance.delivery_region_id == region_id,
                TenantRegionAcceptance.deleted_at.is_(None),
            ).order_by(TenantRegionAcceptance.created_at.desc())
        )
        direct = result.scalar_one_or_none()
        if direct:
            return {
                "acceptance_type": direct.acceptance_type,
                "reason": direct.reason,
                "is_compliance_enforced": direct.is_compliance_enforced,
                "source": "direct",
            }

        # 2. Assigned template
        assignment = await self.get_tenant_template_assignment(tenant_id)
        if assignment:
            rule_result = await self.db.execute(
                select(RegionAcceptanceTemplateRule).where(
                    RegionAcceptanceTemplateRule.template_id == assignment.template_id,
                    RegionAcceptanceTemplateRule.delivery_region_id == region_id,
                    RegionAcceptanceTemplateRule.deleted_at.is_(None),
                )
            )
            rule = rule_result.scalar_one_or_none()
            if rule:
                return {
                    "acceptance_type": rule.acceptance_type,
                    "reason": rule.reason,
                    "is_compliance_enforced": False,
                    "source": "template",
                }

        # 3. Default: accepted
        return {
            "acceptance_type": "accepted",
            "reason": None,
            "is_compliance_enforced": False,
            "source": "default",
        }

    async def check_compliance(self, tenant_id: str, region_id: str) -> None:
        """Raise ComplianceViolationError if region is blocked with enforcement."""
        if not region_id:
            return
        acceptance = await self.get_effective_region_acceptance(tenant_id, region_id)
        if (
            acceptance["acceptance_type"] == "blocked"
            and acceptance["is_compliance_enforced"]
        ):
            raise ComplianceViolationError(
                f"Region is blocked by compliance policy: {acceptance.get('reason', 'No reason')}",
                region_id=region_id,
            )
