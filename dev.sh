#!/usr/bin/env bash
# Overview: Builds and starts all Nimbus services in parallel.
# Architecture: Local development orchestrator (Section 10)
# Dependencies: bash, docker, uv, npm, node
# Concepts: Local development, parallel startup
#
# Usage: ./dev.sh          (build + start all)
#        ./dev.sh --skip-build  (start only, skip install/migrations)

set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
SKIP_BUILD=false
[[ "${1:-}" == "--skip-build" ]] && SKIP_BUILD=true

# Colors
C='\033[0;36m'; G='\033[0;32m'; R='\033[0;31m'; Y='\033[0;33m'; NC='\033[0m'
step()  { echo -e "\n${C}==> $1${NC}"; }
ok()    { echo -e "  ${G}$1${NC}"; }
fail()  { echo -e "  ${R}$1${NC}"; exit 1; }
info()  { echo -e "  ${Y}$1${NC}"; }

# Cleanup on exit — kill by command pattern so nothing survives
PIDS=()
cleanup() {
    trap '' INT TERM EXIT  # Prevent re-entrancy
    echo -e "\n${Y}Shutting down...${NC}"
    # Kill tracked PIDs and their process trees
    for pid in "${PIDS[@]}"; do
        pkill -9 -P "$pid" 2>/dev/null || true
        kill -9 "$pid" 2>/dev/null || true
    done
    # Belt-and-suspenders: kill by command pattern to catch orphans
    pkill -9 -f "ng serve.*--port 4200" 2>/dev/null || true
    pkill -9 -f "uvicorn.*app\.main" 2>/dev/null || true
    pkill -9 -f "app\.workflows\.worker" 2>/dev/null || true
    wait 2>/dev/null
    echo -e "${G}All services stopped.${NC}"
}
trap cleanup EXIT INT TERM

# ── Kill stale processes from previous run ───────────────────────
step "Killing stale processes from previous run"
stale_killed=false

# Kill by command pattern — works reliably on all Linux/WSL2
# (port-based methods like fuser/lsof/ss are unreliable on WSL2)
for pattern in "ng serve.*--port 4200" "uvicorn.*app\.main" "app\.workflows\.worker"; do
    if pkill -9 -f "$pattern" 2>/dev/null; then
        info "Killed: $pattern"
        stale_killed=true
    fi
done

if [[ "$stale_killed" == true ]]; then
    sleep 1  # Let OS release ports
else
    ok "No stale processes found"
fi

# Verify ports are actually free
for port in 4200 8000; do
    if ss -tln 2>/dev/null | grep -q ":${port} "; then
        info "Port $port still held — force-killing all node/python on it"
        fuser -k "${port}/tcp" 2>/dev/null || true
        sleep 1
        if ss -tln 2>/dev/null | grep -q ":${port} "; then
            fail "Port $port still in use after cleanup — kill the process manually"
        fi
    fi
done
ok "Ports 4200/8000 are free"

# ── Prerequisites ─────────────────────────────────────────────────
step "Checking prerequisites"
command -v docker  >/dev/null || fail "docker not found"

if ! command -v uv >/dev/null 2>&1; then
    info "uv not found — installing..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
    command -v uv >/dev/null || fail "uv install failed"
    ok "uv installed"
fi

command -v node    >/dev/null || fail "node not found"
command -v npm     >/dev/null || fail "npm not found"

# Detect docker compose variant (plugin vs standalone)
if docker compose version &>/dev/null; then
    DC="docker compose"
elif command -v docker-compose &>/dev/null; then
    DC="docker-compose"
else
    fail "Neither 'docker compose' nor 'docker-compose' found"
fi
ok "All prerequisites found (compose: $DC)"

# ── Docker Compose ────────────────────────────────────────────────
step "Starting Docker infrastructure"
$DC -f "$ROOT/docker-compose.yml" down --remove-orphans 2>/dev/null || true
$DC -f "$ROOT/docker-compose.yml" up -d

info "Waiting for PostgreSQL..."
for i in $(seq 1 30); do
    status=$(docker inspect --format='{{.State.Health.Status}}' nimbus-postgres 2>/dev/null || echo "starting")
    [[ "$status" == "healthy" ]] && break
    sleep 2
done
[[ "$status" == "healthy" ]] || fail "PostgreSQL did not become healthy"
ok "PostgreSQL healthy"

info "Waiting for Temporal..."
for i in $(seq 1 40); do
    status=$(docker inspect --format='{{.State.Health.Status}}' nimbus-temporal 2>/dev/null || echo "starting")
    [[ "$status" == "healthy" ]] && break
    sleep 3
done
[[ "$status" == "healthy" ]] || fail "Temporal did not become healthy"
ok "Temporal healthy"

info "Registering Temporal namespace 'nimbus'..."
"$ROOT/backend/.venv/bin/python" -c "
from temporalio.client import Client
from temporalio.api.workflowservice.v1 import RegisterNamespaceRequest
from google.protobuf.duration_pb2 import Duration
import asyncio
async def main():
    client = await Client.connect('localhost:7233')
    try:
        await client.workflow_service.register_namespace(
            RegisterNamespaceRequest(namespace='nimbus',
                workflow_execution_retention_period=Duration(seconds=259200)))
        print('created')
    except Exception as e:
        print('exists' if 'already exists' in str(e).lower() else f'error: {e}')
asyncio.run(main())
" 2>/dev/null && ok "Temporal namespace ready" || info "Namespace registration deferred (backend deps not yet installed)"

# ── Install dependencies (parallel) ──────────────────────────────
if [[ "$SKIP_BUILD" == false ]]; then
    step "Installing dependencies (backend + frontend in parallel)"

    (cd "$ROOT/backend" && uv sync 2>&1 | sed 's/^/  [backend] /') &
    PID_BE_DEPS=$!

    (cd "$ROOT/frontend" && npm ci --prefer-offline 2>/dev/null || npm install 2>&1 | sed 's/^/  [frontend] /') &
    PID_FE_DEPS=$!

    wait $PID_BE_DEPS || fail "Backend dependency install failed"
    ok "Backend dependencies installed"

    wait $PID_FE_DEPS || fail "Frontend dependency install failed"
    ok "Frontend dependencies installed"

    # ── Migrations (needs backend deps + postgres) ────────────────
    step "Running database migrations"
    (cd "$ROOT/backend" && uv run alembic upgrade head)
    ok "Migrations applied"
fi

# ── Start services (all parallel) ────────────────────────────────
step "Starting all services"

# Backend API
(cd "$ROOT/backend" && exec uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000) 2>&1 | sed 's/^/  [api]    /' &
PIDS+=($!)
info "Backend API starting on http://localhost:8000"

# Temporal worker
(cd "$ROOT/backend" && exec uv run python -m app.workflows.worker) 2>&1 | sed 's/^/  [worker] /' &
PIDS+=($!)
info "Temporal worker starting"

# Frontend dev server
(cd "$ROOT/frontend" && exec npx ng serve --port 4200 --host 0.0.0.0) 2>&1 | sed 's/^/  [ui]     /' &
PIDS+=($!)
info "Frontend starting on http://localhost:4200"

echo ""
echo -e "${G}All services launched.${NC}"
echo ""
echo "  Backend API:     http://localhost:8000"
echo "  Frontend:        http://localhost:4200"
echo "  Temporal UI:     http://localhost:8233"
echo "  MinIO Console:   http://localhost:9001"
echo "  GraphQL:         http://localhost:8000/graphql"
echo ""
echo -e "${Y}Press Ctrl+C to stop all services.${NC}"
echo ""

# Wait for any process to exit
wait -n "${PIDS[@]}" 2>/dev/null || true
