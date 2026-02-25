#!/bin/sh
# Overview: Production build script for Nimbus.
# Architecture: Validates prerequisites, builds Docker images, runs migrations.
# Dependencies: Docker, Docker Compose, .env file
# Concepts: Production deployment, container orchestration

set -eu

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
COMPOSE_FILE="$SCRIPT_DIR/docker-compose.prod.yml"
ENV_FILE="$SCRIPT_DIR/.env"

# ── Colors ───────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

info()  { printf "${BLUE}[INFO]${NC}  %s\n" "$*"; }
ok()    { printf "${GREEN}[OK]${NC}    %s\n" "$*"; }
warn()  { printf "${YELLOW}[WARN]${NC}  %s\n" "$*"; }
error() { printf "${RED}[ERROR]${NC} %s\n" "$*" >&2; }

# ── Prerequisites ────────────────────────────────────────────────
check_prereqs() {
    info "Checking prerequisites..."

    if ! command -v docker >/dev/null 2>&1; then
        error "Docker is not installed. Install from https://docs.docker.com/get-docker/"
        exit 1
    fi
    ok "Docker found: $(docker --version)"

    if ! docker compose version >/dev/null 2>&1; then
        error "Docker Compose V2 is required. Update Docker or install the compose plugin."
        exit 1
    fi
    ok "Docker Compose found: $(docker compose version --short)"

    if ! docker info >/dev/null 2>&1; then
        error "Docker daemon is not running. Start Docker and try again."
        exit 1
    fi
    ok "Docker daemon is running"
}

# ── Environment ──────────────────────────────────────────────────
check_env() {
    info "Checking environment configuration..."

    if [ ! -f "$ENV_FILE" ]; then
        error ".env file not found. Create one from the example:"
        error "  cp .env.example .env"
        error "Then fill in the required values (POSTGRES_PASSWORD, JWT_SECRET_KEY, MINIO_ROOT_PASSWORD)."
        exit 1
    fi
    ok ".env file found"

    # Source .env to validate required vars
    set -a
    . "$ENV_FILE"
    set +a

    missing=0
    for var in POSTGRES_PASSWORD JWT_SECRET_KEY MINIO_ROOT_PASSWORD; do
        eval val="\${$var:-}"
        if [ -z "$val" ]; then
            error "Required variable $var is not set in .env"
            missing=1
        fi
    done

    if [ "$missing" -eq 1 ]; then
        exit 1
    fi
    ok "All required environment variables are set"
}

# ── Build ────────────────────────────────────────────────────────
build_images() {
    info "Building Docker images..."
    docker compose -f "$COMPOSE_FILE" build --parallel
    ok "Images built successfully"
}

# ── Deploy ───────────────────────────────────────────────────────
deploy() {
    info "Starting infrastructure services..."
    docker compose -f "$COMPOSE_FILE" up -d postgres minio valkey
    docker compose -f "$COMPOSE_FILE" up -d minio-init

    info "Waiting for PostgreSQL to be ready..."
    docker compose -f "$COMPOSE_FILE" up -d temporal
    sleep 5

    info "Running database migrations..."
    docker compose -f "$COMPOSE_FILE" up migrations
    ok "Migrations complete"

    info "Starting application services..."
    docker compose -f "$COMPOSE_FILE" up -d backend worker temporal-ui frontend
    ok "All services started"

    info "Seeding demo data..."
    docker compose -f "$COMPOSE_FILE" up seed
    ok "Demo data seeded"
}

# ── Status ───────────────────────────────────────────────────────
show_status() {
    echo ""
    info "Service status:"
    docker compose -f "$COMPOSE_FILE" ps
    echo ""
    ok "Nimbus is ready!"
    echo ""
    info "Access points:"
    echo "  Application:  http://localhost:${APP_PORT:-80}"
    echo "  Temporal UI:  http://localhost:${TEMPORAL_UI_PORT:-8233}"
    echo ""
    info "Useful commands:"
    echo "  Logs:         docker compose -f docker-compose.prod.yml logs -f"
    echo "  Stop:         docker compose -f docker-compose.prod.yml down"
    echo "  Restart:      docker compose -f docker-compose.prod.yml restart"
    echo ""
}

# ── Main ─────────────────────────────────────────────────────────
main() {
    echo ""
    echo "================================================"
    echo "  Nimbus Production Build"
    echo "================================================"
    echo ""

    cmd="${1:-deploy}"
    case "$cmd" in
        build)
            check_prereqs
            check_env
            build_images
            ;;
        deploy)
            check_prereqs
            check_env
            build_images
            deploy
            show_status
            ;;
        down)
            info "Stopping all services..."
            docker compose -f "$COMPOSE_FILE" down
            ok "All services stopped"
            ;;
        status)
            docker compose -f "$COMPOSE_FILE" ps
            ;;
        logs)
            shift
            docker compose -f "$COMPOSE_FILE" logs -f "$@"
            ;;
        *)
            echo "Usage: $0 {build|deploy|down|status|logs [service...]}"
            echo ""
            echo "Commands:"
            echo "  build   - Build Docker images only"
            echo "  deploy  - Build and start all services (default)"
            echo "  down    - Stop all services"
            echo "  status  - Show service status"
            echo "  logs    - Tail logs (optionally for specific service)"
            exit 1
            ;;
    esac
}

main "$@"
