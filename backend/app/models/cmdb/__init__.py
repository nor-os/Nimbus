"""
Overview: CMDB model package — re-exports all CMDB models for convenient importing.
Architecture: Configuration Management Database models (Section 8)
Dependencies: app.models.cmdb.*
Concepts: CI classes, configuration items, relationships, snapshots, templates, service catalog,
    delivery regions, region acceptance, staff profiles, activities, processes, estimations,
    price list templates, organizational units
"""

from app.models.cmdb.activity import (
    ActivityDefinition,
    ActivityTemplate,
    ProcessActivityLink,
    ServiceProcess,
    ServiceProcessAssignment,
)
from app.models.cmdb.ci import ConfigurationItem
from app.models.cmdb.ci_class import CIAttributeDefinition, CIClass
from app.models.cmdb.ci_class_activity_association import CIClassActivityAssociation
from app.models.cmdb.ci_relationship import CIRelationship
from app.models.cmdb.ci_snapshot import CISnapshot
from app.models.cmdb.ci_template import CITemplate
from app.models.cmdb.delivery_region import DeliveryRegion
from app.models.cmdb.estimation import EstimationLineItem, ServiceEstimation
from app.models.cmdb.price_list import PriceList, PriceListItem, TenantPriceOverride
from app.models.cmdb.price_list_template import PriceListTemplate, PriceListTemplateItem
from app.models.cmdb.region_acceptance import (
    RegionAcceptanceTemplate,
    RegionAcceptanceTemplateRule,
    TenantRegionAcceptance,
    TenantRegionTemplateAssignment,
)
from app.models.cmdb.relationship_type import RelationshipType
from app.models.cmdb.saved_search import SavedSearch
from app.models.cmdb.service_offering import ServiceOffering
from app.models.cmdb.service_offering_ci_class import ServiceOfferingCIClass
from app.models.cmdb.service_offering_region import ServiceOfferingRegion
from app.models.cmdb.staff_profile import InternalRateCard, OrganizationalUnit, StaffProfile

__all__ = [
    "ActivityDefinition",
    "ActivityTemplate",
    "CIAttributeDefinition",
    "CIClass",
    "CIClassActivityAssociation",
    "CIRelationship",
    "CISnapshot",
    "CITemplate",
    "ConfigurationItem",
    "DeliveryRegion",
    "EstimationLineItem",
    "InternalRateCard",
    "OrganizationalUnit",
    "PriceList",
    "PriceListItem",
    "PriceListTemplate",
    "PriceListTemplateItem",
    "ProcessActivityLink",
    "RegionAcceptanceTemplate",
    "RegionAcceptanceTemplateRule",
    "RelationshipType",
    "SavedSearch",
    "ServiceEstimation",
    "ServiceOffering",
    "ServiceOfferingCIClass",
    "ServiceOfferingRegion",
    "ServiceProcess",
    "ServiceProcessAssignment",
    "StaffProfile",
    "TenantPriceOverride",
    "TenantRegionAcceptance",
    "TenantRegionTemplateAssignment",
]
