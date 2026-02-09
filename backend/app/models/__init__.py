"""
Overview: Model package — imports all models for Alembic metadata registration.
Architecture: Central model registry (Section 4)
Dependencies: app.models.*
Concepts: ORM model discovery
"""

from app.models.abac_policy import ABACPolicy
from app.models.approval_policy import ApprovalPolicy
from app.models.approval_request import ApprovalRequest
from app.models.approval_step import ApprovalStep
from app.models.audit import AuditLog, RedactionRule, RetentionPolicy, SavedQuery
from app.models.compartment import Compartment
from app.models.domain_mapping import DomainMapping
from app.models.group import Group
from app.models.group_membership import GroupMembership
from app.models.group_role import GroupRole
from app.models.identity_provider import IdentityProvider
from app.models.idp_claim_mapping import IdPClaimMapping
from app.models.impersonation import ImpersonationSession
from app.models.notification import Notification
from app.models.notification_preference import NotificationPreference
from app.models.notification_template import NotificationTemplate
from app.models.permission import Permission
from app.models.permission_override import PermissionOverride
from app.models.provider import Provider
from app.models.role import Role
from app.models.role_permission import RolePermission
from app.models.scim_token import SCIMToken
from app.models.semantic_type import (
    SemanticCategory,
    SemanticProvider,
    SemanticProviderResourceType,
    SemanticRelationshipKind,
    SemanticResourceType,
    SemanticTypeMapping,
)
from app.models.session import Session
from app.models.system_config import SystemConfig
from app.models.tenant import Tenant
from app.models.tenant_quota import TenantQuota
from app.models.tenant_settings import TenantSettings
from app.models.user import User
from app.models.user_group import UserGroup
from app.models.user_role import UserRole
from app.models.user_tenant import UserTenant
from app.models.webhook_config import WebhookConfig
from app.models.webhook_delivery import WebhookDelivery

__all__ = [
    "ABACPolicy",
    "ApprovalPolicy",
    "ApprovalRequest",
    "ApprovalStep",
    "AuditLog",
    "Compartment",
    "DomainMapping",
    "Group",
    "GroupMembership",
    "GroupRole",
    "IdPClaimMapping",
    "IdentityProvider",
    "ImpersonationSession",
    "Notification",
    "NotificationPreference",
    "NotificationTemplate",
    "Permission",
    "PermissionOverride",
    "Provider",
    "RedactionRule",
    "RetentionPolicy",
    "Role",
    "RolePermission",
    "SCIMToken",
    "SavedQuery",
    "SemanticCategory",
    "SemanticProvider",
    "SemanticProviderResourceType",
    "SemanticRelationshipKind",
    "SemanticResourceType",
    "SemanticTypeMapping",
    "Session",
    "SystemConfig",
    "Tenant",
    "TenantQuota",
    "TenantSettings",
    "User",
    "UserGroup",
    "UserRole",
    "UserTenant",
    "WebhookConfig",
    "WebhookDelivery",
]
