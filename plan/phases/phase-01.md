# Phase 1: Project Foundation & Local Auth

## Status
- [x] Refinement complete
- [ ] Implementation in progress
- [ ] Implementation complete
- [ ] Phase review complete

## Goal
Establish project structure, build system, Docker infrastructure, and basic local authentication with JWT token management.

## Deliverables
- Backend project scaffolding (FastAPI + SQLAlchemy async + Strawberry GraphQL)
- Frontend project scaffolding (Angular 17+ standalone components)
- Docker Compose for local infrastructure (PostgreSQL, MinIO, Temporal Server + UI)
- PowerShell build script with migration support
- Local username/password authentication (REST API)
- JWT token management (access + refresh, configurable expiry)
- Configurable session management (concurrent session limits)
- First-run setup wizard (admin + org config)
- Temporal setup for workflows and scheduled tasks

---

## Refinement Questions & Decisions

### Q1: Python Package Manager
**Question**: What package manager for Python dependencies?
**Decision**: uv
**Rationale**: Modern, fast, with lockfile support. Better DX than pip-tools.

### Q2: Initial User Creation
**Question**: How should the first admin user be created?
**Decision**: First-run wizard (web UI)
**Rationale**: User-friendly, professional UX, allows collecting org setup info.

### Q3: Password Complexity
**Question**: Implement password complexity rules in Phase 1?
**Decision**: Defer - accept any password
**Rationale**: Reduces Phase 1 scope. Add configurable password policy in later phase.

### Q4: Session Management
**Question**: Single or multiple concurrent sessions?
**Decision**: Configurable
**Rationale**: Enterprise flexibility. Default to allowing multiple sessions with configurable limit.

### Q5: Token Expiry
**Question**: JWT token expiry times?
**Decision**: Configurable with defaults: Access 1 hour, Refresh 7 days
**Rationale**: Balance between security and UX. Config allows tenant customization later.

### Q6: Auth API Style
**Question**: REST or GraphQL for authentication?
**Decision**: REST for auth, GraphQL for data
**Rationale**: Auth is simpler with REST. GraphQL for complex data queries.

### Q7: Database Migrations
**Question**: When to run migrations?
**Decision**: PowerShell build script handles migrations
**Rationale**: Explicit control, works in CI, no auto-migration surprises.

### Q8: Temporal Setup
**Question**: Set up Temporal in Phase 1?
**Decision**: Yes - Temporal Server in Docker Compose, SDK scaffold, worker entrypoint
**Rationale**: Foundation for all workflows and scheduled tasks. Replaces Celery entirely.

### Q9: GraphQL in Phase 1
**Question**: Include GraphQL setup even though auth uses REST?
**Decision**: Yes - scaffold with health query
**Rationale**: Establishes pattern early, ready for Phase 2 data queries.

### Q10: First-run Wizard Scope
**Question**: What should the wizard collect?
**Decision**: Extended - Admin credentials + organization name + tenant isolation config
**Rationale**: Sets up provider properly from the start.

---

## Tasks

### Infrastructure Tasks

#### Task 1.1: Docker Compose Setup
**Complexity**: M
**Description**: Create Docker Compose configuration for local development infrastructure.
**Files**:
- `docker-compose.yml` - Main compose file
- `docker/postgres/init.sql` - Initial database setup (nimbus + nimbus_temporal databases)
**Acceptance Criteria**:
- [ ] PostgreSQL container with nimbus and nimbus_temporal databases created
- [ ] MinIO container with nimbus bucket
- [ ] Temporal Server + Temporal UI containers running
- [ ] All services accessible on documented ports
- [ ] Persistent volumes for data
- [ ] Structured logging to stdout (viewable via `docker-compose logs`)

**Note**: Redis (needed for caching/Socket.IO) deferred to Phase 4. Loki + Grafana deferred to Phase 18.
**Tests**:
- [ ] `docker-compose up` starts all services
- [ ] Services health checks pass

---

#### Task 1.2: PowerShell Build Script
**Complexity**: M
**Description**: Create PowerShell build script that orchestrates the entire build process.
**Files**:
- `build.ps1` - Main build script
**Acceptance Criteria**:
- [ ] Validates prerequisites (Python 3.12+, Node.js 20, Docker)
- [ ] Starts Docker Compose infrastructure
- [ ] Installs Python dependencies (uv)
- [ ] Installs Node dependencies (npm)
- [ ] Runs Alembic migrations
- [ ] Builds frontend (optional flag)
- [ ] Works in CI mode (non-interactive)
**Tests**:
- [ ] Script runs successfully on clean checkout
- [ ] Script is idempotent (can run multiple times)

---

### Backend Tasks

#### Task 1.3: Backend Project Scaffolding
**Complexity**: L
**Description**: Set up FastAPI project structure with async SQLAlchemy.
**Files**:
- `backend/pyproject.toml` - Project config with uv
- `backend/uv.lock` - Dependency lockfile
- `backend/app/__init__.py`
- `backend/app/main.py` - FastAPI application entry
- `backend/app/core/config.py` - Configuration management (env vars + YAML)
- `backend/app/core/middleware.py` - Trace ID injection middleware
- `backend/app/db/session.py` - Async SQLAlchemy session
- `backend/app/db/base.py` - Base model class
- `backend/alembic.ini` - Alembic config
- `backend/alembic/env.py` - Migration environment
**Acceptance Criteria**:
- [ ] `uv run uvicorn app.main:app` starts server on port 8000
- [ ] `/health`, `/ready`, `/live` endpoints respond
- [ ] Configuration loaded from env vars and YAML
- [ ] Trace ID middleware adds X-Trace-ID to responses
- [ ] Database connection pool configured
- [ ] File header documentation standard followed
**Tests**:
- [ ] Health endpoints return 200
- [ ] Configuration loading test
- [ ] Trace ID present in responses

---

#### Task 1.4: Core Data Models
**Complexity**: M
**Description**: Create foundational SQLAlchemy models for auth system.
**Files**:
- `backend/app/models/base.py` - TimestampMixin, SoftDeleteMixin
- `backend/app/models/provider.py` - Provider model
- `backend/app/models/user.py` - User model
- `backend/app/models/session.py` - Session model
- `backend/app/models/system_config.py` - System configuration model
- `backend/alembic/versions/001_initial.py` - Initial migration
**Acceptance Criteria**:
- [ ] Provider model with id, name, timestamps
- [ ] User model with id, email, password_hash, provider_id, timestamps, soft delete
- [ ] Session model with id, user_id, token_hash, refresh_token, expires_at, ip, user_agent, revoked_at
- [ ] SystemConfig for setup wizard state and global settings
- [ ] All models have created_at, updated_at
- [ ] Soft delete support via deleted_at
- [ ] Migration runs successfully
**Tests**:
- [ ] Models can be created and queried
- [ ] Soft delete filters correctly

---

#### Task 1.5: Authentication Service
**Complexity**: L
**Description**: Implement local authentication with JWT tokens.
**Files**:
- `backend/app/services/auth/__init__.py`
- `backend/app/services/auth/service.py` - Auth service
- `backend/app/services/auth/jwt.py` - JWT token handling
- `backend/app/services/auth/password.py` - Password hashing (argon2)
- `backend/app/schemas/auth.py` - Pydantic schemas for auth
**Acceptance Criteria**:
- [ ] Password hashing with argon2
- [ ] JWT access token generation with configurable expiry
- [ ] JWT refresh token generation with configurable expiry
- [ ] Token validation and decoding
- [ ] Session creation and tracking
- [ ] Session revocation
- [ ] Concurrent session limit enforcement (configurable)
- [ ] Token contains: sub, provider_id, jti, exp, iat
**Tests**:
- [ ] Password hashing and verification
- [ ] Token generation and validation
- [ ] Expired token rejection
- [ ] Session limit enforcement

---

#### Task 1.6: Auth REST Endpoints
**Complexity**: M
**Description**: Create REST API endpoints for authentication.
**Files**:
- `backend/app/api/v1/router.py` - API v1 router
- `backend/app/api/v1/endpoints/auth.py` - Auth endpoints
- `backend/app/api/deps.py` - Dependency injection (get_current_user, etc.)
**Acceptance Criteria**:
- [ ] `POST /api/v1/auth/login` - Login with email/password
- [ ] `POST /api/v1/auth/refresh` - Refresh access token
- [ ] `POST /api/v1/auth/logout` - Revoke current session
- [ ] `GET /api/v1/auth/me` - Get current user info
- [ ] `GET /api/v1/auth/sessions` - List user's active sessions
- [ ] `DELETE /api/v1/auth/sessions/{id}` - Revoke specific session
- [ ] Proper error responses with trace_id
- [ ] Rate limiting on login endpoint
**Tests**:
- [ ] Successful login returns tokens
- [ ] Invalid credentials return 401
- [ ] Refresh token flow works
- [ ] Logout revokes session
- [ ] Protected endpoint requires valid token

---

#### Task 1.7: First-Run Setup Wizard API
**Complexity**: M
**Description**: Backend API for first-run setup wizard.
**Files**:
- `backend/app/api/v1/endpoints/setup.py` - Setup wizard endpoints
- `backend/app/services/setup/__init__.py`
- `backend/app/services/setup/service.py` - Setup service
- `backend/app/schemas/setup.py` - Setup schemas
**Acceptance Criteria**:
- [ ] `GET /api/v1/setup/status` - Check if setup is complete
- [ ] `POST /api/v1/setup/initialize` - Complete setup wizard
- [ ] Setup accepts: admin email, admin password, organization name
- [ ] Creates provider record
- [ ] Creates admin user
- [ ] Marks setup as complete (prevents re-running)
- [ ] Returns initial tokens for admin
**Tests**:
- [ ] Setup status returns false initially
- [ ] Setup creates provider and admin
- [ ] Setup cannot be run twice
- [ ] Admin can login after setup

---

#### Task 1.8: GraphQL Scaffold
**Complexity**: S
**Description**: Set up Strawberry GraphQL with basic health query.
**Files**:
- `backend/app/api/graphql/__init__.py`
- `backend/app/api/graphql/schema.py` - Root schema
- `backend/app/api/graphql/queries/__init__.py`
- `backend/app/api/graphql/queries/health.py` - Health query
**Acceptance Criteria**:
- [ ] GraphQL endpoint at `/graphql`
- [ ] GraphiQL UI available in development
- [ ] `query { health }` returns "ok"
- [ ] `query { version }` returns app version
- [ ] Authentication context available for future use
**Tests**:
- [ ] Health query returns expected value
- [ ] GraphQL endpoint accessible

---

#### Task 1.9: Temporal Setup
**Complexity**: L
**Description**: Set up Temporal as the sole workflow engine and task scheduler. Temporal Server runs in Docker Compose. The Python Temporal worker handles all background work: durable multi-step workflows (approvals, deployments, impersonation) and recurring scheduled tasks (token cleanup, archival) via Temporal Schedules. No Celery needed.
**Files**:
- `docker-compose.yml` - Add Temporal Server, Temporal UI, and Temporal worker services
- `docker/postgres/init.sql` - Add `nimbus_temporal` database creation
- `backend/app/core/temporal.py` - Temporal client factory (connection to Temporal Server)
- `backend/app/workflows/__init__.py` - Workflow package init
- `backend/app/workflows/worker.py` - Temporal worker entrypoint
- `backend/app/workflows/activities/__init__.py` - Activities package
- `backend/app/workflows/activities/example.py` - Example activity (for testing)
- `backend/app/workflows/example.py` - Example workflow (for testing)
**Acceptance Criteria**:
- [ ] Temporal Server running in Docker Compose (using official `temporalio/auto-setup` image)
- [ ] Temporal UI accessible at port 8233
- [ ] Temporal uses same PostgreSQL instance (separate `nimbus_temporal` database)
- [ ] `temporalio` Python SDK added to pyproject.toml
- [ ] Temporal client factory creates async client with configurable host/port/namespace
- [ ] Temporal worker starts and polls `nimbus-workflows` task queue
- [ ] Example workflow (with one activity) can be started and completes successfully
- [ ] Example Temporal Schedule can be created and triggers workflow on interval
- [ ] Worker startup command documented
**Tests**:
- [ ] Temporal client connects to server
- [ ] Example workflow can be started via client
- [ ] Example activity executes and returns result
- [ ] Schedule triggers workflow on defined interval
- [ ] Worker shuts down gracefully

---

### Frontend Tasks

#### Task 1.10: Frontend Project Scaffolding
**Complexity**: L
**Description**: Set up Angular 17+ project with standalone components.
**Files**:
- `frontend/package.json` - Dependencies
- `frontend/angular.json` - Angular config (hash-based routing)
- `frontend/tsconfig.json` - TypeScript config
- `frontend/src/main.ts` - Bootstrap
- `frontend/src/app/app.component.ts` - Root component
- `frontend/src/app/app.routes.ts` - Route definitions
- `frontend/src/environments/` - Environment configs
- `frontend/.eslintrc.json` - ESLint config
- `frontend/.prettierrc` - Prettier config
**Acceptance Criteria**:
- [ ] `npm start` serves app on port 4200
- [ ] Hash-based routing (`/#/`)
- [ ] Taiga UI installed and configured
- [ ] Apollo Angular installed and configured
- [ ] Environment-based API URL configuration
- [ ] ESLint + Prettier configured
**Tests**:
- [ ] App compiles without errors
- [ ] Lint passes

---

#### Task 1.11: Core Auth Service (Frontend)
**Complexity**: M
**Description**: Angular service for authentication state management.
**Files**:
- `frontend/src/app/core/auth/auth.service.ts` - Auth service with signals
- `frontend/src/app/core/auth/auth.interceptor.ts` - HTTP interceptor for tokens
- `frontend/src/app/core/auth/auth.guard.ts` - Route guard
- `frontend/src/app/core/auth/auth.models.ts` - Auth types
- `frontend/src/app/core/services/api.service.ts` - Base API service
**Acceptance Criteria**:
- [ ] Login method calls REST API
- [ ] Tokens stored in localStorage
- [ ] Automatic token refresh before expiry
- [ ] Auth state as signals (isAuthenticated, currentUser)
- [ ] HTTP interceptor attaches Authorization header
- [ ] Route guard redirects unauthenticated users
**Tests**:
- [ ] Login updates auth state
- [ ] Interceptor adds token
- [ ] Guard blocks unauthenticated access

---

#### Task 1.12: Login Page
**Complexity**: M
**Description**: Login page using Taiga UI components.
**Files**:
- `frontend/src/app/features/auth/login/login.component.ts`
- `frontend/src/app/features/auth/login/login.component.html`
- `frontend/src/app/features/auth/login/login.component.scss`
**Acceptance Criteria**:
- [ ] Email and password fields
- [ ] Form validation (required fields)
- [ ] Error message display
- [ ] Loading state during login
- [ ] Redirect to dashboard on success
- [ ] Redirect to setup wizard if not initialized
- [ ] Taiga UI components used
**Tests**:
- [ ] Form validation works
- [ ] Submit calls auth service

---

#### Task 1.13: First-Run Setup Wizard (Frontend)
**Complexity**: L
**Description**: Multi-step setup wizard for initial configuration.
**Files**:
- `frontend/src/app/features/setup/setup.component.ts` - Wizard container
- `frontend/src/app/features/setup/steps/welcome/welcome.component.ts`
- `frontend/src/app/features/setup/steps/admin/admin.component.ts`
- `frontend/src/app/features/setup/steps/organization/organization.component.ts`
- `frontend/src/app/features/setup/steps/complete/complete.component.ts`
- `frontend/src/app/features/setup/setup.service.ts`
**Acceptance Criteria**:
- [ ] Step 1: Welcome message, explains what Nimbus is
- [ ] Step 2: Admin account (email, password, confirm password)
- [ ] Step 3: Organization/Provider name
- [ ] Step 4: Completion confirmation
- [ ] Isolation strategy hardcoded to Schema per Tenant + RLS (no user choice)
- [ ] Progress indicator
- [ ] Back/Next navigation
- [ ] Submit on final step
- [ ] Auto-login after completion
**Tests**:
- [ ] Navigation between steps works
- [ ] Form validation per step
- [ ] Submit sends correct data

---

#### Task 1.14: Basic Dashboard Shell
**Complexity**: S
**Description**: Minimal dashboard layout for authenticated users.
**Files**:
- `frontend/src/app/features/dashboard/dashboard.component.ts`
- `frontend/src/app/features/dashboard/dashboard.component.html`
- `frontend/src/app/shared/components/layout/layout.component.ts`
- `frontend/src/app/shared/components/header/header.component.ts`
**Acceptance Criteria**:
- [ ] Header with app name and user menu
- [ ] User menu with logout option
- [ ] Sidebar placeholder (empty for now)
- [ ] Main content area
- [ ] Welcome message with user email
**Tests**:
- [ ] Logout calls auth service
- [ ] User email displayed

---

---

## Phase Completion Checklist

- [ ] All 14 tasks completed
- [ ] File headers follow documentation standards (4-part: Overview, Architecture, Dependencies, Concepts)
- [ ] All backend tests pass (pytest)
- [ ] All frontend tests pass (Jest)
- [ ] Ruff linting passes
- [ ] ESLint + Prettier pass
- [ ] API documentation auto-generated (OpenAPI)
- [ ] Local dev environment tested end-to-end:
  - [ ] `build.ps1` runs successfully
  - [ ] Docker services start
  - [ ] Backend starts
  - [ ] Frontend starts
  - [ ] Setup wizard completes
  - [ ] Login works
  - [ ] Dashboard displays

## Dependencies for Next Phase
Phase 2 (Multi-Tenancy Foundation) will build on:
- Provider model created in this phase
- Auth middleware and user context
- Database session management
- GraphQL scaffold

## Notes & Learnings
[To be filled during implementation]
