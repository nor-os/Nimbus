"""
Overview: Root GraphQL schema combining all query and mutation types.
Architecture: GraphQL schema definition (Section 7.2)
Dependencies: strawberry, app.api.graphql.queries, app.api.graphql.mutations
Concepts: GraphQL schema, query and mutation aggregation
"""

import strawberry

from app.api.graphql.mutations.architecture import ArchitectureMutation
from app.api.graphql.mutations.approval import ApprovalMutation
from app.api.graphql.mutations.audit import AuditMutation
from app.api.graphql.mutations.catalog import CatalogMutation
from app.api.graphql.mutations.cloud_backend import CloudBackendMutation
from app.api.graphql.mutations.component import ComponentMutation
from app.api.graphql.mutations.cluster import ClusterMutation
from app.api.graphql.mutations.currency import CurrencyMutation
from app.api.graphql.mutations.deployment import DeploymentMutation
from app.api.graphql.mutations.cmdb import CMDBMutation
from app.api.graphql.mutations.delivery import DeliveryMutation
from app.api.graphql.mutations.impersonation import ImpersonationMutation
from app.api.graphql.mutations.landing_zone import LandingZoneMutation
from app.api.graphql.mutations.notification import NotificationMutation
from app.api.graphql.mutations.os_image import OsImageMutation
from app.api.graphql.mutations.permissions import PermissionMutation
from app.api.graphql.mutations.policy import PolicyMutation
from app.api.graphql.mutations.semantic import SemanticMutation
from app.api.graphql.mutations.service_catalog_mutations import ServiceCatalogMutation
from app.api.graphql.mutations.tenant_tag import TenantTagMutation
from app.api.graphql.mutations.tenants import TenantMutation
from app.api.graphql.mutations.users import UserMutation
from app.api.graphql.mutations.workflow import WorkflowMutation
from app.api.graphql.queries.architecture import ArchitectureQuery
from app.api.graphql.queries.approval import ApprovalQuery
from app.api.graphql.queries.audit import AuditQuery
from app.api.graphql.queries.catalog import CatalogQuery
from app.api.graphql.queries.cloud_backend import CloudBackendQuery
from app.api.graphql.queries.component import ComponentQuery
from app.api.graphql.queries.cluster import ClusterQuery
from app.api.graphql.queries.currency import CurrencyQuery
from app.api.graphql.queries.deployment import DeploymentQuery
from app.api.graphql.queries.cmdb import CMDBQuery
from app.api.graphql.queries.delivery import DeliveryQuery
from app.api.graphql.queries.health import HealthQuery
from app.api.graphql.queries.impersonation import ImpersonationQuery
from app.api.graphql.queries.landing_zone import LandingZoneQuery
from app.api.graphql.queries.notification import NotificationQuery
from app.api.graphql.queries.os_image import OsImageQuery
from app.api.graphql.queries.permissions import PermissionQuery
from app.api.graphql.queries.policy import PolicyQuery
from app.api.graphql.queries.semantic import SemanticQuery
from app.api.graphql.queries.service_catalog_queries import ServiceCatalogQuery
from app.api.graphql.queries.tenant_tag import TenantTagQuery
from app.api.graphql.queries.tenants import TenantQuery
from app.api.graphql.queries.users import UserQuery
from app.api.graphql.queries.workflow import WorkflowQuery


@strawberry.type
class Query(
    HealthQuery, TenantQuery, TenantTagQuery, PermissionQuery, UserQuery,
    AuditQuery, ImpersonationQuery, NotificationQuery, ApprovalQuery,
    SemanticQuery, WorkflowQuery, CMDBQuery, ClusterQuery, CatalogQuery, DeliveryQuery,
    ArchitectureQuery, ServiceCatalogQuery, CloudBackendQuery, CurrencyQuery, DeploymentQuery,
    LandingZoneQuery, PolicyQuery, OsImageQuery, ComponentQuery,
):
    pass


@strawberry.type
class Mutation(
    TenantMutation, TenantTagMutation, PermissionMutation, UserMutation, AuditMutation,
    ImpersonationMutation, NotificationMutation, ApprovalMutation,
    SemanticMutation, WorkflowMutation, CMDBMutation, ClusterMutation, CatalogMutation,
    DeliveryMutation, ArchitectureMutation, ServiceCatalogMutation, CloudBackendMutation, DeploymentMutation,
    LandingZoneMutation, CurrencyMutation, PolicyMutation, OsImageMutation, ComponentMutation,
):
    pass


schema = strawberry.Schema(query=Query, mutation=Mutation)
