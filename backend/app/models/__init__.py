"""
Overview: Model package — imports all models for Alembic metadata registration.
Architecture: Central model registry (Section 4)
Dependencies: app.models.*
Concepts: ORM model discovery
"""

from app.models.abac_policy import ABACPolicy
from app.models.architecture_topology import ArchitectureTopology
from app.models.approval_policy import ApprovalPolicy
from app.models.approval_request import ApprovalRequest
from app.models.approval_step import ApprovalStep
from app.models.audit import AuditLog, CategoryRetentionOverride, RedactionRule, RetentionPolicy, SavedQuery
from app.models.cmdb import (
    ActivityDefinition,
    ActivityTemplate,
    StackBlueprintParameter,
    CIAttributeDefinition,
    CIClass,
    CIClassActivityAssociation,
    CIRelationship,
    CISnapshot,
    CITemplate,
    ConfigurationItem,
    ConsumptionRecord,
    DeliveryRegion,
    EstimationLineItem,
    InternalRateCard,
    PriceList,
    PriceListItem,
    PriceListTemplate,
    PriceListTemplateItem,
    ProviderSku,
    RegionAcceptanceTemplate,
    RegionAcceptanceTemplateRule,
    RelationshipType,
    SavedSearch,
    ServiceCatalog,
    ServiceCatalogItem,
    ServiceCluster,
    ServiceClusterSlot,
    ServiceEstimation,
    ServiceGroup,
    ServiceGroupItem,
    ServiceOffering,
    ServiceOfferingCIClass,
    ServiceOfferingRegion,
    ServiceOfferingSku,
    ServiceProcessAssignment,
    StaffProfile,
    TenantCatalogPin,
    TenantPriceListPin,
    TenantRegionAcceptance,
    TenantRegionTemplateAssignment,
)
from app.models.cloud_backend import CloudBackend, CloudBackendIAMMapping
from app.models.compartment import Compartment
from app.models.currency_exchange_rate import CurrencyExchangeRate
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
from app.models.os_image import OsImage, OsImageProviderMapping, OsImageTenantAssignment
from app.models.permission import Permission
from app.models.policy_library import PolicyLibraryEntry
from app.models.permission_override import PermissionOverride
from app.models.provider import Provider
from app.models.role import Role
from app.models.role_permission import RolePermission
from app.models.scim_token import SCIMToken
from app.models.semantic_activity_type import SemanticActivityType
from app.models.semantic_type import (
    SemanticCategory,
    SemanticProvider,
    SemanticRelationshipKind,
    SemanticResourceType,
)
from app.models.session import Session
from app.models.system_config import SystemConfig
from app.models.tenant import Tenant
from app.models.tenant_quota import TenantQuota
from app.models.tenant_settings import TenantSettings
from app.models.tenant_tag import TenantTag
from app.models.user import User
from app.models.user_group import UserGroup
from app.models.user_role import UserRole
from app.models.user_tenant import UserTenant
from app.models.webhook_config import WebhookConfig
from app.models.webhook_delivery import WebhookDelivery
from app.models.workflow_definition import WorkflowDefinition
from app.models.workflow_execution import WorkflowExecution, WorkflowNodeExecution

__all__ = [
    "ABACPolicy",
    "ArchitectureTopology",
    "ActivityDefinition",
    "ActivityTemplate",
    "ApprovalPolicy",
    "ApprovalRequest",
    "ApprovalStep",
    "AuditLog",
    "CategoryRetentionOverride",
    "CloudBackend",
    "CloudBackendIAMMapping",
    "CIAttributeDefinition",
    "CIClass",
    "CIClassActivityAssociation",
    "CIRelationship",
    "CISnapshot",
    "CITemplate",
    "Compartment",
    "CurrencyExchangeRate",
    "ConfigurationItem",
    "ConsumptionRecord",
    "DeliveryRegion",
    "DomainMapping",
    "EstimationLineItem",
    "Group",
    "GroupMembership",
    "GroupRole",
    "IdPClaimMapping",
    "IdentityProvider",
    "ImpersonationSession",
    "InternalRateCard",
    "Notification",
    "NotificationPreference",
    "NotificationTemplate",
    "OsImage",
    "OsImageProviderMapping",
    "OsImageTenantAssignment",
    "Permission",
    "PermissionOverride",
    "PolicyLibraryEntry",
    "PriceList",
    "PriceListItem",
    "PriceListTemplate",
    "PriceListTemplateItem",
    "Provider",
    "ProviderSku",
    "RedactionRule",
    "RegionAcceptanceTemplate",
    "RegionAcceptanceTemplateRule",
    "RelationshipType",
    "RetentionPolicy",
    "Role",
    "RolePermission",
    "SCIMToken",
    "SavedQuery",
    "SavedSearch",
    "SemanticActivityType",
    "SemanticCategory",
    "SemanticProvider",
    "SemanticRelationshipKind",
    "SemanticResourceType",
    "ServiceCatalog",
    "ServiceCatalogItem",
    "ServiceCluster",
    "ServiceClusterSlot",
    "ServiceEstimation",
    "ServiceGroup",
    "ServiceGroupItem",
    "ServiceOffering",
    "ServiceOfferingCIClass",
    "ServiceOfferingRegion",
    "ServiceOfferingSku",
    "ServiceProcessAssignment",
    "StackBlueprintParameter",
    "Session",
    "StaffProfile",
    "SystemConfig",
    "Tenant",
    "TenantCatalogPin",
    "TenantPriceListPin",
    "TenantQuota",
    "TenantRegionAcceptance",
    "TenantRegionTemplateAssignment",
    "TenantSettings",
    "TenantTag",
    "User",
    "UserGroup",
    "UserRole",
    "UserTenant",
    "WebhookConfig",
    "WebhookDelivery",
    "WorkflowDefinition",
    "WorkflowExecution",
    "WorkflowNodeExecution",
]
