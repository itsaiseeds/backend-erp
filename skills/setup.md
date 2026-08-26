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
| `.env` | Yes | Render deployment | Production runtime — Neon DB credentials |
| `.env.dev` | No | `reload_db.sh` | Local dev — Docker PostgreSQL |

### `.env` (production)
Contains Neon DB connection details, Django secrets, and debug flags.
**Never committed to git.** Managed by Neon CLI (`neon env pull`).

### `.env.dev` (local development)
Contains local Docker PostgreSQL connection params. **Committed to git** with placeholder values.

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

> **Safety:** This script only connects to local Docker PostgreSQL.
> It will NEVER connect to or modify the production Neon database.

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
| `POSTGRES_HOST` | Yes | Yes | Yes (`localhost`) |
| `POSTGRES_PORT` | Yes | Yes | Yes |
| `ALLOWED_HOSTS` | Yes | Yes | Yes |
| `SECRET_KEY` | Yes (with fallback) | Yes | Yes |
| `DEBUG` | Yes (with fallback) | Yes | Yes |
| `DJANGO_SUPERUSER_USERNAME` | No (command) | Required | Required |
| `DJANGO_SUPERUSER_EMAIL` | No (command) | Required | Required |
| `DJANGO_SUPERUSER_PASSWORD` | No (command) | Required | Required |

---

## Deployment (Render + Neon)

### Architecture

- **Web service**: Django app running gunicorn on Render
- **Cron service**: Pings the app every 10 minutes to prevent cold starts
- **Database**: Neon DB (serverless PostgreSQL)
- **Deploy trigger**: Push to `master` branch auto-deploys via Render GitHub integration

### Setup (one-time)

1. Create account at [render.com](https://render.com)
2. New → Blueprint → connect this GitHub repo
3. Render reads `render.yaml` and provisions:
   - Web service (`backend-erp`)
   - Cron job (`keep-alive`)
4. Update `ALLOWED_HOSTS` in Render env vars to match your actual Render URL

### Environment variables (Render)

| Variable | Value | Source |
|---|---|---|
| `SECRET_KEY` | Auto-generated | Render |
| `DEBUG` | `False` | Hardcoded in render.yaml |
| `ALLOWED_HOSTS` | `backend-erp.onrender.com` | Hardcoded in render.yaml |
| `POSTGRES_HOST` | `ep-misty-block-aya29p71-pooler.c-5.us-east-2.aws.neon.tech` | Neon |
| `POSTGRES_PORT` | `5432` | Neon |
| `POSTGRES_DB` | `neondb` | Neon |
| `POSTGRES_USER` | `neondb_owner` | Neon |
| `POSTGRES_PASSWORD` | (from Neon) | Set manually in Render dashboard |

> **Note:** `POSTGRES_PASSWORD` is not in `render.yaml` for security. Set it manually in Render dashboard after first deploy.

### After first deploy

1. Set `POSTGRES_PASSWORD` in Render dashboard (Environment → Environment Variables)
2. Set `DJANGO_SUPERUSER_USERNAME`, `DJANGO_SUPERUSER_EMAIL`, `DJANGO_SUPERUSER_PASSWORD` in Render dashboard
   - Example: `admin` / `admin@example.com` / `your-strong-password`
3. Run initial schema against Neon (via Neon SQL Editor or psql):
   ```bash
   psql "postgresql://neondb_owner:...@ep-misty-block-aya29p71.c-5.us-east-2.aws.neon.tech/neondb?sslmode=require" -f sql/ddl.sql
   ```
4. Seed initial data:
   ```bash
   psql "postgresql://neondb_owner:...@ep-misty-block-aya29p71.c-5.us-east-2.aws.neon.tech/neondb?sslmode=require" -f sql/dml.sql
   ```
5. `createsuperuser_if_not_exists` runs automatically on every deploy (idempotent)

### CI/CD flow

```
Developer pushes to feature branch
        ↓
Opens PR to master
        ↓
GitHub Actions runs pytest (must pass)
        ↓
PR merged to master
        ↓
Render auto-deploys web service
        ↓
Cron pings app every 10 min (prevents cold starts)
```

### Schema changes in production

1. Write the `ALTER TABLE` / `CREATE TABLE` SQL
2. Test locally against Docker PostgreSQL first
3. Run against Neon via Neon SQL Editor or `psql`
4. Update `sql/ddl.sql` to keep local reference in sync

> **Never** use `reload_db.sh` against production.
> **Never** run Django migrations against production.
