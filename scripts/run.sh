#!/usr/bin/env bash
# =============================================================================
# run.sh — Single entry point for all project commands
# =============================================================================
# Usage:
#   bash scripts/run.sh build        # Build Docker images
#   bash scripts/run.sh up           # Start all services (auto-builds Flutter if needed)
#   bash scripts/run.sh down         # Stop all services
#   bash scripts/run.sh restart      # Restart all services
#   bash scripts/run.sh reload-db    # Drop + recreate tables + seed data
#   bash scripts/run.sh logs         # Tail logs
#   bash scripts/run.sh status       # Show container status
#   bash scripts/run.sh shell        # Open Django shell in web container
#   bash scripts/run.sh psql         # Open psql in db container
#   bash scripts/run.sh flutter      # Build Flutter web app for production
#   bash scripts/run.sh flutter-prod # Build Flutter web app pointing at the prod API
#   bash scripts/run.sh schema       # Regenerate docs/api/openapi.yml
#   bash scripts/run.sh test         # All tests (in web container)
#   bash scripts/run.sh test-unit    # Only non-integration tests (in web container)
#   bash scripts/run.sh test-dml     # DML-seeded Django tests (in web container)
#   bash scripts/run.sh lint         # ruff check (in web container)
#   bash scripts/run.sh typecheck    # mypy (in web container)
#   bash scripts/run.sh hooks        # Install git pre-commit hooks (ruff lint)
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

COMMAND="${1:-}"

if [[ -z "$COMMAND" ]]; then
    echo "Usage: bash scripts/run.sh <command> [args...]"
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
    echo "  flutter     Build Flutter web app for production"
    echo "  flutter-prod Build Flutter web app for the production API"
    echo "  schema      Regenerate docs/api/openapi.yml"
    echo "  test        Run all tests in web container"
    echo "  test-unit   Run unit tests in web container"
    echo "  test-dml    Run DML-seeded Django tests in web container"
    echo "  lint        Run ruff check in web container"
    echo "  typecheck   Run mypy in web container"
    echo "  hooks       Install git pre-commit hooks (ruff lint)"
    exit 1
fi

# Drop the command word; remaining "$@" are passed on to subcommands that take args.
shift

# ---------------------------------------------------------------------------
# Find Flutter
# ---------------------------------------------------------------------------
FLUTTER_CMD=""

find_flutter() {
    if [ -n "$FLUTTER_CMD" ]; then
        return
    fi

    if command -v flutter &>/dev/null; then
        FLUTTER_CMD="flutter"
        return
    fi

    # Windows common paths (check both flutter and flutter.bat)
    for path in \
        "C:/flutter/bin" \
        "C:/src/flutter/bin" \
        "$LOCALAPPDATA/flutter/bin" \
        "$HOME/flutter/bin" \
        "/opt/flutter/bin"; do
        if [ -f "$path/flutter.bat" ]; then
            FLUTTER_CMD="$path/flutter.bat"
            echo "[flutter] Found Flutter at $path"
            return
        fi
        if [ -f "$path/flutter" ]; then
            FLUTTER_CMD="$path/flutter"
            echo "[flutter] Found Flutter at $path"
            return
        fi
    done

    echo "Error: flutter not found."
    echo "Install Flutter SDK: https://docs.flutter.dev/get-started/install"
    exit 1
}

# ---------------------------------------------------------------------------
# Flutter build (production)
# ---------------------------------------------------------------------------
cmd_flutter() {
    find_flutter
    echo "[flutter] Building Flutter web app ..."
    cd "$REPO_ROOT/web"
    "$FLUTTER_CMD" pub get
    MSYS_NO_PATHCONV=1 "$FLUTTER_CMD" build web --release --base-href /sales-admin/
    cd "$REPO_ROOT"
    echo "[flutter] Build complete: web/build/web/"
}

# ---------------------------------------------------------------------------
# Flutter build (production) with the prod API baked in.
# ---------------------------------------------------------------------------
# --dart-define bakes a COMPILE-TIME constant into the static web bundle, so
# unlike a server-side Render env var it must be rebuilt whenever the URL
# changes. Override at call time if needed:
#   API_BASE_URL=https://api.example.com bash scripts/run.sh flutter-prod
cmd_flutter_prod() {
    find_flutter
    local prod_url
    prod_url="${API_BASE_URL:-https://backend-erp-jlt9.onrender.com/}"
    echo "[flutter-prod] Building Flutter web app for prod API: $prod_url"
    cd "$REPO_ROOT/web"
    "$FLUTTER_CMD" pub get
    MSYS_NO_PATHCONV=1 "$FLUTTER_CMD" build web --release \
        --base-href /sales-admin/ \
        --dart-define=API_BASE_URL="$prod_url"
    cd "$REPO_ROOT"
    echo "[flutter-prod] Build complete: web/build/web/"
}

# ---------------------------------------------------------------------------
# Build Docker images
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
    # Auto-build Flutter if build output is missing
    if [ ! -f "$REPO_ROOT/web/build/web/index.html" ]; then
        cmd_flutter
    fi
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
# OpenAPI schema
# ---------------------------------------------------------------------------
cmd_schema() {
    echo "[schema] Regenerating OpenAPI spec ..."
    docker compose exec web python manage.py spectacular --file docs/api/openapi.yml
    echo "[schema] Wrote docs/api/openapi.yml"
}

# ---------------------------------------------------------------------------
# Tests (inside the web container so host Python without Django is irrelevant)
# ---------------------------------------------------------------------------
# Run commands in a SHORT-LIVED web-service container instead of exec-ing into
# the long-running one. The one-off never boots the ENTRYPOINT (gunicorn etc.),
# so tests/lint only pay for the python image + db — keeps memory tiny and
# avoids GitHub Actions OOM-kills (exit 137).
webrun() {
    docker compose run --rm --no-deps --entrypoint "" -T web "$@"
}

cmd_test_unit() {
    echo "[test-unit] Running unit tests in web container ..."
    webrun python -m pytest -v
}

cmd_test_dml() {
    echo "[test-dml] Running DML-seeded Django tests in web container ..."
    webrun python -m pytest tests/test_verify_otp_view.py tests/test_auth_flow.py -v
}

cmd_test() {
    cmd_test_unit
}

# ---------------------------------------------------------------------------
# Lint / typecheck (web container has our pinned versions of ruff + mypy)
# ---------------------------------------------------------------------------
cmd_lint() {
    echo "[lint] Running ruff check in web container ..."
    webrun ruff check .
}

cmd_typecheck() {
    echo "[typecheck] Running mypy in web container ..."
    webrun mypy .
}

# ---------------------------------------------------------------------------
# Install git pre-commit hooks
# ---------------------------------------------------------------------------
cmd_hooks() {
    "$SCRIPT_DIR/install-hooks.sh"
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
    flutter)    cmd_flutter ;;
    flutter-prod) cmd_flutter_prod ;;
    schema)     cmd_schema ;;
    test)       cmd_test ;;
    test-unit)  cmd_test_unit ;;
    test-dml)   cmd_test_dml ;;
    lint)       cmd_lint ;;
    typecheck)  cmd_typecheck ;;
    hooks)      cmd_hooks ;;
    *)
        echo "Unknown command: $COMMAND"
        echo "Run: bash scripts/run.sh (no args) for help"
        exit 1
        ;;
esac
