# Nimbus Architecture Documentation

## Table of Contents

1. [Overview](#1-overview)
2. [System Architecture](#2-system-architecture)
3. [Component Architecture](#3-component-architecture)
4. [Data Architecture](#4-data-architecture)
5. [Security Architecture](#5-security-architecture)
6. [Integration Architecture](#6-integration-architecture)
7. [API Architecture](#7-api-architecture)
8. [Real-time Architecture](#8-real-time-architecture)
9. [Background Processing & Workflow Engine](#9-background-processing--workflow-engine)
10. [Deployment Architecture](#10-deployment-architecture)
11. [Monitoring & Observability](#11-monitoring--observability)
12. [Disaster Recovery](#12-disaster-recovery)

---

## 1. Overview

### 1.1 Purpose

Nimbus is a Pulumi-based SaaS Control Panel for multi-user and multi-tenancy cloud backend management. It provides a unified interface for managing cloud infrastructure across multiple providers (Proxmox, AWS, Azure, GCP, OCI) with enterprise-grade features including CMDB, semantic layer abstraction, and comprehensive audit trails.

### 1.2 Key Capabilities

- **Multi-Cloud Management**: Unified control plane for Proxmox, AWS, Azure, GCP, and OCI
- **Multi-Tenancy**: Hierarchical tenant model (Provider → Tenant → Sub-tenant)
- **Infrastructure as Code**: Pulumi Automation API integration
- **CMDB**: Configuration Management Database with semantic layer
- **Visual Architecture Planning**: Drag-and-drop infrastructure designer
- **Enterprise Security**: HSM support, RBAC+ABAC, impersonation workflows

### 1.3 Design Principles

1. **Security First**: All operations audited, cryptographic proof for critical actions
2. **Tenant Isolation**: Schema per tenant + RLS for all tenants
3. **API-First**: All functionality exposed via versioned REST and GraphQL APIs
4. **Cloud Agnostic**: Abstraction layer normalizes cloud provider differences
5. **Observable**: Comprehensive logging, metrics, and tracing

---

## 2. System Architecture

### 2.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                  CLIENTS                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │   Web UI     │  │  REST API    │  │ GraphQL API  │  │   Webhooks   │    │
│  │  (Angular)   │  │   Clients    │  │   Clients    │  │   Consumers  │    │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘    │
└─────────┼─────────────────┼─────────────────┼─────────────────┼────────────┘
          │                 │                 │                 │
          ▼                 ▼                 ▼                 ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              LOAD BALANCER                                   │
│                        (nginx / cloud-native LB)                            │
└─────────────────────────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                             API GATEWAY LAYER                                │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                         FastAPI Application                          │   │
│  ├─────────────────────────────────────────────────────────────────────┤   │
│  │  ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐           │   │
│  │  │   Auth    │ │   Rate    │ │  Security │ │   Trace   │           │   │
│  │  │Middleware │ │  Limiter  │ │  Headers  │ │    ID     │           │   │
│  │  └───────────┘ └───────────┘ └───────────┘ └───────────┘           │   │
│  ├─────────────────────────────────────────────────────────────────────┤   │
│  │  ┌─────────────────────┐  ┌─────────────────────┐                   │   │
│  │  │     REST Router     │  │   GraphQL Router    │                   │   │
│  │  │    /api/v1/*        │  │   /graphql          │                   │   │
│  │  └─────────────────────┘  └─────────────────────┘                   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                            SERVICE LAYER                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐│
│  │   CMDB     │ │ Permission │ │  Workflow  │ │   Pulumi   │ │    Cost    ││
│  │  Service   │ │  Service   │ │  Service   │ │  Service   │ │  Service   ││
│  └────────────┘ └────────────┘ └────────────┘ └────────────┘ └────────────┘│
│  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐│
│  │   Audit    │ │   Auth     │ │Notification│ │  Semantic  │ │   Drift    ││
│  │  Service   │ │  Service   │ │  Service   │ │  Service   │ │  Service   ││
│  └────────────┘ └────────────┘ └────────────┘ └────────────┘ └────────────┘│
└─────────────────────────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           DATA ACCESS LAYER                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    SQLAlchemy ORM (Async)                            │   │
│  │              Tenant-aware query filtering (RLS)                      │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          INFRASTRUCTURE LAYER                                │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │  PostgreSQL  │  │   Valkey     │  │    MinIO     │  │  Temporal    │    │
│  │   Database   │  │Cache/PubSub │  │   Storage    │  │   Server +   │    │
│  │              │  │ (Phase 12+) │  │              │  │   Workers    │    │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         EXTERNAL INTEGRATIONS                                │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │    Pulumi    │  │   Proxmox   │  │  AWS/Azure   │  │   GCP/OCI    │    │
│  │   Service    │  │  (Phase 7)  │  │ (Phase 17)   │  │ (Phase 17)   │    │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Request Flow

```
Client Request
      │
      ▼
┌─────────────────┐
│  Load Balancer  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐     ┌─────────────────┐
│  Auth Middleware│────▶│  JWT Validation │
└────────┬────────┘     │  + Tenant ID    │
         │              └─────────────────┘
         ▼
┌─────────────────┐
│  Rate Limiter   │──── Per-tenant limits
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Trace ID Inject │──── Correlation ID for logs
└────────┬────────┘
         │
         ▼
┌─────────────────┐     ┌─────────────────┐
│  Permission     │────▶│  RBAC + ABAC    │
│  Check          │     │  Evaluation     │
└────────┬────────┘     └─────────────────┘
         │
         ▼
┌─────────────────┐
│  Service Layer  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Audit Log      │──── Every action logged
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│    Response     │
└─────────────────┘
```

---

## 3. Component Architecture

### 3.1 Backend Components

```
backend/
├── app/
│   ├── api/
│   │   ├── v1/
│   │   │   ├── endpoints/          # REST endpoints
│   │   │   │   ├── auth.py
│   │   │   │   ├── tenants.py
│   │   │   │   ├── cmdb.py
│   │   │   │   ├── workflows.py
│   │   │   │   └── ...
│   │   │   └── router.py
│   │   └── graphql/
│   │       ├── schema.py           # Strawberry schema
│   │       ├── queries/
│   │       ├── mutations/
│   │       └── subscriptions/
│   │
│   ├── core/
│   │   ├── config.py               # Configuration management
│   │   ├── security.py             # Auth, JWT, HSM
│   │   ├── permissions.py          # RBAC + ABAC engine
│   │   └── middleware.py           # Custom middleware
│   │
│   ├── services/
│   │   ├── cmdb/                   # CMDB service
│   │   ├── pulumi/                 # Pulumi Automation API
│   │   ├── semantic/               # Semantic layer
│   │   ├── audit/                  # Audit logging
│   │   ├── notification/           # Email, webhooks
│   │   ├── drift/                  # Drift detection
│   │   └── cost/                   # Cost management
│   │
│   ├── workflows/                  # Temporal workflow definitions
│   │   ├── activities/             # Temporal activities (reusable steps)
│   │   │   ├── approval.py
│   │   │   ├── pulumi_ops.py
│   │   │   ├── notification.py
│   │   │   └── audit.py
│   │   ├── approval.py             # Approval chain workflow
│   │   ├── pulumi_deploy.py        # Pulumi stack operations workflow
│   │   ├── impersonation.py        # Impersonation lifecycle workflow
│   │   ├── break_glass.py          # Emergency access workflow
│   │   ├── drift_remediation.py    # Drift detection → approval → fix
│   │   └── worker.py               # Temporal worker entrypoint
│   │
│   ├── models/
│   │   ├── base.py                 # Base model with tenant_id
│   │   ├── tenant.py
│   │   ├── user.py
│   │   ├── cmdb.py
│   │   └── ...
│   │
│   ├── schemas/                    # Pydantic schemas
│   │   ├── tenant.py
│   │   ├── user.py
│   │   └── ...
│   │
│   ├── db/
│   │   ├── session.py              # Async session management
│   │   ├── tenant_context.py       # Tenant-aware queries
│   │   └── migrations/             # Alembic migrations
│   │
│   └── main.py
│
├── tests/
└── alembic/
```

### 3.2 Frontend Components

```
frontend/
├── src/
│   ├── app/
│   │   ├── core/
│   │   │   ├── auth/               # Authentication
│   │   │   ├── guards/             # Route guards
│   │   │   ├── interceptors/       # HTTP interceptors
│   │   │   └── services/           # Core services
│   │   │
│   │   ├── shared/
│   │   │   ├── components/         # Reusable components
│   │   │   ├── directives/
│   │   │   ├── pipes/
│   │   │   └── models/
│   │   │
│   │   ├── features/
│   │   │   ├── dashboard/
│   │   │   ├── cmdb/
│   │   │   ├── architecture-planner/   # Rete.js integration
│   │   │   ├── tenants/
│   │   │   ├── users/
│   │   │   ├── workflows/
│   │   │   ├── audit/
│   │   │   ├── settings/
│   │   │   └── cost/
│   │   │
│   │   ├── graphql/
│   │   │   ├── queries/
│   │   │   ├── mutations/
│   │   │   └── subscriptions/
│   │   │
│   │   └── app.component.ts
│   │
│   ├── assets/
│   ├── environments/
│   └── styles/
│
├── angular.json
└── package.json
```

### 3.3 Service Interactions

```
┌─────────────────────────────────────────────────────────────────┐
│                        API Request                               │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │  Auth Service   │
                    │  ┌───────────┐  │
                    │  │ JWT Valid │  │
                    │  │ Tenant ID │  │
                    │  │ User Ctx  │  │
                    │  └───────────┘  │
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              ▼              ▼              ▼
     ┌────────────┐  ┌────────────┐  ┌────────────┐
     │ Permission │  │   Audit    │  │   Cache    │
     │  Service   │  │  Service   │  │  Service   │
     └────────────┘  └────────────┘  └────────────┘
              │              │              │
              └──────────────┼──────────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │ Business Logic  │
                    │    Services     │
                    └────────┬────────┘
                             │
         ┌───────────────────┼───────────────────┐
         ▼                   ▼                   ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│  CMDB Service   │ │ Pulumi Service  │ │Temporal Workflows│
│                 │ │                 │ │                 │
│ - Resources     │ │ - Stack Mgmt    │ │ - Approvals     │
│ - Relationships │ │ - State Export  │ │ - Deploy Chains │
│ - Drift         │ │ - Automation    │ │ - Impersonation │
└─────────────────┘ └─────────────────┘ └─────────────────┘
         │                   │                   │
         └───────────────────┼───────────────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │   Data Layer    │
                    │  (PostgreSQL)   │
                    └─────────────────┘
```

---

## 4. Data Architecture

### 4.1 Multi-Tenancy Strategy

Nimbus uses **Schema per Tenant + Row-Level Security (RLS)** as its isolation strategy. This provides the strongest default: schema-level separation for data partitioning plus RLS as a defense-in-depth safety net.

```
┌─────────────────────────────────────────────────────────────────┐
│              SCHEMA PER TENANT + RLS                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Database: nimbus                                                │
│  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐   │
│  │ nimbus_core     │ │nimbus_tenant_001│ │nimbus_tenant_002│   │
│  │ (system tables) │ │ (tenant data)   │ │ (tenant data)   │   │
│  │ - users         │ │ + RLS policies  │ │ + RLS policies  │   │
│  │ - tenants       │ │                 │ │                 │   │
│  │ - providers     │ │                 │ │                 │   │
│  └─────────────────┘ └─────────────────┘ └─────────────────┘   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 4.2 Core Database Schema

```
┌─────────────────────────────────────────────────────────────────┐
│                     CORE SCHEMA (nimbus_core)                    │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────┐       ┌─────────────────┐
│    providers    │       │     tenants     │
├─────────────────┤       ├─────────────────┤
│ id (PK)         │───┐   │ id (PK)         │
│ name            │   │   │ provider_id(FK) │◄──┐
│ created_at      │   └──▶│ parent_id (FK)  │───┘ (self-ref)
│ updated_at      │       │ name            │
│ deleted_at      │       │ isolation_type  │
└─────────────────┘       │ schema_name     │
                          │ settings (JSON) │
                          │ created_at      │
                          │ deleted_at      │
                          └────────┬────────┘
                                   │
        ┌──────────────────────────┼──────────────────────────┐
        ▼                          ▼                          ▼
┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐
│     users       │       │     groups      │       │ cloud_accounts  │
├─────────────────┤       ├─────────────────┤       ├─────────────────┤
│ id (PK)         │       │ id (PK)         │       │ id (PK)         │
│ tenant_id (FK)  │       │ tenant_id (FK)  │       │ tenant_id (FK)  │
│ email           │       │ name            │       │ provider_type   │
│ password_hash   │       │ permissions     │       │ credentials     │
│ mfa_enabled     │       │ created_at      │       │ (encrypted)     │
│ last_login      │       └─────────────────┘       │ created_at      │
│ created_at      │                                 └─────────────────┘
│ deleted_at      │
└─────────────────┘

┌─────────────────┐       ┌─────────────────┐
│  audit_logs     │       │    sessions     │
├─────────────────┤       ├─────────────────┤
│ id (PK)         │       │ id (PK)         │
│ tenant_id (FK)  │       │ user_id (FK)    │
│ user_id (FK)    │       │ token_hash      │
│ action          │       │ refresh_token   │
│ resource_type   │       │ expires_at      │
│ resource_id     │       │ ip_address      │
│ old_value(JSON) │       │ user_agent      │
│ new_value(JSON) │       │ created_at      │
│ trace_id        │       │ revoked_at      │
│ ip_address      │       └─────────────────┘
│ timestamp       │
│ priority        │
└─────────────────┘
```

### 4.3 CMDB Schema

```
┌─────────────────────────────────────────────────────────────────┐
│                     CMDB SCHEMA (per tenant)                     │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────┐       ┌─────────────────┐
│  compartments   │       │   ci_classes    │
├─────────────────┤       ├─────────────────┤
│ id (PK)         │       │ id (PK)         │
│ tenant_id       │       │ name            │
│ parent_id (FK)  │       │ provider_type   │
│ name            │       │ attributes(JSON)│
│ cloud_id        │       │ relationships   │
│ provider_type   │       └────────┬────────┘
│ created_at      │                │
└────────┬────────┘                │
         │                         │
         ▼                         ▼
┌─────────────────────────────────────────────┐
│              configuration_items             │
├─────────────────────────────────────────────┤
│ id (PK)                                      │
│ tenant_id                                    │
│ compartment_id (FK)                          │
│ ci_class_id (FK)                             │
│ cloud_resource_id                            │
│ name                                         │
│ attributes (JSONB)                           │
│ pulumi_urn                                   │
│ state_version                                │
│ created_at                                   │
│ updated_at                                   │
│ deleted_at                                   │
└─────────────────────────────────────────────┘
         │
         ▼
┌─────────────────┐       ┌─────────────────┐
│ ci_relationships│       │   drift_logs    │
├─────────────────┤       ├─────────────────┤
│ id (PK)         │       │ id (PK)         │
│ source_ci (FK)  │       │ ci_id (FK)      │
│ target_ci (FK)  │       │ detected_at     │
│ relationship    │       │ drift_type      │
│ attributes      │       │ expected (JSON) │
└─────────────────┘       │ actual (JSON)   │
                          │ status          │
                          │ resolved_at     │
                          │ resolved_by     │
                          └─────────────────┘
```

### 4.4 Semantic Layer Mapping

```
┌─────────────────────────────────────────────────────────────────┐
│                    SEMANTIC LAYER MAPPING                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Nimbus Concept  │  Proxmox (Phase 7) │  AWS        │  Azure       │  OCI     │
│  ────────────────────────────────────────────────────────────────────────────│
│  Tenancy         │  Datacenter/Cluster│  Account    │ Subscription │ Tenancy  │
│  Compartment     │  Pool              │  Tags/OUs   │ Resource Grp │Compartm  │
│  Network         │  Bridge/SDN VNet   │  VPC        │  VNet        │  VCN     │
│  Subnet          │  SDN Subnet        │  Subnet     │  Subnet      │  Subnet  │
│  Compute         │  QEMU VM / LXC     │  EC2        │  VM          │ Instance │
│  Storage         │  ZFS/Ceph/LVM      │  S3/EBS     │  Blob/Disk   │  Object  │
│  Database        │  N/A (VM-hosted)   │  RDS        │ SQL Database │  ATP     │
│  Load Balancer   │  N/A (VM-hosted)   │  ALB/NLB    │  LB          │  LB      │
│  Security Group  │  Firewall rules    │  SG         │  NSG         │  NSL     │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 5. Security Architecture

### 5.1 Authentication Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    AUTHENTICATION FLOWS                          │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  LOCAL AUTH                                                      │
│  ───────────────────────────────────────────────────────────────│
│                                                                  │
│  User ──▶ Login Form ──▶ Validate ──▶ MFA Check ──▶ JWT Issue   │
│               │              │            │             │        │
│               ▼              ▼            ▼             ▼        │
│          username/pw    password     TOTP/WebAuthn  access_token │
│                         policy                      refresh_token│
│                                                                  │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  OIDC/SAML AUTH                                                  │
│  ───────────────────────────────────────────────────────────────│
│                                                                  │
│  User ──▶ IdP Redirect ──▶ IdP Auth ──▶ Callback ──▶ JWT Issue  │
│               │               │            │             │       │
│               ▼               ▼            ▼             ▼       │
│          auth_request    user login    code/token   map claims  │
│                                                     to tenant   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  TOKEN STRUCTURE                                                 │
│  ───────────────────────────────────────────────────────────────│
│                                                                  │
│  {                                                               │
│    "sub": "user_uuid",                                          │
│    "tenant_id": "tenant_uuid",                                  │
│    "provider_id": "provider_uuid",                              │
│    "roles": ["tenant_admin", "cmdb_write"],                     │
│    "permissions": ["cmdb:read", "cmdb:write", "users:read"],    │
│    "impersonating": null | { "original_user": "...", ... },     │
│    "exp": 1234567890,                                           │
│    "iat": 1234567800,                                           │
│    "jti": "unique_token_id"                                     │
│  }                                                               │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 5.2 Permission Model (RBAC + ABAC)

```
┌─────────────────────────────────────────────────────────────────┐
│                    PERMISSION HIERARCHY                          │
└─────────────────────────────────────────────────────────────────┘

                    ┌─────────────────┐
                    │    Provider     │  Requires HSM/Yubikey
                    │   (Highest)     │  for critical actions
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │  Tenant Admin   │  Full tenant control
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │      User       │  Configurable permissions
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │    Read-Only    │  View access only
                    └─────────────────┘


┌─────────────────────────────────────────────────────────────────┐
│                    RBAC + ABAC EVALUATION                        │
└─────────────────────────────────────────────────────────────────┘

  Request Context                    Policy Evaluation
  ─────────────────                  ─────────────────
  ┌─────────────────┐               ┌─────────────────┐
  │ user_id         │               │ RBAC Check      │
  │ tenant_id       │──────────────▶│ - Role exists?  │
  │ action          │               │ - Has permission│
  │ resource_type   │               └────────┬────────┘
  │ resource_id     │                        │
  │ attributes      │               ┌────────▼────────┐
  │ - ip_address    │               │ ABAC Check      │
  │ - time_of_day   │               │ - Attribute     │
  │ - location      │               │   conditions    │
  └─────────────────┘               │ - Context rules │
                                    └────────┬────────┘
                                             │
                                    ┌────────▼────────┐
                                    │ Combined Result │
                                    │ ALLOW / DENY    │
                                    └─────────────────┘
```

### 5.3 HSM Integration

```
┌─────────────────────────────────────────────────────────────────┐
│                    HSM ARCHITECTURE                              │
└─────────────────────────────────────────────────────────────────┘

  Production Mode                    Demo Mode (--debug)
  ─────────────────                  ────────────────────
  ┌─────────────────┐               ┌─────────────────┐
  │   HSM Module    │               │    Yubikey      │
  │  (PKCS#11)      │               │   (WebAuthn)    │
  └────────┬────────┘               └────────┬────────┘
           │                                 │
           ▼                                 ▼
  ┌─────────────────┐               ┌─────────────────┐
  │ Key Operations  │               │ Challenge-Resp  │
  │ - Sign          │               │ - Touch verify  │
  │ - Verify        │               │ - Presence      │
  │ - Encrypt       │               └─────────────────┘
  └─────────────────┘

  Critical Operations Requiring Cryptographic Proof:
  ──────────────────────────────────────────────────
  - Provider-level permission changes
  - Tenant deletion
  - HSM key rotation
  - Emergency access override
  - Bulk data export
```

### 5.4 Impersonation Security

```
┌─────────────────────────────────────────────────────────────────┐
│              IMPERSONATION WORKFLOW (Temporal)                   │
└─────────────────────────────────────────────────────────────────┘

  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
  │ Request  │───▶│ Approval │───▶│Re-Auth   │───▶│ Session  │
  │ Submit   │    │(Temporal)│    │Required  │    │ Created  │
  └──────────┘    └──────────┘    └──────────┘    └──────────┘
       │               │               │               │
       ▼               ▼               ▼               ▼
  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
  │ Log      │    │ Notify   │    │ MFA/HSM  │    │ Separate │
  │ Request  │    │ Approver │    │ Verify   │    │ Audit    │
  └──────────┘    └──────────┘    └──────────┘    │ Trail    │
                                                  └──────────┘

  Session Token During Impersonation:
  ────────────────────────────────────
  {
    "sub": "impersonated_user_id",
    "tenant_id": "target_tenant_id",
    "impersonating": {
      "original_user": "admin_user_id",
      "original_tenant": "provider_tenant_id",
      "started_at": "2024-01-15T10:00:00Z",
      "expires_at": "2024-01-15T10:30:00Z",  // 30min default
      "approval_id": "approval_uuid"
    }
  }
```

---

## 6. Integration Architecture

### 6.1 Pulumi Integration

```
┌─────────────────────────────────────────────────────────────────┐
│                    PULUMI INTEGRATION                            │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                      Nimbus Backend                              │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                 Pulumi Service Layer                     │   │
│  │  ┌───────────────┐  ┌───────────────┐  ┌─────────────┐  │   │
│  │  │ Stack Manager │  │ State Manager │  │ Event Proc  │  │   │
│  │  └───────────────┘  └───────────────┘  └─────────────┘  │   │
│  └─────────────────────────────────────────────────────────┘   │
│                              │                                   │
│                              ▼                                   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              Pulumi Automation API                       │   │
│  │                                                          │   │
│  │  - LocalWorkspace / RemoteWorkspace                      │   │
│  │  - Stack.up() / Stack.preview() / Stack.destroy()        │   │
│  │  - Stack.export_stack() / Stack.import_stack()           │   │
│  │  - Stack.refresh()                                       │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Pulumi Service                              │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    Pulumi Cloud                          │   │
│  │  ┌───────────┐  ┌───────────┐  ┌───────────┐            │   │
│  │  │  State    │  │  Audit    │  │ Webhooks  │            │   │
│  │  │  Storage  │  │   Logs    │  │           │            │   │
│  │  └───────────┘  └───────────┘  └───────────┘            │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              │
          ┌──────────────┬──────────────┬──────────────┐
          ▼              ▼              ▼              ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│   Proxmox    │ │     AWS      │ │    Azure     │ │   GCP/OCI    │
│  (Phase 7)   │ │  (Phase 17)  │ │  (Phase 17)  │ │  (Phase 17)  │
└──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘


  Pulumi Event Flow:
  ──────────────────

  Pulumi Cloud ──▶ Webhook ──▶ Nimbus API ──▶ Event Processor
                                                    │
                    ┌───────────────────────────────┤
                    ▼                               ▼
              ┌──────────┐                   ┌──────────┐
              │  CMDB    │                   │  Drift   │
              │  Update  │                   │  Check   │
              └──────────┘                   └──────────┘
```

### 6.2 Cloud Provider Abstraction

```
┌─────────────────────────────────────────────────────────────────┐
│                 CLOUD PROVIDER ABSTRACTION                       │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                    Provider Interface                            │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  class CloudProviderInterface(ABC):                      │   │
│  │      @abstractmethod                                     │   │
│  │      def list_resources(self, compartment_id)            │   │
│  │      def get_resource(self, resource_id)                 │   │
│  │      def get_cost_data(self, start_date, end_date)       │   │
│  │      def map_to_semantic(self, resource) -> CIClass      │   │
│  │      def validate_credentials(self)                      │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│ ProxmoxProvider │  │  AWSProvider    │  │  AzureProvider  │
│   (Phase 7)     │  │   (Phase 17)    │  │   (Phase 17)    │
├─────────────────┤  ├─────────────────┤  ├─────────────────┤
│ - proxmoxer     │  │ - boto3 client  │  │ - azure-mgmt    │
│ - REST API      │  │ - Cost Explorer │  │ - Cost Mgmt API │
│ - Pulumi bpg    │  │ - Organizations │  │ - Graph API     │
└─────────────────┘  └─────────────────┘  └─────────────────┘
                                          + GCPProvider, OCIProvider
```

---

## 7. API Architecture

### 7.1 REST API Structure

```
┌─────────────────────────────────────────────────────────────────┐
│                    REST API ENDPOINTS                            │
└─────────────────────────────────────────────────────────────────┘

  REST is used exclusively for authentication and health.
  All data operations use GraphQL (see Section 7.2).

  Base URL: /api/v1

  Authentication:
    POST   /auth/login              # Local login
    POST   /auth/refresh            # Refresh token
    POST   /auth/logout             # Revoke session
    GET    /auth/oidc/{provider}    # OIDC initiate
    POST   /auth/oidc/callback      # OIDC callback
    POST   /auth/mfa/setup          # Setup MFA
    POST   /auth/mfa/verify         # Verify MFA

  Health:
    GET    /health                  # Overall health
    GET    /ready                   # Readiness probe
    GET    /live                    # Liveness probe

  Setup:
    GET    /setup/status            # Check if first-run complete
    POST   /setup/complete          # Complete first-run wizard
```

### 7.2 GraphQL Schema Overview

```graphql
# ─────────────────────────────────────────────────────────────────
#                    GRAPHQL SCHEMA OVERVIEW
# ─────────────────────────────────────────────────────────────────

type Query {
  # Tenant queries
  tenant(id: ID!): Tenant
  tenants(filter: TenantFilter, pagination: Pagination): TenantConnection

  # User queries
  me: User
  user(id: ID!): User
  users(filter: UserFilter, pagination: Pagination): UserConnection

  # CMDB queries
  compartment(id: ID!): Compartment
  compartments(filter: CompartmentFilter): [Compartment!]!
  resource(id: ID!): ConfigurationItem
  resources(filter: ResourceFilter, pagination: Pagination): ResourceConnection
  driftReport(tenantId: ID!, compartmentId: ID): DriftReport

  # Search
  search(query: String!, types: [SearchType!]): SearchResults

  # Audit
  auditLogs(filter: AuditFilter, pagination: Pagination): AuditLogConnection
}

type Mutation {
  # Authentication
  login(input: LoginInput!): AuthPayload
  refreshToken(refreshToken: String!): AuthPayload
  logout: Boolean

  # Tenant management
  createTenant(input: CreateTenantInput!): Tenant
  updateTenant(id: ID!, input: UpdateTenantInput!): Tenant
  deleteTenant(id: ID!): Boolean

  # CMDB operations
  importResources(input: ImportInput!): ImportJob
  acceptDrift(driftId: ID!): ConfigurationItem
  rejectDrift(driftId: ID!): ConfigurationItem

  # Workflows
  approveRequest(id: ID!, comment: String): ApprovalResult
  rejectRequest(id: ID!, reason: String!): ApprovalResult

  # Impersonation
  requestImpersonation(input: ImpersonationInput!): ImpersonationRequest
  endImpersonation: Boolean
}

type Subscription {
  # Real-time updates
  resourceChanged(tenantId: ID!): ResourceChangeEvent
  driftDetected(tenantId: ID!): DriftEvent
  approvalRequired(userId: ID!): ApprovalEvent
  auditEvent(tenantId: ID!): AuditLogEntry
  notificationReceived(userId: ID!): Notification
}
```

### 7.3 Error Response Format

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid input provided",
    "details": [
      {
        "field": "email",
        "message": "Invalid email format"
      }
    ],
    "trace_id": "abc123-def456-ghi789",
    "timestamp": "2024-01-15T10:30:00Z"
  }
}
```

---

## 8. Real-time Architecture

### 8.1 WebSocket / Socket.IO

```
┌─────────────────────────────────────────────────────────────────┐
│                    REAL-TIME ARCHITECTURE                        │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                        Clients                                   │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│  │  Angular    │  │   Mobile    │  │   CLI       │              │
│  │  (Apollo)   │  │   App       │  │   Tool      │              │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘              │
└─────────┼────────────────┼────────────────┼─────────────────────┘
          │                │                │
          └────────────────┼────────────────┘
                           │
                           ▼
          ┌────────────────────────────────┐
          │         Socket.IO Server       │
          │  ┌──────────────────────────┐ │
          │  │    Connection Manager    │ │
          │  │  - JWT Authentication    │ │
          │  │  - Tenant Room Mapping   │ │
          │  │  - Rate Limiting         │ │
          │  └──────────────────────────┘ │
          │  ┌──────────────────────────┐ │
          │  │      Room Structure      │ │
          │  │  - tenant:{tenant_id}    │ │
          │  │  - user:{user_id}        │ │
          │  │  - resource:{res_id}     │ │
          │  └──────────────────────────┘ │
          └────────────────────────────────┘
                           │
                           ▼
          ┌────────────────────────────────┐
          │         Event Handlers         │
          │  ┌────────────┐ ┌────────────┐│
          │  │ GraphQL    │ │ Custom     ││
          │  │Subscription│ │ Events     ││
          │  └────────────┘ └────────────┘│
          └────────────────────────────────┘


  Event Types:
  ────────────
  - resource.created
  - resource.updated
  - resource.deleted
  - drift.detected
  - approval.required
  - approval.completed
  - notification.new
  - impersonation.started
  - impersonation.ended
```

### 8.2 Event Publishing

```
┌─────────────────────────────────────────────────────────────────┐
│                    EVENT PUBLISHING FLOW                         │
└─────────────────────────────────────────────────────────────────┘

  Service Layer                Valkey Pub/Sub             Socket.IO
  ─────────────                ─────────────              ─────────
       │                            │                         │
       │  publish_event()           │                         │
       ├───────────────────────────▶│                         │
       │                            │  channel: events        │
       │                            ├────────────────────────▶│
       │                            │                         │
       │                            │                    broadcast
       │                            │                    to rooms
       │                            │                         │
       │                            │                         │
       │                            │◀────────────────────────┤
       │                            │  ack                    │
       │◀───────────────────────────┤                         │
       │  confirmed                 │                         │

  Event Payload:
  ──────────────
  {
    "type": "resource.updated",
    "tenant_id": "uuid",
    "data": {
      "resource_id": "uuid",
      "changes": { ... }
    },
    "timestamp": "2024-01-15T10:30:00Z",
    "trace_id": "abc123"
  }
```

---

## 9. Background Processing & Workflow Engine

Nimbus uses **Temporal** as its sole background processing and workflow engine. Temporal handles both durable multi-step workflows (approvals, deployments, impersonation) and simple recurring tasks (token cleanup, archival) via Temporal Schedules — eliminating the need for a separate task queue like Celery.

### 9.1 Temporal Workflow Engine

```
┌─────────────────────────────────────────────────────────────────┐
│                    TEMPORAL ARCHITECTURE                         │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                      FastAPI Backend                             │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                 Workflow Starters                        │   │
│  │  - Approval request submitted                            │   │
│  │  - Pulumi deploy/destroy triggered                       │   │
│  │  - Impersonation requested                               │   │
│  │  - Drift remediation initiated                           │   │
│  │  - Break-glass emergency access                          │   │
│  └─────────────────────────────────────────────────────────┘   │
└──────────────────────────────┬──────────────────────────────────┘
                               │  start_workflow()
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Temporal Server                             │
│  ┌────────────────────────┐  ┌────────────────────────┐        │
│  │   Workflow History     │  │   Task Queues          │        │
│  │  - Durable state       │  │  - nimbus-workflows    │        │
│  │  - Event sourcing      │  │  - nimbus-activities   │        │
│  │  - Replay on failure   │  │                        │        │
│  └────────────────────────┘  └────────────────────────┘        │
│  ┌────────────────────────┐  ┌────────────────────────┐        │
│  │   Visibility Store     │  │   Timer Service        │        │
│  │  - Workflow search      │  │  - Approval timeouts   │        │
│  │  - Status queries       │  │  - Session expiry      │        │
│  │  - Audit integration    │  │  - Escalation timers   │        │
│  └────────────────────────┘  └────────────────────────┘        │
│                                                                  │
│  Database: PostgreSQL (nimbus_temporal schema)                   │
└──────────────────────────────┬──────────────────────────────────┘
                               │
        ┌──────────────────────┼──────────────────────────┐
        ▼                      ▼                          ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│  Workflow Worker │  │  Workflow Worker │  │ Activity Worker │
│  (workflows)     │  │  (workflows)     │  │  (activities)   │
├─────────────────┤  ├─────────────────┤  ├─────────────────┤
│ - Approval chain│  │ - Pulumi deploy │  │ - DB operations │
│ - Impersonation │  │ - Drift remed.  │  │ - Email/notify  │
│ - Break-glass   │  │                 │  │ - Cloud API     │
│ - Concurrency:4 │  │ - Concurrency:4 │  │ - Concurrency:8 │
└─────────────────┘  └─────────────────┘  └─────────────────┘
```

#### Temporal Workflow Definitions

```
  Workflow                     Trigger                     Key Behaviors
  ─────────────────────────────────────────────────────────────────────────
  ApprovalChainWorkflow        API request for approval    Multi-step approval chain, configurable
                                                           approvers, timeout + escalation, denial
                                                           short-circuit

  PulumiDeployWorkflow         Deploy/update/destroy       Preview → approve → execute → verify,
                               request                     rollback on failure (saga pattern),
                                                           progress events via Signal

  ImpersonationWorkflow        Impersonation request       Request → approve → re-auth → session,
                                                           auto-revoke on timer expiry (default 30m)

  BreakGlassWorkflow           Emergency access request    Multi-approval (configurable count),
                                                           HSM verification (Phase 14), time-limited,
                                                           full audit trail at each step

  DriftRemediationWorkflow     Drift detected (manual or   Detect → notify → approve → remediate,
                               scheduled)                   supports auto-approve for low severity
```

#### Temporal Activities (Reusable Steps)

```
  Activity                     Used By                     Description
  ─────────────────────────────────────────────────────────────────────────
  send_approval_request        Approval, BreakGlass,       Create approval record, notify approver
                               Impersonation
  check_approval_status        Approval, BreakGlass        Poll/signal for approval decision
  send_notification            All workflows               Send email/webhook/in-app notification
  execute_pulumi_operation     PulumiDeploy                Run Pulumi up/destroy/refresh
  record_audit_event           All workflows               Write audit log entry
  revoke_session               Impersonation               Invalidate impersonation session
  verify_hsm                   BreakGlass (Phase 14)       HSM/Yubikey cryptographic verification
```

#### Temporal Signals and Queries

```python
# Signals allow external input into running workflows
@workflow.signal
async def approval_decision(self, decision: ApprovalDecision):
    """Approver submits approve/reject decision."""

@workflow.signal
async def extend_session(self, minutes: int):
    """Extend an impersonation session."""

# Queries allow reading workflow state without side effects
@workflow.query
def get_approval_status(self) -> ApprovalStatus:
    """Get current approval chain status (who approved, who pending)."""

@workflow.query
def get_deployment_progress(self) -> DeploymentProgress:
    """Get Pulumi operation progress (resources created/updated/deleted)."""
```

### 9.2 Temporal Schedules (Recurring Tasks)

Temporal Schedules replace the need for a separate cron/scheduler system. Each schedule triggers a lightweight workflow (typically a single activity) on a defined interval.

```
┌─────────────────────────────────────────────────────────────────┐
│                    TEMPORAL SCHEDULES                            │
└─────────────────────────────────────────────────────────────────┘

  Temporal Server manages all schedules natively.
  Schedules are created/updated via the Temporal Schedule API.

  Schedule                  Cron Expression       Workflow Triggered
  ─────────────────────────────────────────────────────────────────
  drift-scan-all            0 2 * * * (daily 2AM) DriftRemediationWorkflow (per tenant)
  state-export              0 * * * * (hourly)    StateExportWorkflow
  cleanup-expired-tokens    */15 * * * * (15min)  TokenCleanupWorkflow
  audit-log-archive         0 3 * * * (daily 3AM) AuditArchiveWorkflow
  cost-data-sync            0 */6 * * * (6hr)     CostSyncWorkflow
  notification-digest       0 8 * * * (daily 8AM) NotificationDigestWorkflow


  Tenant-Specific Scheduling:
  ───────────────────────────
  Each tenant can configure custom schedules stored in DB.
  Backend creates/updates Temporal Schedules via the Schedule API.

  ┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
  │  Tenant Config  │────▶│   Backend API   │────▶│Temporal Schedule │
  │  (scan: hourly) │     │  (Schedule API) │     │   (managed)     │
  └─────────────────┘     └─────────────────┘     └─────────────────┘

  Benefits over separate scheduler:
  - All schedules visible in Temporal UI
  - Failed runs automatically retried
  - Execution history preserved
  - Pause/resume without redeployment
  - No additional infrastructure (no Celery, no Valkey broker)
```

---

## 10. Deployment Architecture

### 10.1 Container Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    CONTAINER ARCHITECTURE                        │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                    Docker Compose (Development)                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│  │   backend   │  │  frontend   │  │temporal-wkr │              │
│  │  (FastAPI)  │  │  (Angular)  │  │  (Workers)  │              │
│  │  Port:8000  │  │  Port:4200  │  │             │              │
│  └─────────────┘  └─────────────┘  └─────────────┘              │
│                                                                  │
│  ┌─────────────┐  ┌─────────────┐                               │
│  │  temporal   │  │temporal-ui  │                               │
│  │  (Server)   │  │  Port:8233  │                               │
│  │  Port:7233  │  │             │                               │
│  └─────────────┘  └─────────────┘                               │
│                                                                  │
│  ┌─────────────┐  ┌─────────────┐                               │
│  │  postgres   │  │    minio    │  Phase 1+                     │
│  │  Port:5432  │  │ Port:9000/1 │                               │
│  └─────────────┘  └─────────────┘                               │
│                                                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│  │   valkey    │  │    loki     │  │   grafana   │  Phase 12+   │
│  │  Port:6379  │  │  Port:3100  │  │  Port:3000  │  (deferred)  │
│  └─────────────┘  └─────────────┘  └─────────────┘              │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 10.2 Production Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    PRODUCTION ARCHITECTURE                       │
└─────────────────────────────────────────────────────────────────┘

                    ┌─────────────────┐
                    │   DNS / CDN     │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │  Load Balancer  │
                    │  (L7 / HTTPS)   │
                    └────────┬────────┘
                             │
         ┌───────────────────┼───────────────────┐
         ▼                   ▼                   ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│  Backend Pod 1  │ │  Backend Pod 2  │ │  Backend Pod N  │
│  - FastAPI      │ │  - FastAPI      │ │  - FastAPI      │
│  - Gunicorn     │ │  - Gunicorn     │ │  - Gunicorn     │
└─────────────────┘ └─────────────────┘ └─────────────────┘
         │                   │                   │
         └───────────────────┼───────────────────┘
                             │
┌────────────────────────────┼────────────────────────────┐
│                      Internal Network                    │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐     │
│  │ PostgreSQL  │  │   Valkey    │  │   MinIO     │     │
│  │  Primary    │  │  Cluster    │  │  Cluster    │     │
│  │     +       │  │             │  │             │     │
│  │  Standby    │  │             │  │             │     │
│  └─────────────┘  └─────────────┘  └─────────────┘     │
│                                                         │
│  ┌─────────────┐  ┌─────────────┐                      │
│  │  Temporal   │  │  Temporal   │                      │
│  │   Server    │  │  Workers    │                      │
│  └─────────────┘  └─────────────┘                      │
└─────────────────────────────────────────────────────────┘

  Static Assets (Frontend):
  ─────────────────────────
  ┌─────────────┐     ┌─────────────┐
  │   CDN       │◀────│  S3/MinIO   │
  │  (cached)   │     │  (origin)   │
  └─────────────┘     └─────────────┘
```

### 10.3 Kubernetes Deployment (Future)

```yaml
# Deployment structure for K8s reference
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nimbus-backend
spec:
  replicas: 3
  template:
    spec:
      containers:
      - name: backend
        image: nimbus/backend:latest
        ports:
        - containerPort: 8000
        livenessProbe:
          httpGet:
            path: /live
            port: 8000
        readinessProbe:
          httpGet:
            path: /ready
            port: 8000
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "1Gi"
            cpu: "1000m"
```

---

## 11. Monitoring & Observability

### 11.1 Metrics Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    METRICS ARCHITECTURE                          │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                      Application                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              Prometheus Metrics Exporter                 │   │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐        │   │
│  │  │ HTTP Metrics│ │ DB Metrics  │ │Custom Metric│        │   │
│  │  │ - latency   │ │ - pool size │ │ - tenants   │        │   │
│  │  │ - requests  │ │ - queries   │ │ - resources │        │   │
│  │  │ - errors    │ │ - latency   │ │ - drift     │        │   │
│  │  └─────────────┘ └─────────────┘ └─────────────┘        │   │
│  └─────────────────────────────────────────────────────────┘   │
│                              │                                   │
│                    /metrics endpoint                             │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               ▼
              ┌────────────────────────────────┐
              │         Prometheus             │
              │  ┌──────────────────────────┐ │
              │  │      Scrape Config       │ │
              │  │  - nimbus-backend:8000   │ │
              │  │  - temporal-server:7233  │ │
              │  │  - valkey:9121            │ │
              │  │  - postgres:9187         │ │
              │  └──────────────────────────┘ │
              └────────────────┬───────────────┘
                               │
               ┌───────────────┼───────────────┐
               ▼               ▼               ▼
        ┌────────────┐  ┌────────────┐  ┌────────────┐
        │  Grafana   │  │ Alerting   │  │ Pushgateway│
        │ Dashboards │  │  Rules     │  │ (optional) │
        └────────────┘  └────────────┘  └────────────┘


  Key Metrics:
  ────────────
  - nimbus_http_requests_total{method, path, status}
  - nimbus_http_request_duration_seconds{method, path}
  - nimbus_active_tenants
  - nimbus_resources_total{provider, type}
  - nimbus_drift_detected_total{tenant_id, severity}
  - nimbus_audit_events_total{action, resource_type}
  - nimbus_temporal_workflows_total{workflow_type, status}
  - nimbus_temporal_workflow_duration_seconds{workflow_type}
  - nimbus_temporal_activities_total{activity_type, status}
  - nimbus_temporal_schedules_total{schedule_name, status}
```

### 11.2 Logging Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    LOGGING ARCHITECTURE                          │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                      Application Logs                            │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              Structured Logging (JSON)                   │   │
│  │  {                                                       │   │
│  │    "timestamp": "2024-01-15T10:30:00Z",                 │   │
│  │    "level": "INFO",                                      │   │
│  │    "logger": "nimbus.api.cmdb",                         │   │
│  │    "message": "Resource created",                        │   │
│  │    "trace_id": "abc123-def456",                         │   │
│  │    "tenant_id": "tenant_uuid",                          │   │
│  │    "user_id": "user_uuid",                              │   │
│  │    "resource_id": "resource_uuid",                      │   │
│  │    "duration_ms": 45                                     │   │
│  │  }                                                       │   │
│  └─────────────────────────────────────────────────────────┘   │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               ▼ stdout/stderr
              ┌────────────────────────────────┐
              │      Docker / Container        │
              │         Log Driver             │
              └────────────────┬───────────────┘
                               │
                               ▼
              ┌────────────────────────────────┐
              │         Promtail               │
              │  (Loki log collector)          │
              └────────────────┬───────────────┘
                               │
                               ▼
              ┌────────────────────────────────┐
              │           Loki                 │
              │  ┌──────────────────────────┐ │
              │  │     Log Storage          │ │
              │  │  - Label indexing        │ │
              │  │  - Chunk storage         │ │
              │  │  - Retention policies    │ │
              │  └──────────────────────────┘ │
              └────────────────┬───────────────┘
                               │
                               ▼
              ┌────────────────────────────────┐
              │         Grafana                │
              │   Log exploration & queries    │
              └────────────────────────────────┘
```

### 11.3 Alerting Configuration

```
┌─────────────────────────────────────────────────────────────────┐
│                    ALERTING FLOW                                 │
└─────────────────────────────────────────────────────────────────┘

  Prometheus Rules          Alert Manager           Destinations
  ─────────────────         ─────────────           ────────────
       │                         │                       │
       │  alert: HighErrorRate   │                       │
       ├────────────────────────▶│                       │
       │                         │  route by severity    │
       │                         ├──────────────────────▶│ PagerDuty
       │                         │                       │ (critical)
       │                         │                       │
       │                         ├──────────────────────▶│ Email
       │                         │                       │ (warning)
       │                         │                       │
       │  alert: DriftDetected   │                       │
       ├────────────────────────▶│                       │
       │                         │  (if configured)      │
       │                         ├──────────────────────▶│ Webhook
       │                         │                       │


  Alert Rules (examples):
  ───────────────────────
  - HighErrorRate: error_rate > 5% for 5 minutes
  - HighLatency: p99_latency > 2s for 5 minutes
  - DatabaseConnectionPool: available < 10% for 2 minutes
  - TemporalWorkflowTimeout: workflow_duration > SLA threshold
  - TemporalWorkerDown: temporal_worker_count < expected for 2 minutes
  - TemporalScheduleMissed: scheduled run did not start within expected window
  - DriftDetected: new_drift_count > 0 (tenant-configurable)
```

---

## 12. Disaster Recovery

### 12.1 Backup Strategy

```
┌─────────────────────────────────────────────────────────────────┐
│                    BACKUP STRATEGY                               │
└─────────────────────────────────────────────────────────────────┘

  Component         Backup Method           Frequency    Retention
  ─────────────────────────────────────────────────────────────────
  PostgreSQL        WAL Streaming +         Continuous   30 days
                    Daily full backup       Daily

  Valkey            RDB Snapshots           Hourly       7 days
                    AOF Persistence         Continuous

  MinIO             Cross-region            Continuous   90 days
                    replication

  Pulumi State      Pulumi Service          Automatic    Unlimited
                    (managed backup)

  Configuration     Git repository          On change    Unlimited


┌─────────────────────────────────────────────────────────────────┐
│                    BACKUP ARCHITECTURE                           │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   PostgreSQL    │────▶│  WAL Archiver   │────▶│   S3 Bucket     │
│    Primary      │     │                 │     │   (Backups)     │
└─────────────────┘     └─────────────────┘     └─────────────────┘
        │
        │ Streaming
        │ Replication
        ▼
┌─────────────────┐
│   PostgreSQL    │
│    Standby      │
└─────────────────┘
```

### 12.2 Recovery Procedures

```
┌─────────────────────────────────────────────────────────────────┐
│                    RECOVERY PROCEDURES                           │
└─────────────────────────────────────────────────────────────────┘

  Scenario: Primary Database Failure
  ───────────────────────────────────

  1. Automatic Detection
     └── Health check fails (< 30 seconds)

  2. Automatic Failover
     └── Standby promoted to primary (< 60 seconds)

  3. Service Recovery
     └── Application reconnects to new primary

  4. Manual Steps (post-incident)
     └── Provision new standby
     └── Investigate root cause


  Scenario: Complete Region Failure
  ──────────────────────────────────

  1. DNS Failover
     └── Route traffic to secondary region

  2. Database Recovery
     └── Restore from S3 backups
     └── Apply WAL logs to point-in-time

  3. Service Startup
     └── Start application containers
     └── Verify data integrity

  4. Client Notification
     └── Update status page
     └── Send incident notification


  RTO/RPO Targets:
  ────────────────
  - RPO (Recovery Point Objective): 0 (zero data loss)
    Achieved via: Synchronous replication to standby

  - RTO (Recovery Time Objective): 0 (zero downtime)
    Achieved via: Automatic failover to standby
```

---

## Appendix A: Configuration Reference

### A.1 Environment Variables

```bash
# Application
NIMBUS_ENV=production|development
NIMBUS_DEBUG=false
NIMBUS_SECRET_KEY=<random-secret>

# Database
NIMBUS_DB_HOST=localhost
NIMBUS_DB_PORT=5432
NIMBUS_DB_NAME=nimbus
NIMBUS_DB_USER=nimbus
NIMBUS_DB_PASSWORD=<password>
NIMBUS_DB_POOL_SIZE=20

# Valkey
NIMBUS_VALKEY_URL=valkey://localhost:6379/0

# MinIO/S3
NIMBUS_S3_ENDPOINT=http://localhost:9000
NIMBUS_S3_ACCESS_KEY=<access-key>
NIMBUS_S3_SECRET_KEY=<secret-key>
NIMBUS_S3_BUCKET=nimbus

# Authentication
NIMBUS_JWT_SECRET=<jwt-secret>
NIMBUS_JWT_EXPIRY=3600
NIMBUS_REFRESH_TOKEN_EXPIRY=604800

# Pulumi
PULUMI_ACCESS_TOKEN=<pulumi-token>

# Temporal
NIMBUS_TEMPORAL_HOST=localhost
NIMBUS_TEMPORAL_PORT=7233
NIMBUS_TEMPORAL_NAMESPACE=nimbus
NIMBUS_TEMPORAL_TASK_QUEUE=nimbus-workflows

# Email
NIMBUS_SMTP_HOST=smtp.example.com
NIMBUS_SMTP_PORT=587
NIMBUS_SMTP_USER=<user>
NIMBUS_SMTP_PASSWORD=<password>
```

### A.2 YAML Configuration

```yaml
# config/nimbus.yaml
app:
  name: Nimbus
  version: 1.0.0

logging:
  level: INFO
  format: json  # or: plain

rate_limiting:
  enabled: true
  default_limit: 100/minute

tenancy:
  isolation: schema_with_rls  # hardcoded, not configurable

drift_detection:
  default_schedule: "0 2 * * *"  # Daily at 2 AM

notifications:
  email:
    enabled: true
    provider: smtp  # or: ses, sendgrid
  webhooks:
    enabled: true
    timeout: 30
```

---

## Appendix B: Glossary

| Term | Definition |
|------|------------|
| CI | Configuration Item - a resource tracked in the CMDB |
| CMDB | Configuration Management Database |
| Compartment | Logical grouping of resources (similar to Resource Group/Project) |
| Drift | Difference between desired state (Pulumi) and actual state (cloud) |
| HSM | Hardware Security Module |
| Impersonation | Acting on behalf of another user with proper authorization |
| Provider | Top-level entity managing the Nimbus installation |
| RLS | Row-Level Security |
| Semantic Layer | Abstraction mapping cloud resources to business concepts |
| Temporal | Durable workflow engine for long-running, stateful processes |
| Temporal Activity | A single step in a workflow (e.g., send email, call API) |
| Temporal Signal | External input sent to a running workflow (e.g., approval decision) |
| Temporal Query | Read-only inspection of a running workflow's state |
| Tenant | A customer organization using the platform |
| URN | Uniform Resource Name (Pulumi resource identifier) |

---

## Document Information

- **Version**: 1.0.0
- **Last Updated**: 2024-01-15
- **Authors**: Architecture Team
- **Status**: Draft

---

*This is a living document. Update when architecture decisions change.*
