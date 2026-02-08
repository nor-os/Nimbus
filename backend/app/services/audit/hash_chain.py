"""
Overview: Hash chain service for audit log integrity verification using SHA-256.
Architecture: Audit integrity layer (Section 8)
Dependencies: hashlib, sqlalchemy, app.models.audit
Concepts: Hash chain, tamper detection, advisory locks, chain verification
"""

import hashlib
import json
from dataclasses import dataclass, field

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog


@dataclass
class VerifyResult:
    valid: bool
    total_checked: int = 0
    broken_links: list[dict] = field(default_factory=list)


class HashChainService:
    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    def compute_hash(entry_data: dict, previous_hash: str | None) -> str:
        """Compute SHA-256 hash of sorted entry data concatenated with previous hash."""
        canonical = json.dumps(entry_data, sort_keys=True, default=str)
        payload = f"{canonical}:{previous_hash or ''}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    async def get_previous_hash(self, tenant_id: str) -> str | None:
        """Get the hash of the most recent audit log entry for a tenant.

        Uses PostgreSQL advisory lock to ensure concurrency safety.
        """
        # Advisory lock keyed on tenant_id hash to avoid collisions
        lock_key = int(hashlib.md5(tenant_id.encode()).hexdigest()[:15], 16) % (2**31)
        await self.db.execute(text(f"SELECT pg_advisory_xact_lock({lock_key})"))

        result = await self.db.execute(
            select(AuditLog.hash)
            .where(AuditLog.tenant_id == tenant_id)
            .order_by(AuditLog.created_at.desc())
            .limit(1)
        )
        row = result.scalar_one_or_none()
        return row

    async def verify_chain(
        self,
        tenant_id: str,
        start: int = 0,
        limit: int = 1000,
    ) -> VerifyResult:
        """Walk the hash chain for a tenant and verify integrity."""
        result = await self.db.execute(
            select(AuditLog)
            .where(AuditLog.tenant_id == tenant_id)
            .order_by(AuditLog.created_at.asc())
            .offset(start)
            .limit(limit)
        )
        entries = list(result.scalars().all())

        if not entries:
            return VerifyResult(valid=True, total_checked=0)

        broken_links: list[dict] = []

        for i, entry in enumerate(entries):
            entry_data = _build_entry_data(entry)

            expected_previous = entries[i - 1].hash if i > 0 else None
            # For the first entry in the window, we can't verify previous_hash
            # unless start == 0
            if i == 0 and start > 0:
                expected_previous = entry.previous_hash  # trust it

            expected_hash = HashChainService.compute_hash(entry_data, expected_previous)

            if entry.hash != expected_hash:
                broken_links.append({
                    "entry_id": str(entry.id),
                    "position": start + i,
                    "expected_hash": expected_hash,
                    "actual_hash": entry.hash,
                })

            if i > 0 and entry.previous_hash != entries[i - 1].hash:
                broken_links.append({
                    "entry_id": str(entry.id),
                    "position": start + i,
                    "error": "previous_hash mismatch",
                    "expected_previous": entries[i - 1].hash,
                    "actual_previous": entry.previous_hash,
                })

        return VerifyResult(
            valid=len(broken_links) == 0,
            total_checked=len(entries),
            broken_links=broken_links,
        )


def _build_entry_data(entry: AuditLog) -> dict:
    """Build the canonical data dict for hash computation from an AuditLog entry.

    Conditionally includes event_type and event_category when present to
    maintain backward compatibility with old entries (no recomputation).
    """
    data = {
        "tenant_id": str(entry.tenant_id),
        "actor_id": str(entry.actor_id) if entry.actor_id else None,
        "actor_email": entry.actor_email,
        "action": entry.action.value if entry.action else None,
        "resource_type": entry.resource_type,
        "resource_id": entry.resource_id,
        "resource_name": entry.resource_name,
        "old_values": entry.old_values,
        "new_values": entry.new_values,
        "trace_id": entry.trace_id,
        "priority": entry.priority.value if entry.priority else None,
        "created_at": str(entry.created_at),
    }
    # Include taxonomy fields only if present (new entries)
    if entry.event_type is not None:
        data["event_type"] = entry.event_type
    if entry.event_category is not None:
        data["event_category"] = entry.event_category.value
    return data
