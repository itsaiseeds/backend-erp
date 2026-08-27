#!/usr/bin/env bash
# =============================================================================
# integration_db.sh — Build a throwaway integration-test database from DDL + DML
# =============================================================================
# Creates a SEPARATE Postgres database (default: django_test) from
# sql/ddl.sql + sql/dml.sql. It never touches your dev 'django' database.
#
# Usage:
#   bash scripts/integration_db.sh                # create django_test (DDL+DML)
#   bash scripts/integration_db.sh --drop         # drop django_test only
#   bash scripts/integration_db.sh --name xyz     # use db name 'xyz'
#
# Runs via the Docker db container (no local psql needed).
# Use Git Bash: "C:\Program Files\Git\bin\bash.exe" scripts/integration_db.sh
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SQL_DIR="$REPO_ROOT/sql"
ENV_FILE="$REPO_ROOT/.env.dev"

TEST_DB="django_test"
DROP_ONLY=0

# ---------------------------------------------------------------------------
# Parse arguments
# ---------------------------------------------------------------------------
while [[ $# -gt 0 ]]; do
    case "$1" in
        --name)
            TEST_DB="$2"
            shift 2
            ;;
        --drop)
            DROP_ONLY=1
            shift
            ;;
        *)
            echo "Unknown argument: $1"
            echo "Usage: bash scripts/integration_db.sh [--name db] [--drop]"
            exit 1
            ;;
    esac
done

# ---------------------------------------------------------------------------
# Prerequisites
# ---------------------------------------------------------------------------
if ! command -v docker &>/dev/null; then
    echo "Error: 'docker' is not installed or not in PATH."
    exit 1
fi

if [[ ! -f "$ENV_FILE" ]]; then
    echo "Error: Environment file not found: $ENV_FILE"
    exit 1
fi

set -a
source "$ENV_FILE"
set +a

for var in POSTGRES_DB POSTGRES_USER POSTGRES_PASSWORD; do
    if [[ -z "${!var:-}" ]]; then
        echo "Error: $var is not set in $ENV_FILE"
        exit 1
    fi
done

DbUser="$POSTGRES_USER"

if ! docker compose ps db --format "{{.Status}}" 2>/dev/null | grep -q "Up"; then
    echo "Error: The 'db' container is not running."
    echo "Run: docker compose up -d"
    exit 1
fi

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
run_psql() {
    echo "$1" | docker compose exec -T db psql -U "$DbUser" -d postgres -v ON_ERROR_STOP=1
}

run_sql_in() {
    # "$1" = target db, remaining args = sql files
    local target_db="$1"
    shift
    for file in "$@"; do
        if [[ ! -f "$file" ]]; then
            echo "Error: SQL file not found: $file"
            exit 1
        fi
        echo "[SQL] Applying $(basename "$file") into '$target_db' ..."
        cat "$file" | docker compose exec -T db psql -U "$DbUser" -d "$target_db" -v ON_ERROR_STOP=1
    done
}

# ---------------------------------------------------------------------------
# Drop (idempotent)
# ---------------------------------------------------------------------------
echo "[DROP] Dropping test database '$TEST_DB' (if present) ..."
run_psql "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '$TEST_DB' AND pid <> pg_backend_pid();" >/dev/null || true
run_psql "DROP DATABASE IF EXISTS \"$TEST_DB\";"
echo "[DROP] Done."

if [[ "$DROP_ONLY" -eq 1 ]]; then
    echo "Finished: dropped $TEST_DB (--drop). Exiting."
    exit 0
fi

# ---------------------------------------------------------------------------
# Create + load DDL + DML
# ---------------------------------------------------------------------------
echo "[CREATE] Creating test database '$TEST_DB' ..."
run_psql "CREATE DATABASE \"$TEST_DB\" OWNER \"$DbUser\";"

run_sql_in "$TEST_DB" "$SQL_DIR/ddl.sql" "$SQL_DIR/dml.sql"

echo "=============================================="
echo " Integration-test DB ready: $TEST_DB"
echo "=============================================="
