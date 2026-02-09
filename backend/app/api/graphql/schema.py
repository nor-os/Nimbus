"""
Overview: Root GraphQL schema combining all query and mutation types.
Architecture: GraphQL schema definition (Section 7.2)
Dependencies: strawberry, app.api.graphql.queries, app.api.graphql.mutations
Concepts: GraphQL schema, query and mutation aggregation
"""

import strawberry

from app.api.graphql.mutations.approval import ApprovalMutation
from app.api.graphql.mutations.audit import AuditMutation
from app.api.graphql.mutations.catalog import CatalogMutation
from app.api.graphql.mutations.cmdb import CMDBMutation
from app.api.graphql.mutations.delivery import DeliveryMutation
from app.api.graphql.mutations.impersonation import ImpersonationMutation
from app.api.graphql.mutations.notification import NotificationMutation
from app.api.graphql.mutations.permissions import PermissionMutation
from app.api.graphql.mutations.semantic import SemanticMutation
from app.api.graphql.mutations.tenants import TenantMutation
from app.api.graphql.mutations.users import UserMutation
from app.api.graphql.mutations.workflow import WorkflowMutation
from app.api.graphql.queries.approval import ApprovalQuery
from app.api.graphql.queries.audit import AuditQuery
from app.api.graphql.queries.catalog import CatalogQuery
from app.api.graphql.queries.cmdb import CMDBQuery
from app.api.graphql.queries.delivery import DeliveryQuery
from app.api.graphql.queries.health import HealthQuery
from app.api.graphql.queries.impersonation import ImpersonationQuery
from app.api.graphql.queries.notification import NotificationQuery
from app.api.graphql.queries.permissions import PermissionQuery
from app.api.graphql.queries.semantic import SemanticQuery
from app.api.graphql.queries.tenants import TenantQuery
from app.api.graphql.queries.users import UserQuery
from app.api.graphql.queries.workflow import WorkflowQuery


@strawberry.type
class Query(
    HealthQuery, TenantQuery, PermissionQuery, UserQuery,
    AuditQuery, ImpersonationQuery, NotificationQuery, ApprovalQuery,
    SemanticQuery, WorkflowQuery, CMDBQuery, CatalogQuery, DeliveryQuery,
):
    pass


@strawberry.type
class Mutation(
    TenantMutation, PermissionMutation, UserMutation, AuditMutation,
    ImpersonationMutation, NotificationMutation, ApprovalMutation,
    SemanticMutation, WorkflowMutation, CMDBMutation, CatalogMutation,
    DeliveryMutation,
):
    pass


schema = strawberry.Schema(query=Query, mutation=Mutation)
