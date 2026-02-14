"""
Overview: Per-provider JSON Schema definitions for credential validation and scope configuration.
Architecture: Schema definitions for CloudBackendService credential validation (Section 11)
Dependencies: None (pure data module)
Concepts: Each provider defines one or more auth types with JSON Schema for credential fields.
    Scope schemas define per-provider configuration (regions, accounts, projects, etc.).
"""

from __future__ import annotations

# -- Credential schemas per provider ----------------------------------------

CREDENTIAL_SCHEMAS: dict[str, dict] = {
    "proxmox": {
        "type": "object",
        "properties": {
            "auth_type": {
                "type": "string",
                "enum": ["api_token", "password"],
                "description": "Authentication method",
            },
            "cluster_url": {
                "type": "string",
                "format": "uri",
                "description": "Proxmox cluster URL (e.g. https://pve.example.com:8006)",
            },
            "token_id": {
                "type": "string",
                "description": "API token ID (e.g. user@pam!token-name)",
            },
            "secret": {
                "type": "string",
                "description": "API token secret",
            },
            "username": {
                "type": "string",
                "description": "Username (e.g. root@pam)",
            },
            "password": {
                "type": "string",
                "description": "Password",
            },
            "verify_ssl": {
                "type": "boolean",
                "default": True,
                "description": "Verify SSL certificates",
            },
        },
        "required": ["auth_type", "cluster_url"],
        "allOf": [
            {
                "if": {"properties": {"auth_type": {"const": "api_token"}}},
                "then": {"required": ["token_id", "secret"]},
            },
            {
                "if": {"properties": {"auth_type": {"const": "password"}}},
                "then": {"required": ["username", "password"]},
            },
        ],
    },
    "aws": {
        "type": "object",
        "properties": {
            "auth_type": {
                "type": "string",
                "enum": ["access_key", "assume_role"],
                "description": "Authentication method",
            },
            "access_key_id": {
                "type": "string",
                "description": "AWS access key ID",
            },
            "secret_access_key": {
                "type": "string",
                "description": "AWS secret access key",
            },
            "region": {
                "type": "string",
                "description": "Default AWS region (e.g. us-east-1)",
            },
            "role_arn": {
                "type": "string",
                "description": "ARN of IAM role to assume",
            },
            "external_id": {
                "type": "string",
                "description": "External ID for cross-account role assumption",
            },
        },
        "required": ["auth_type"],
        "allOf": [
            {
                "if": {"properties": {"auth_type": {"const": "access_key"}}},
                "then": {"required": ["access_key_id", "secret_access_key", "region"]},
            },
            {
                "if": {"properties": {"auth_type": {"const": "assume_role"}}},
                "then": {"required": ["role_arn"]},
            },
        ],
    },
    "azure": {
        "type": "object",
        "properties": {
            "auth_type": {
                "type": "string",
                "enum": ["service_principal"],
                "description": "Authentication method",
            },
            "tenant_id": {
                "type": "string",
                "format": "uuid",
                "description": "Azure AD tenant ID",
            },
            "client_id": {
                "type": "string",
                "format": "uuid",
                "description": "Application (client) ID",
            },
            "client_secret": {
                "type": "string",
                "description": "Client secret",
            },
            "subscription_id": {
                "type": "string",
                "format": "uuid",
                "description": "Default subscription ID",
            },
        },
        "required": ["auth_type", "tenant_id", "client_id", "client_secret", "subscription_id"],
    },
    "gcp": {
        "type": "object",
        "properties": {
            "auth_type": {
                "type": "string",
                "enum": ["service_account"],
                "description": "Authentication method",
            },
            "service_account_json": {
                "type": "string",
                "description": "Service account JSON key (full content)",
            },
            "project_id": {
                "type": "string",
                "description": "Default GCP project ID",
            },
        },
        "required": ["auth_type", "service_account_json", "project_id"],
    },
    "oci": {
        "type": "object",
        "properties": {
            "auth_type": {
                "type": "string",
                "enum": ["api_key"],
                "description": "Authentication method",
            },
            "user_ocid": {
                "type": "string",
                "description": "User OCID",
            },
            "tenancy_ocid": {
                "type": "string",
                "description": "Tenancy OCID",
            },
            "fingerprint": {
                "type": "string",
                "description": "API key fingerprint",
            },
            "private_key": {
                "type": "string",
                "description": "PEM-encoded private key",
            },
            "region": {
                "type": "string",
                "description": "Default OCI region (e.g. us-ashburn-1)",
            },
        },
        "required": ["auth_type", "user_ocid", "tenancy_ocid", "fingerprint", "private_key", "region"],
    },
}

# -- Scope schemas per provider ---------------------------------------------

SCOPE_SCHEMAS: dict[str, dict] = {
    "proxmox": {
        "type": "object",
        "properties": {
            "nodes": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Limit to specific Proxmox nodes (empty = all)",
            },
            "pools": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Limit to specific resource pools",
            },
        },
    },
    "aws": {
        "type": "object",
        "properties": {
            "regions": {
                "type": "array",
                "items": {"type": "string"},
                "description": "AWS regions to manage (e.g. ['us-east-1', 'eu-west-1'])",
            },
            "account_ids": {
                "type": "array",
                "items": {"type": "string"},
                "description": "AWS account IDs to manage",
            },
        },
    },
    "azure": {
        "type": "object",
        "properties": {
            "subscriptions": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Azure subscription IDs",
            },
            "resource_groups": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Limit to specific resource groups",
            },
        },
    },
    "gcp": {
        "type": "object",
        "properties": {
            "projects": {
                "type": "array",
                "items": {"type": "string"},
                "description": "GCP project IDs to manage",
            },
            "regions": {
                "type": "array",
                "items": {"type": "string"},
                "description": "GCP regions (e.g. ['us-central1'])",
            },
        },
    },
    "oci": {
        "type": "object",
        "properties": {
            "compartments": {
                "type": "array",
                "items": {"type": "string"},
                "description": "OCI compartment OCIDs",
            },
            "regions": {
                "type": "array",
                "items": {"type": "string"},
                "description": "OCI regions",
            },
        },
    },
}


def get_credential_schema(provider_name: str) -> dict | None:
    """Get the credential JSON Schema for a provider (case-insensitive)."""
    return CREDENTIAL_SCHEMAS.get(provider_name.lower())


def get_scope_schema(provider_name: str) -> dict | None:
    """Get the scope JSON Schema for a provider (case-insensitive)."""
    return SCOPE_SCHEMAS.get(provider_name.lower())
