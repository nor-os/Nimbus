"""
Overview: API v1 router aggregating all REST endpoint routers.
Architecture: REST API routing (Section 7.1)
Dependencies: fastapi, app.api.v1.endpoints
Concepts: API routing, versioned endpoints
"""

from fastapi import APIRouter

from app.api.v1.endpoints.abac_policies import router as abac_policies_router
from app.api.v1.endpoints.audit import router as audit_router
from app.api.v1.endpoints.auth import router as auth_router
from app.api.v1.endpoints.compartments import router as compartment_router
from app.api.v1.endpoints.domain_mappings import router as domain_mappings_router
from app.api.v1.endpoints.impersonation import router as impersonation_router
from app.api.v1.endpoints.groups import router as groups_router
from app.api.v1.endpoints.identity_providers import router as idp_router
from app.api.v1.endpoints.permission_overrides import router as permission_overrides_router
from app.api.v1.endpoints.permissions import router as permissions_router
from app.api.v1.endpoints.roles import router as roles_router
from app.api.v1.endpoints.scim_tokens import router as scim_tokens_router
from app.api.v1.endpoints.setup import router as setup_router
from app.api.v1.endpoints.tenant_export import router as tenant_export_router
from app.api.v1.endpoints.tenants import router as tenant_router
from app.api.v1.endpoints.users import router as users_router

router = APIRouter(prefix="/api/v1")
router.include_router(auth_router)
router.include_router(setup_router)
router.include_router(tenant_router)
router.include_router(compartment_router)
router.include_router(tenant_export_router)
router.include_router(users_router)
router.include_router(idp_router)
router.include_router(scim_tokens_router)
router.include_router(permissions_router)
router.include_router(permission_overrides_router)
router.include_router(roles_router)
router.include_router(groups_router)
router.include_router(abac_policies_router)
router.include_router(audit_router)
router.include_router(domain_mappings_router)
router.include_router(impersonation_router)
