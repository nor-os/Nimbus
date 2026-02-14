"""
Overview: Policy projection service stub — translates resolved policies to provider-native format.
Architecture: Provider abstraction layer for IAM policy projection (Section 5)
Dependencies: app.services.policy.data_classes
Concepts: Policy projection maps semantic actions to provider-native IAM actions using
    provider resource mappings from the semantic registry. Implemented in Phase 12 (Pulumi Integration).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID

from app.services.policy.data_classes import ResolvedPolicy


@dataclass
class ProviderPolicyDocument:
    provider_id: str
    format: str  # 'aws_iam_json', 'azure_policy', 'gcp_iam_binding', 'proxmox_acl'
    document: dict
    warnings: list[str] = field(default_factory=list)


class PolicyProjectionService:
    async def project_to_provider(
        self,
        resolved_policies: list[ResolvedPolicy],
        provider_id: UUID,
        target_resources: list[str] | None = None,
    ) -> ProviderPolicyDocument:
        """Stub — implementation in Phase 12.

        Will use provider resource mappings from the semantic registry to translate
        semantic actions to provider-native IAM actions.
        """
        raise NotImplementedError(
            "Policy projection implemented in Phase 12 (Pulumi Integration)"
        )
