"""
Overview: Event taxonomy for structured audit log categorization with dotted-notation event types.
Architecture: Audit taxonomy definitions (Section 8)
Dependencies: enum
Concepts: Event categories, event types, actor types, taxonomy tree, migration mapping
"""

import enum
import re


class EventCategory(str, enum.Enum):
    API = "API"
    AUTH = "AUTH"
    DATA = "DATA"
    PERMISSION = "PERMISSION"
    SYSTEM = "SYSTEM"
    SECURITY = "SECURITY"
    TENANT = "TENANT"
    USER = "USER"


class ActorType(str, enum.Enum):
    USER = "USER"
    SYSTEM = "SYSTEM"
    SERVICE = "SERVICE"
    ANONYMOUS = "ANONYMOUS"


# ── Full Taxonomy ────────────────────────────────────────────

TAXONOMY: dict[EventCategory, list[dict]] = {
    EventCategory.API: [
        {"key": "api.request", "label": "API Request", "description": "Generic HTTP API request", "default_priority": "INFO"},
        {"key": "api.graphql", "label": "GraphQL Query", "description": "GraphQL query or mutation", "default_priority": "INFO"},
    ],
    EventCategory.AUTH: [
        {"key": "auth.login", "label": "Login", "description": "Successful user login", "default_priority": "INFO"},
        {"key": "auth.login.failed", "label": "Login Failed", "description": "Failed login attempt", "default_priority": "WARN"},
        {"key": "auth.logout", "label": "Logout", "description": "User logout", "default_priority": "INFO"},
        {"key": "auth.token.refresh", "label": "Token Refresh", "description": "Access token refreshed", "default_priority": "INFO"},
        {"key": "auth.token.revoke", "label": "Token Revoke", "description": "Token revoked", "default_priority": "WARN"},
        {"key": "auth.session.expire", "label": "Session Expire", "description": "Session expired", "default_priority": "INFO"},
    ],
    EventCategory.DATA: [
        {"key": "data.create", "label": "Create", "description": "Generic data creation", "default_priority": "INFO"},
        {"key": "data.update", "label": "Update", "description": "Generic data update", "default_priority": "INFO"},
        {"key": "data.delete", "label": "Delete", "description": "Generic data deletion", "default_priority": "WARN"},
        {"key": "data.read", "label": "Read", "description": "Generic data read", "default_priority": "DEBUG"},
        {"key": "data.export", "label": "Export", "description": "Data export", "default_priority": "INFO"},
        {"key": "data.archive", "label": "Archive", "description": "Data archival", "default_priority": "INFO"},
    ],
    EventCategory.PERMISSION: [
        {"key": "permission.check.denied", "label": "Permission Denied", "description": "Permission check failed", "default_priority": "WARN"},
        {"key": "permission.role.assign", "label": "Role Assign", "description": "Role assigned to user", "default_priority": "WARN"},
        {"key": "permission.role.revoke", "label": "Role Revoke", "description": "Role revoked from user", "default_priority": "WARN"},
        {"key": "permission.role.create", "label": "Role Create", "description": "New role created", "default_priority": "WARN"},
        {"key": "permission.role.update", "label": "Role Update", "description": "Role updated", "default_priority": "WARN"},
        {"key": "permission.role.delete", "label": "Role Delete", "description": "Role deleted", "default_priority": "WARN"},
        {"key": "permission.group.assign", "label": "Group Assign", "description": "User added to group", "default_priority": "INFO"},
        {"key": "permission.group.revoke", "label": "Group Revoke", "description": "User removed from group", "default_priority": "INFO"},
    ],
    EventCategory.SYSTEM: [
        {"key": "system.startup", "label": "Startup", "description": "System startup", "default_priority": "INFO"},
        {"key": "system.shutdown", "label": "Shutdown", "description": "System shutdown", "default_priority": "INFO"},
        {"key": "system.config.update", "label": "Config Update", "description": "System configuration changed", "default_priority": "WARN"},
        {"key": "system.migration", "label": "Migration", "description": "Database migration executed", "default_priority": "INFO"},
    ],
    EventCategory.SECURITY: [
        {"key": "security.breakglass.request", "label": "Break-Glass Request", "description": "Emergency access requested", "default_priority": "CRITICAL"},
        {"key": "security.breakglass.activate", "label": "Break-Glass Activate", "description": "Emergency access activated", "default_priority": "CRITICAL"},
        {"key": "security.breakglass.deactivate", "label": "Break-Glass Deactivate", "description": "Emergency access deactivated", "default_priority": "CRITICAL"},
        {"key": "security.impersonate.start", "label": "Impersonate Start", "description": "Impersonation session started", "default_priority": "WARN"},
        {"key": "security.impersonate.end", "label": "Impersonate End", "description": "Impersonation session ended", "default_priority": "WARN"},
        {"key": "security.impersonate.reject", "label": "Impersonate Reject", "description": "Impersonation request rejected", "default_priority": "WARN"},
        {"key": "security.impersonate.expire", "label": "Impersonate Expire", "description": "Impersonation session expired", "default_priority": "WARN"},
        {"key": "security.override", "label": "Override", "description": "Security override activated", "default_priority": "CRITICAL"},
    ],
    EventCategory.TENANT: [
        {"key": "tenant.create", "label": "Tenant Create", "description": "Tenant created", "default_priority": "WARN"},
        {"key": "tenant.update", "label": "Tenant Update", "description": "Tenant updated", "default_priority": "INFO"},
        {"key": "tenant.delete", "label": "Tenant Delete", "description": "Tenant deleted", "default_priority": "CRITICAL"},
        {"key": "tenant.quota.update", "label": "Quota Update", "description": "Tenant quota updated", "default_priority": "WARN"},
        {"key": "tenant.config.update", "label": "Tenant Config Update", "description": "Tenant configuration updated", "default_priority": "WARN"},
    ],
    EventCategory.USER: [
        {"key": "user.create", "label": "User Create", "description": "User account created", "default_priority": "INFO"},
        {"key": "user.update", "label": "User Update", "description": "User account updated", "default_priority": "INFO"},
        {"key": "user.delete", "label": "User Delete", "description": "User account deleted", "default_priority": "WARN"},
        {"key": "user.password.change", "label": "Password Change", "description": "User changed password", "default_priority": "INFO"},
        {"key": "user.password.reset", "label": "Password Reset", "description": "Password reset initiated", "default_priority": "WARN"},
        {"key": "user.activate", "label": "User Activate", "description": "User account activated", "default_priority": "INFO"},
        {"key": "user.deactivate", "label": "User Deactivate", "description": "User account deactivated", "default_priority": "WARN"},
        {"key": "user.scim.provision", "label": "SCIM Provision", "description": "User provisioned via SCIM", "default_priority": "INFO"},
        {"key": "user.scim.deprovision", "label": "SCIM Deprovision", "description": "User deprovisioned via SCIM", "default_priority": "WARN"},
        {"key": "user.scim.update", "label": "SCIM Update", "description": "User updated via SCIM", "default_priority": "INFO"},
    ],
}

# Build a flat lookup of all valid event_type keys
_ALL_EVENT_TYPES: set[str] = set()
_EVENT_TYPE_TO_CATEGORY: dict[str, EventCategory] = {}
_EVENT_TYPE_TO_PRIORITY: dict[str, str] = {}

for cat, entries in TAXONOMY.items():
    for entry in entries:
        key = entry["key"]
        _ALL_EVENT_TYPES.add(key)
        _EVENT_TYPE_TO_CATEGORY[key] = cat
        _EVENT_TYPE_TO_PRIORITY[key] = entry["default_priority"]


# ── Validation & Lookup ──────────────────────────────────────


def validate_event_type(event_type: str) -> bool:
    """Check if an event_type string is in the taxonomy."""
    return event_type in _ALL_EVENT_TYPES


def get_category_for_event_type(event_type: str) -> EventCategory | None:
    """Derive EventCategory from an event_type string.

    Falls back to prefix matching: 'auth.login.failed' -> AUTH.
    """
    if event_type in _EVENT_TYPE_TO_CATEGORY:
        return _EVENT_TYPE_TO_CATEGORY[event_type]
    # Prefix fallback
    prefix = event_type.split(".")[0].upper()
    try:
        return EventCategory(prefix)
    except ValueError:
        return None


def get_default_priority(event_type: str) -> str:
    """Get the default priority for an event_type. Returns 'INFO' if not found."""
    return _EVENT_TYPE_TO_PRIORITY.get(event_type, "INFO")


# ── Table -> Resource Type Mapping ───────────────────────────

TABLE_TO_RESOURCE_TYPE: dict[str, str] = {
    "users": "iam:user",
    "tenants": "tenant:tenant",
    "roles": "iam:role",
    "groups": "iam:group",
    "permissions": "iam:permission",
    "user_roles": "iam:user_role",
    "group_roles": "iam:group_role",
    "user_groups": "iam:user_group",
    "identity_providers": "iam:identity_provider",
    "scim_configs": "iam:scim_config",
    "impersonation_sessions": "security:impersonation",
    "retention_policies": "audit:retention_policy",
    "redaction_rules": "audit:redaction_rule",
    "saved_queries": "audit:saved_query",
}

# ── Table + action -> event_type Mapping ─────────────────────

_TABLE_ACTION_TO_EVENT_TYPE: dict[tuple[str, str], str] = {
    ("users", "CREATE"): "user.create",
    ("users", "UPDATE"): "user.update",
    ("users", "DELETE"): "user.delete",
    ("tenants", "CREATE"): "tenant.create",
    ("tenants", "UPDATE"): "tenant.update",
    ("tenants", "DELETE"): "tenant.delete",
    ("roles", "CREATE"): "permission.role.create",
    ("roles", "UPDATE"): "permission.role.update",
    ("roles", "DELETE"): "permission.role.delete",
    ("user_roles", "CREATE"): "permission.role.assign",
    ("user_roles", "DELETE"): "permission.role.revoke",
    ("group_roles", "CREATE"): "permission.role.assign",
    ("group_roles", "DELETE"): "permission.role.revoke",
    ("user_groups", "CREATE"): "permission.group.assign",
    ("user_groups", "DELETE"): "permission.group.revoke",
    ("groups", "CREATE"): "data.create",
    ("groups", "UPDATE"): "data.update",
    ("groups", "DELETE"): "data.delete",
    ("identity_providers", "CREATE"): "data.create",
    ("identity_providers", "UPDATE"): "data.update",
    ("identity_providers", "DELETE"): "data.delete",
    ("scim_configs", "CREATE"): "data.create",
    ("scim_configs", "UPDATE"): "data.update",
    ("scim_configs", "DELETE"): "data.delete",
    ("impersonation_sessions", "CREATE"): "security.impersonate.start",
    ("impersonation_sessions", "UPDATE"): "data.update",
    ("impersonation_sessions", "DELETE"): "data.delete",
    ("retention_policies", "CREATE"): "data.create",
    ("retention_policies", "UPDATE"): "system.config.update",
    ("retention_policies", "DELETE"): "data.delete",
    ("redaction_rules", "CREATE"): "data.create",
    ("redaction_rules", "UPDATE"): "data.update",
    ("redaction_rules", "DELETE"): "data.delete",
    ("saved_queries", "CREATE"): "data.create",
    ("saved_queries", "UPDATE"): "data.update",
    ("saved_queries", "DELETE"): "data.delete",
}

# Generic fallback: action name -> data.* event_type
_ACTION_TO_DATA_EVENT: dict[str, str] = {
    "CREATE": "data.create",
    "UPDATE": "data.update",
    "DELETE": "data.delete",
    "READ": "data.read",
}


def derive_event_type_from_table(table_name: str, action: str) -> str:
    """Derive event_type from a table name and action string."""
    return _TABLE_ACTION_TO_EVENT_TYPE.get(
        (table_name, action),
        _ACTION_TO_DATA_EVENT.get(action, "data.create"),
    )


# ── Migration Map (old action enum -> new event_type) ────────

ACTION_MIGRATION_MAP: dict[str, tuple[str, str]] = {
    # old_action -> (event_type, event_category)
    "CREATE": ("data.create", "DATA"),
    "READ": ("data.read", "DATA"),
    "UPDATE": ("data.update", "DATA"),
    "DELETE": ("data.delete", "DATA"),
    "LOGIN": ("auth.login", "AUTH"),
    "LOGOUT": ("auth.logout", "AUTH"),
    "PERMISSION_CHANGE": ("permission.role.assign", "PERMISSION"),
    "BREAK_GLASS": ("security.breakglass.activate", "SECURITY"),
    "EXPORT": ("data.export", "DATA"),
    "ARCHIVE": ("data.archive", "DATA"),
    "SYSTEM": ("system.config.update", "SYSTEM"),
    "IMPERSONATE": ("security.impersonate.start", "SECURITY"),
    "OVERRIDE": ("security.override", "SECURITY"),
}


# ── Regex validator ──────────────────────────────────────────

_EVENT_TYPE_PATTERN = re.compile(r"^[a-z][a-z0-9]*(\.[a-z][a-z0-9]*){1,4}$")


def is_valid_event_type_format(event_type: str) -> bool:
    """Check if event_type follows dotted notation format."""
    return bool(_EVENT_TYPE_PATTERN.match(event_type))
