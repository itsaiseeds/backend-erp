# Setup & Environment

> First-time setup, environment files, and daily workflow.

---

## Prerequisites

- Docker & Docker Compose
- Python 3.14+ (for local management commands outside Docker)

---

## Environment Files

| File | Gitignored | Used by | Purpose |
|---|---|---|---|
| `.env` | Yes | Docker Compose (`web` service) | Production runtime — Neon DB credentials |
| `.env.dev` | No | `reload_db.sh` | Local dev — localhost PostgreSQL |

### `.env` (production)
Contains Neon DB connection details, Django secrets, and debug flags.
**Never committed to git.** Injected at deploy time.

### `.env.dev` (local development)
Contains local PostgreSQL connection params. **Committed to git** with placeholder values.

---

## First-Time Setup

```bash
# 1. Build the Docker image
docker compose build

# 2. Start all services (Django + PostgreSQL)
docker compose up -d

# 3. Create all tables + seed data
bash scripts/reload_db.sh --step all
```

Django is now running at `http://localhost:8000/admin/`
Login: `admin` / `admin` or `xZist` / `admin@123`

---

## Running the Django Server

### Via Docker Compose (recommended)

```bash
# Start all services in detached mode (Django + PostgreSQL)
docker compose up -d

# Start services and see logs in the terminal
docker compose up

# Start only the Django web server (db must already be running)
docker compose up web

# Rebuild images and start (after Dockerfile or requirements changes)
docker compose up -d --build

# Restart all services
docker compose restart

# Stop all services
docker compose down

# Stop and remove volumes (destroys database data)
docker compose down -v
```

### Checking if services are running

```bash
# Show container status
docker compose ps

# View logs from all services
docker compose logs -f

# View logs from only the web service
docker compose logs -f web

# View logs from only the db service
docker compose logs -f db
```

### Running Django management commands inside Docker

```bash
# Open a Django shell inside the running web container
docker compose exec web python manage.py shell

# Create a new superuser
docker compose exec web python manage.py createsuperuser

# Collect static files
docker compose exec web python manage.py collectstatic
```

---

## Reloading the Database

### Full reload (drop + create + seed)

```bash
bash scripts/reload_db.sh --step all
```

This drops all tables, recreates them from `sql/ddl.sql`, and inserts seed data from `sql/dml.sql`.

### Schema only (drop + create tables, no seed data)

```bash
bash scripts/reload_db.sh --step ddl
```

### Seed data only (insert data without dropping tables)

```bash
bash scripts/reload_db.sh --step dml
```

### How the reload script works

1. Reads connection params from `.env.dev`
2. Checks that Docker and the `db` container are running
3. `--step ddl` or `--step all`: drops all tables (reverse dependency order), then runs `ddl.sql`
4. `--step dml` or `--step all`: runs `dml.sql` to insert seed data
5. All SQL runs inside the Docker `db` container via `docker compose exec`

> **Important:** The `db` container must be running before running `reload_db.sh`.
> Start it with: `docker compose up -d`

---

## Quick Reference

```bash
# Build images
docker compose build

# Start everything
docker compose up -d

# Reload database
bash scripts/reload_db.sh --step all

# Check status
docker compose ps

# View logs
docker compose logs -f

# Stop everything
docker compose down
```

---

## Django Management Commands

Run via Docker:
```bash
docker compose exec web python manage.py <command>
```

Or locally (with `.env.dev` loaded):
```bash
python manage.py <command>
```

Useful commands:
- `python manage.py shell` — interactive Python shell
- `python manage.py createsuperuser` — create additional superusers
- `python manage.py collectstatic` — collect static files (needs `STATIC_ROOT` in settings first)

---

## Adding a New Django App

```bash
# Create the app
python manage.py startapp <app_name>

# Add to INSTALLED_APPS in config/settings.py:
#   '<app_name>',

# The existing MIGRATION_MODULES line automatically picks up new apps:
#   MIGRATION_MODULES = {app.split(".")[-1]: None for app in INSTALLED_APPS}

# Write your models, then:
# 1. Add CREATE TABLE to sql/ddl.sql
# 2. Add any seed data to sql/dml.sql
# 3. Run: bash scripts/reload_db.sh --step all
```

---

## Environment Variables (Django settings.py)

| Variable | Read by settings.py | Used in `.env` | Used in `.env.dev` |
|---|---|---|---|
| `POSTGRES_DB` | Yes | Yes | Yes |
| `POSTGRES_USER` | Yes | Yes | Yes |
| `POSTGRES_PASSWORD` | Yes | Yes | Yes |
| `POSTGRES_HOST` | Yes | Yes (`db`) | Yes (`localhost`) |
| `POSTGRES_PORT` | Yes | Yes | Yes |
| `ALLOWED_HOSTS` | Yes | Yes | Yes |
| `SECRET_KEY` | **No** (hardcoded) | Yes | Yes |
| `DEBUG` | **No** (hardcoded) | Yes | Yes |

> **Note:** `SECRET_KEY` and `DEBUG` are not read from environment in `settings.py`. This is intentional for now but may need to be addressed before production deployment.
