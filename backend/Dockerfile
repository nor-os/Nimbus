# Overview: Multi-stage Dockerfile for the Nimbus backend (FastAPI + Alembic).
# Architecture: Produces a slim production image with uv-managed dependencies.
# Dependencies: Python 3.12, uv, PostgreSQL client libs
# Concepts: Multi-stage build, non-root user, health check

# ── Build stage ──────────────────────────────────────────────────────
FROM python:3.12-slim-bookworm AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Install dependencies first (layer cache)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-editable

# Copy application code
COPY . .

# ── Runtime stage ────────────────────────────────────────────────────
FROM python:3.12-slim-bookworm AS runtime

RUN apt-get update && apt-get install -y --no-install-recommends \
        libpq5 curl \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd -r nimbus && useradd -r -g nimbus -d /app -s /sbin/nologin nimbus

WORKDIR /app

# Copy virtualenv and app from builder
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/app ./app
COPY --from=builder /app/alembic ./alembic
COPY --from=builder /app/alembic.ini ./alembic.ini
COPY --from=builder /app/pyproject.toml ./pyproject.toml

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH="/app" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

RUN chown -R nimbus:nimbus /app
USER nimbus

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
