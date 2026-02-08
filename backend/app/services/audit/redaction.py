"""
Overview: Redaction service for applying regex-based field masking to audit log data.
Architecture: Audit data protection layer (Section 8)
Dependencies: sqlalchemy, re, app.models.audit
Concepts: Data redaction, regex patterns, PII masking
"""

import re
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import RedactionRule


class RedactionService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def redact(self, tenant_id: str, data: dict) -> dict:
        """Apply active redaction rules to a data dict, ordered by priority."""
        rules = await self._get_active_rules(tenant_id)
        if not rules:
            return data
        return _apply_rules(data, rules)

    async def _get_active_rules(self, tenant_id: str) -> list[RedactionRule]:
        result = await self.db.execute(
            select(RedactionRule)
            .where(
                RedactionRule.tenant_id == tenant_id,
                RedactionRule.is_active.is_(True),
                RedactionRule.deleted_at.is_(None),
            )
            .order_by(RedactionRule.priority.asc())
        )
        return list(result.scalars().all())

    # ── CRUD ─────────────────────────────────────────────

    async def create_rule(
        self,
        tenant_id: str,
        field_pattern: str,
        replacement: str = "[REDACTED]",
        is_active: bool = True,
        priority: int = 0,
    ) -> RedactionRule:
        rule = RedactionRule(
            tenant_id=tenant_id,
            field_pattern=field_pattern,
            replacement=replacement,
            is_active=is_active,
            priority=priority,
        )
        self.db.add(rule)
        await self.db.flush()
        return rule

    async def update_rule(self, rule_id: str, tenant_id: str, **kwargs) -> RedactionRule | None:
        result = await self.db.execute(
            select(RedactionRule).where(
                RedactionRule.id == rule_id,
                RedactionRule.tenant_id == tenant_id,
                RedactionRule.deleted_at.is_(None),
            )
        )
        rule = result.scalar_one_or_none()
        if not rule:
            return None
        for key, value in kwargs.items():
            if value is not None and hasattr(rule, key):
                setattr(rule, key, value)
        await self.db.flush()
        return rule

    async def delete_rule(self, rule_id: str, tenant_id: str) -> bool:
        result = await self.db.execute(
            select(RedactionRule).where(
                RedactionRule.id == rule_id,
                RedactionRule.tenant_id == tenant_id,
                RedactionRule.deleted_at.is_(None),
            )
        )
        rule = result.scalar_one_or_none()
        if not rule:
            return False
        rule.deleted_at = datetime.now(UTC)
        await self.db.flush()
        return True

    async def list_rules(self, tenant_id: str) -> list[RedactionRule]:
        result = await self.db.execute(
            select(RedactionRule)
            .where(
                RedactionRule.tenant_id == tenant_id,
                RedactionRule.deleted_at.is_(None),
            )
            .order_by(RedactionRule.priority.asc())
        )
        return list(result.scalars().all())

    async def get_rule(self, rule_id: str, tenant_id: str) -> RedactionRule | None:
        result = await self.db.execute(
            select(RedactionRule).where(
                RedactionRule.id == rule_id,
                RedactionRule.tenant_id == tenant_id,
                RedactionRule.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()


def _apply_rules(data: dict, rules: list[RedactionRule]) -> dict:
    """Recursively apply redaction rules to dict values."""
    result = {}
    for key, value in data.items():
        redacted_value = value
        for rule in rules:
            try:
                if re.search(rule.field_pattern, key):
                    if isinstance(value, str):
                        redacted_value = rule.replacement
                    elif isinstance(value, dict):
                        redacted_value = {k: rule.replacement for k in value}
                    else:
                        redacted_value = rule.replacement
                    break
            except re.error:
                continue
        if isinstance(redacted_value, dict) and redacted_value is value:
            redacted_value = _apply_rules(redacted_value, rules)
        result[key] = redacted_value
    return result
