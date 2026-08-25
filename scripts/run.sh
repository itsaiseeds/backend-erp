#!/usr/bin/env bash
# =============================================================================
# run.sh — Single entry point for all project commands
# =============================================================================
# Usage:
#   bash scripts/run.sh build        # Build Docker images
#   bash scripts/run.sh up           # Start all services
#   bash scripts/run.sh down         # Stop all services
#   bash scripts/run.sh restart      # Restart all services
#   bash scripts/run.sh reload-db    # Drop + recreate tables + seed data
#   bash scripts/run.sh logs         # Tail logs
#   bash scripts/run.sh status       # Show container status
#   bash scripts/run.sh shell        # Open Django shell in web container
#   bash scripts/run.sh psql         # Open psql in db container
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

COMMAND="${1:-}"

if [[ -z "$COMMAND" ]]; then
    echo "Usage: bash scripts/run.sh <command>"
    echo ""
    echo "Commands:"
    echo "  build       Build Docker images"
    echo "  up          Start all services (detached)"
    echo "  down        Stop all services"
    echo "  restart     Restart all services"
    echo "  reload-db   Drop + recreate tables + seed data"
    echo "  logs        Tail logs from all services"
    echo "  status      Show container status"
    echo "  shell       Open Django shell in web container"
    echo "  psql        Open psql in db container"
    exit 1
fi

# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------
cmd_build() {
    echo "[build] Building Docker images ..."
    docker compose build
    echo "[build] Done."
}

# ---------------------------------------------------------------------------
# Up
# ---------------------------------------------------------------------------
cmd_up() {
    echo "[up] Starting services ..."
    docker compose up -d
    echo "[up] Done."
    docker compose ps
}

# ---------------------------------------------------------------------------
# Down
# ---------------------------------------------------------------------------
cmd_down() {
    echo "[down] Stopping services ..."
    docker compose down
    echo "[down] Done."
}

# ---------------------------------------------------------------------------
# Restart
# ---------------------------------------------------------------------------
cmd_restart() {
    echo "[restart] Restarting services ..."
    docker compose restart
    echo "[restart] Done."
    docker compose ps
}

# ---------------------------------------------------------------------------
# Reload DB
# ---------------------------------------------------------------------------
cmd_reload_db() {
    "$SCRIPT_DIR/reload_db.sh" --step all
}

# ---------------------------------------------------------------------------
# Logs
# ---------------------------------------------------------------------------
cmd_logs() {
    docker compose logs -f
}

# ---------------------------------------------------------------------------
# Status
# ---------------------------------------------------------------------------
cmd_status() {
    docker compose ps
}

# ---------------------------------------------------------------------------
# Shell
# ---------------------------------------------------------------------------
cmd_shell() {
    docker compose exec web python manage.py shell
}

# ---------------------------------------------------------------------------
# PSQL
# ---------------------------------------------------------------------------
cmd_psql() {
    docker compose exec db psql -U django -d django
}

# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------
case "$COMMAND" in
    build)      cmd_build ;;
    up)         cmd_up ;;
    down)       cmd_down ;;
    restart)    cmd_restart ;;
    reload-db)  cmd_reload_db ;;
    logs)       cmd_logs ;;
    status)     cmd_status ;;
    shell)      cmd_shell ;;
    psql)       cmd_psql ;;
    *)
        echo "Unknown command: $COMMAND"
        echo "Run: bash scripts/run.sh (no args) for help"
        exit 1
        ;;
esac