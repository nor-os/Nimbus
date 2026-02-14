"""
Overview: Data classes for policy resolution results and summaries.
Architecture: DTOs for policy resolution service (Section 5)
Dependencies: dataclasses
Concepts: Resolved policies with source tracking, compartment policy summary statistics
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ResolvedPolicy:
    policy_id: str
    name: str
    source: str  # 'library' | 'inline' | 'inherited_library' | 'inherited_inline'
    source_compartment_id: str | None
    statements: list[dict]
    severity: str
    category: str
    can_suppress: bool  # False if ANY statement has effect=deny


@dataclass
class PolicySummary:
    compartment_id: str
    direct_policies: int
    inherited_policies: int
    total_statements: int
    deny_count: int
    allow_count: int
