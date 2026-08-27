#!/usr/bin/env bash
# =============================================================================
# reload_db.sh — Drop the whole database, then recreate schema + seed data
# =============================================================================
# Usage:
#   bash scripts/reload_db.sh --step ddl      # Drop DB + create tables only
#   bash scripts/reload_db.sh --step dml      # Insert seed data only
#   bash scripts/reload_db.sh --step all      # Drop DB + DDL + DML
#
# Runs via the Docker db container (no local psql needed).
# Use Git Bash: "C:\Program Files\Git\bin\bash.exe" scripts/reload_db.sh
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SQL_DIR="$REPO_ROOT/sql"
ENV_FILE="$REPO_ROOT/.env.dev"

# ---------------------------------------------------------------------------
# Parse arguments
# ---------------------------------------------------------------------------
STEP=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --step)
            STEP="$2"
            shift 2
            ;;
        *)
            echo "Unknown argument: $1"
            echo "Usage: bash scripts/reload_db.sh --step ddl|dml|all"
            exit 1
            ;;
    esac
done

if [[ -z "$STEP" ]]; then
    echo "Error: --step argument is required."
    echo "Usage: bash scripts/reload_db.sh --step ddl|dml|all"
    exit 1
fi

if [[ "$STEP" != "ddl" && "$STEP" != "dml" && "$STEP" != "all" ]]; then
    echo "Error: --step must be 'ddl', 'dml', or 'all'. Got: $STEP"
    exit 1
fi

# ---------------------------------------------------------------------------
# Check prerequisites
# ---------------------------------------------------------------------------
if ! command -v docker &>/dev/null; then
    echo "Error: 'docker' is not installed or not in PATH."
    exit 1
fi

if [[ ! -f "$ENV_FILE" ]]; then
    echo "Error: Environment file not found: $ENV_FILE"
    exit 1
fi

# ---------------------------------------------------------------------------
# Load environment variables from .env.dev
# ---------------------------------------------------------------------------
set -a
source "$ENV_FILE"
set +a

for var in POSTGRES_DB POSTGRES_USER POSTGRES_PASSWORD; do
    if [[ -z "${!var:-}" ]]; then
        echo "Error: $var is not set in $ENV_FILE"
        exit 1
    fi
done

DbName="$POSTGRES_DB"
DbUser="$POSTGRES_USER"

# ---------------------------------------------------------------------------
# Check that the db container is running
# ---------------------------------------------------------------------------
if ! docker compose ps db --format "{{.Status}}" 2>/dev/null | grep -q "Up"; then
    echo "Error: The 'db' container is not running."
    echo "Run: docker compose up -d"
    exit 1
fi

# ---------------------------------------------------------------------------
# Helper: run SQL via docker exec
# ---------------------------------------------------------------------------
run_psql() {
    echo "$1" | docker compose exec -T db psql -U "$DbUser" -d "$DbName" -v ON_ERROR_STOP=1
}

# ---------------------------------------------------------------------------
# Drop the whole database, then recreate it (no hard-coded table list)
# ---------------------------------------------------------------------------
# We connect to the 'postgres' maintenance db because a database cannot be
# dropped while we are connected to it. DROP/CREATE DATABASE cannot run inside
# a transaction block, hence the separate psql -c calls.
# ---------------------------------------------------------------------------
drop_all() {
    echo "[DROP] Dropping database '$DbName' ..."

    # Terminate any active connections to the target database.
    docker compose exec -T db psql -U "$DbUser" -d postgres -v ON_ERROR_STOP=1 \
        -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '$DbName' AND pid <> pg_backend_pid();" >/dev/null

    docker compose exec -T db psql -U "$DbUser" -d postgres -v ON_ERROR_STOP=1 \
        -c "DROP DATABASE IF EXISTS \"$DbName\";"

    docker compose exec -T db psql -U "$DbUser" -d postgres -v ON_ERROR_STOP=1 \
        -c "CREATE DATABASE \"$DbName\" OWNER \"$DbUser\";"

    echo "[DROP] Recreated database '$DbName'."
}

# ---------------------------------------------------------------------------
# Execute a SQL file
# ---------------------------------------------------------------------------
run_sql() {
    local file="$1"
    local label="$2"

    if [[ ! -f "$file" ]]; then
        echo "Error: SQL file not found: $file"
        exit 1
    fi

    echo "[$label] Running $(basename "$file") ..."
    cat "$file" | docker compose exec -T db psql -U "$DbUser" -d "$DbName" -v ON_ERROR_STOP=1
    echo "[$label] Done."
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
echo "=============================================="
echo " Database: $DbName (via Docker)"
echo " Step:     $STEP"
echo "=============================================="

case "$STEP" in
    ddl)
        drop_all
        run_sql "$SQL_DIR/ddl.sql" "DDL"
        ;;
    dml)
        run_sql "$SQL_DIR/dml.sql" "DML"
        ;;
    all)
        drop_all
        run_sql "$SQL_DIR/ddl.sql" "DDL"
        run_sql "$SQL_DIR/dml.sql" "DML"
        ;;
esac

echo "=============================================="
echo " Finished: $STEP"
echo "=============================================="