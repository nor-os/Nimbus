<#
.SYNOPSIS
    Nimbus build script — validates prerequisites, starts infrastructure, installs dependencies, runs migrations.
.DESCRIPTION
    Overview: Orchestrates the entire build process for local development.
    Architecture: Build system entry point (Section 10)
    Dependencies: PowerShell 7+, Docker, Python 3.12+, Node.js 20+, uv
    Concepts: Build automation, local development
.PARAMETER SkipDocker
    Skip starting Docker Compose infrastructure.
.PARAMETER SkipFrontend
    Skip installing frontend dependencies.
.PARAMETER CI
    Run in CI mode (non-interactive, fail on warnings).
#>
param(
    [switch]$SkipDocker,
    [switch]$SkipFrontend,
    [switch]$CI
)

$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot

function Write-Step($message) {
    Write-Host "`n==> $message" -ForegroundColor Cyan
}

function Test-Command($command) {
    $null -ne (Get-Command $command -ErrorAction SilentlyContinue)
}

# ── Prerequisites ─────────────────────────────────────────────────
Write-Step "Checking prerequisites"

# Python
if (-not (Test-Command "python")) {
    Write-Error "Python not found. Install Python 3.12+."
}
$pyVersion = (python --version 2>&1) -replace "Python ", ""
$pyMajor, $pyMinor = $pyVersion.Split(".")[0..1]
if ([int]$pyMajor -lt 3 -or ([int]$pyMajor -eq 3 -and [int]$pyMinor -lt 12)) {
    Write-Error "Python 3.12+ required, found $pyVersion"
}
Write-Host "  Python $pyVersion"

# Node.js
if (-not (Test-Command "node")) {
    Write-Error "Node.js not found. Install Node.js 20 LTS."
}
$nodeVersion = (node --version) -replace "v", ""
$nodeMajor = [int]($nodeVersion.Split(".")[0])
if ($nodeMajor -lt 20) {
    Write-Error "Node.js 20+ required, found v$nodeVersion"
}
Write-Host "  Node.js v$nodeVersion"

# Docker
if (-not (Test-Command "docker")) {
    Write-Error "Docker not found. Install Docker Desktop."
}
Write-Host "  Docker $(docker --version)"

# uv
if (-not (Test-Command "uv")) {
    Write-Error "uv not found. Install with: pip install uv"
}
Write-Host "  uv $(uv --version)"

Write-Host "  All prerequisites met." -ForegroundColor Green

# ── Docker Compose ────────────────────────────────────────────────
if (-not $SkipDocker) {
    Write-Step "Starting Docker Compose infrastructure"
    Push-Location $Root
    docker compose up -d
    Pop-Location

    Write-Host "  Waiting for PostgreSQL to be ready..."
    $attempts = 0
    do {
        Start-Sleep -Seconds 2
        $attempts++
        $healthy = docker inspect --format='{{.State.Health.Status}}' nimbus-postgres 2>$null
    } while ($healthy -ne "healthy" -and $attempts -lt 30)

    if ($healthy -ne "healthy") {
        Write-Error "PostgreSQL did not become healthy within 60 seconds."
    }
    Write-Host "  Infrastructure running." -ForegroundColor Green
}

# ── Backend Dependencies ──────────────────────────────────────────
Write-Step "Installing backend dependencies"
Push-Location "$Root/backend"
uv sync
Pop-Location
Write-Host "  Backend dependencies installed." -ForegroundColor Green

# ── Database Migrations ───────────────────────────────────────────
Write-Step "Running database migrations"
Push-Location "$Root/backend"
uv run alembic upgrade head
Pop-Location
Write-Host "  Migrations applied." -ForegroundColor Green

# ── Frontend Dependencies ─────────────────────────────────────────
if (-not $SkipFrontend) {
    Write-Step "Installing frontend dependencies"
    Push-Location "$Root/frontend"
    npm ci --prefer-offline 2>$null || npm install
    Pop-Location
    Write-Host "  Frontend dependencies installed." -ForegroundColor Green
}

# ── Done ──────────────────────────────────────────────────────────
Write-Host "`n" -NoNewline
Write-Host "Build complete!" -ForegroundColor Green
Write-Host @"

  Start backend:   cd backend && uv run uvicorn app.main:app --reload
  Start worker:    cd backend && uv run python -m app.workflows.worker
  Start frontend:  cd frontend && npm start

  Services:
    Backend API:     http://localhost:8000
    Frontend:        http://localhost:4200
    Temporal UI:     http://localhost:8233
    MinIO Console:   http://localhost:9001
    Swagger (debug): http://localhost:8000/docs
"@
