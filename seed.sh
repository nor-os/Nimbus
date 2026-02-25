#!/bin/sh
# Overview: Run the demo data seeder against running infrastructure.
# Architecture: One-shot container that seeds via setup wizard + migration replay.
# Dependencies: Docker, .env, backend image built, infrastructure running
# Concepts: Demo data seeding, interactive container execution

set -eu

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ENV_FILE="$SCRIPT_DIR/.env"
COMPOSE_FILE="$SCRIPT_DIR/docker-compose.prod.yml"

# ── Colors ───────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

info()  { printf "${BLUE}[INFO]${NC}  %s\n" "$*"; }
ok()    { printf "${GREEN}[OK]${NC}    %s\n" "$*"; }
error() { printf "${RED}[ERROR]${NC} %s\n" "$*" >&2; }

# ── Load .env ────────────────────────────────────────────────────
if [ ! -f "$ENV_FILE" ]; then
    error ".env file not found at $ENV_FILE"
    exit 1
fi

set -a
. "$ENV_FILE"
set +a
ok "Loaded .env"

# ── Verify infrastructure is running ────────────────────────────
info "Checking infrastructure..."

pg_status=$(docker inspect --format='{{.State.Health.Status}}' nimbus-postgres 2>/dev/null || echo "not found")
if [ "$pg_status" != "healthy" ]; then
    error "PostgreSQL is not healthy (status: $pg_status). Start infrastructure first."
    exit 1
fi
ok "PostgreSQL healthy"

be_status=$(docker inspect --format='{{.State.Health.Status}}' nimbus-backend 2>/dev/null || echo "not found")
if [ "$be_status" != "healthy" ]; then
    error "Backend is not healthy (status: $be_status). Start backend first."
    exit 1
fi
ok "Backend healthy"

# ── Resolve Docker network ──────────────────────────────────────
NETWORK=$(docker inspect nimbus-backend --format='{{range $k, $v := .NetworkSettings.Networks}}{{$k}}{{"\n"}}{{end}}' 2>/dev/null | head -1)
if [ -z "$NETWORK" ]; then
    error "Cannot determine backend network"
    exit 1
fi
ok "Using network: $NETWORK"

# ── Resolve backend image ───────────────────────────────────────
IMAGE=$(docker inspect nimbus-backend --format='{{.Config.Image}}' 2>/dev/null)
if [ -z "$IMAGE" ]; then
    error "Cannot determine backend image"
    exit 1
fi
ok "Using image: $IMAGE"

# ── Run seeder ──────────────────────────────────────────────────
info "Running demo data seeder..."
echo ""

docker run --rm -it \
    --name nimbus-seed \
    --network "$NETWORK" \
    -e NIMBUS_DATABASE_URL="postgresql+asyncpg://${POSTGRES_USER:-nimbus}:${POSTGRES_PASSWORD}@nimbus-postgres:5432/nimbus?ssl=disable" \
    -e NIMBUS_BACKEND_URL="http://nimbus-backend:8000" \
    -e NIMBUS_ADMIN_EMAIL="${ADMIN_EMAIL:-admin@nimbus.dev}" \
    -e NIMBUS_ADMIN_PASSWORD="${ADMIN_PASSWORD:-admin}" \
    -e NIMBUS_ORG_NAME="${ORG_NAME:-Nimbus Demo}" \
    "$IMAGE" \
    python -m app.seed_demo

echo ""
ok "Seeding complete"
