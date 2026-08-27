# Setup & Environment

> First-time setup, environment files, and daily workflow.

---

## Prerequisites

- Docker & Docker Compose
- Python 3.14+ (for local management commands outside Docker)
- Flutter SDK (for building the admin web app)

---

## Environment Files

| File | Gitignored | Used by | Purpose |
|---|---|---|---|
| `.env` | Yes | Render deployment | Production runtime — Neon DB credentials |
| `.env.dev` | No | Docker Compose | Local dev — Docker PostgreSQL |

### `.env` (production)
Contains Neon DB connection details, Django secrets, and debug flags.
**Never committed to git.** Managed by Neon CLI (`neon env pull`).

### `.env.dev` (local development)
Contains local Docker PostgreSQL connection params. **Committed to git** with placeholder values.

---

## First-Time Setup

```bash
# 1. Build Flutter web app (required before Docker build)
bash scripts/run.sh flutter

# 2. Build the Docker image
docker compose build

# 3. Start all services (Django + PostgreSQL)
docker compose up -d

# 4. Create all tables + seed data
bash scripts/reload_db.sh --step all
```

Django is now running at:
- `http://localhost:8000/admin/` — Django admin
- `http://localhost:8000/sales-admin/` — Flutter admin app

Login: the superuser created at startup by `createsuperuser_if_not_exists` (or a user you create with `createsuperuser`).

---

## Flutter Admin Web App

The Flutter app lives in `web/` and the build output is committed to git.

### Build the Flutter app

```bash
bash scripts/run.sh flutter
```

This runs `flutter pub get` and `flutter build web --release --base-href /sales-admin/` in the `web/` directory.

### After building

The build output is at `web/build/web/`. This is committed to git. Docker copies it into the image.

### Changing Flutter code

1. Edit files in `web/lib/`
2. Run `bash scripts/run.sh flutter` to rebuild
3. Commit the updated `web/build/web/` directory
4. Push — Render auto-deploys with the new build

### Why commit the build?

- Avoids installing Flutter SDK in Docker (saves ~100MB image size)
- Docker builds are fast (~5s instead of ~2min)
- Render deploys are fast (~15s instead of ~3min)
- Developer responsibility: always rebuild before committing Flutter changes

---

## Running the Django Server

### Via Docker Compose (recommended)

```bash
# Start all services in detached mode
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
docker compose ps
docker compose logs -f
docker compose logs -f web
docker compose logs -f db
```

### Running Django management commands inside Docker

```bash
docker compose exec web python manage.py shell
docker compose exec web python manage.py createsuperuser
docker compose exec web python manage.py collectstatic
```

---

## Reloading the Database

### Full reload (drop + create + seed)

```bash
bash scripts/reload_db.sh --step all
```

### Schema only (drop + create tables, no seed data)

```bash
bash scripts/reload_db.sh --step ddl
```

### Seed data only (insert data without dropping tables)

```bash
bash scripts/reload_db.sh --step dml
```

> **Important:** The `db` container must be running before running `reload_db.sh`.

> **Safety:** This script only connects to local Docker PostgreSQL.
> It will NEVER connect to or modify the production Neon database.

---

## Quick Reference

```bash
# Build Flutter app
bash scripts/run.sh flutter

# Build Docker images
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

## Deployment (Render + Neon)

### Architecture

- **Web service**: Django app running gunicorn on Render (Docker-based deploy)
- **Cron service**: Pings the app every 10 minutes to prevent cold starts
- **Database**: Neon DB (serverless PostgreSQL)
- **Flutter build**: Committed to git, served by Django catch-all view

### Setup (one-time)

1. Create account at [render.com](https://render.com)
2. Create a new Web Service → connect this GitHub repo
3. Configure in the Render dashboard:
   - **Runtime**: Docker
   - **Branch**: `master`
   - **Region**: Singapore (Southeast Asia)
   - **Root directory**: (empty)
   - **Auto-deploy**: On, from master
4. Create a Cron Job (`keep-alive`, `*/10 * * * *`, `curl -s https://backend-erp-jlt9.onrender.com/ > /dev/null`)
5. Set env vars in Render dashboard (see below)

### Environment variables (Render)

| Variable | Value | Source |
|---|---|---|
| `SECRET_KEY` | Auto-generated | Render |
| `DEBUG` | `False` | Render dashboard |
| `ALLOWED_HOSTS` | `backend-erp-jlt9.onrender.com` | Render dashboard |
| `POSTGRES_HOST` | `ep-misty-block-aya29p71-pooler.c-5.us-east-2.aws.neon.tech` | Neon |
| `POSTGRES_PORT` | `5432` | Neon |
| `POSTGRES_DB` | `neondb` | Neon |
| `POSTGRES_USER` | `neondb_owner` | Neon |
| `POSTGRES_PASSWORD` | (from Neon) | Set manually in Render dashboard |
| `DJANGO_SUPERUSER_USERNAME` | (your choice) | Set manually in Render dashboard |
| `DJANGO_SUPERUSER_EMAIL` | (your choice) | Set manually in Render dashboard |
| `DJANGO_SUPERUSER_PASSWORD` | (your choice) | Set manually in Render dashboard |

> **Note:** `POSTGRES_PASSWORD` and `DJANGO_SUPERUSER_*` are not committed to git. Set them manually in Render dashboard.

### Deploy workflow

1. Make changes to Django code
2. If Flutter changed: run `bash scripts/run.sh flutter` and commit `web/build/web/`
3. Commit and push to `master`
4. Render auto-deploys using the Dockerfile
5. `createsuperuser_if_not_exists` runs automatically on deploy

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
Render auto-deploys web service (Docker build)
        ↓
Cron pings app every 10 min (prevents cold starts)
```

### Schema changes in production

Production (Neon) schema is **manual SQL only** — it does not run `migrate`. The standard workflow:

1. Edit the model
2. `makemigrations` + `migrate` on local Docker PostgreSQL (this is a local tool — it produces the schema)
3. Copy the changed table's DDL from **DBeaver** (local DB)
4. Paste that DDL into the **Neon** write replica (SQL Editor or `psql`)
5. For breaking changes (e.g. adding a `NOT NULL` constraint): prepare the data first (run a script so nothing is `NULL`), **deploy the code first**, then apply the DDL change as the **last step** for minimal downtime

> **Never** use `reload_db.sh` against production.
> **Never** rely on prod running `migrate` to change the schema — apply the SQL manually.

---

## Environment Variables (Django settings.py)

| Variable | Read by settings.py | Used in `.env` | Used in `.env.dev` |
|---|---|---|---|
| `POSTGRES_DB` | Yes | Yes | Yes |
| `POSTGRES_USER` | Yes | Yes | Yes |
| `POSTGRES_PASSWORD` | Yes | Yes | Yes |
| `POSTGRES_HOST` | Yes | Yes | Yes (`db` for Docker) |
| `POSTGRES_PORT` | Yes | Yes | Yes |
| `ALLOWED_HOSTS` | Yes | Yes | Yes |
| `SECRET_KEY` | Yes (with fallback) | Yes | Yes |
| `DEBUG` | Yes (with fallback) | Yes | Yes |
| `DJANGO_SUPERUSER_USERNAME` | No (command) | Required on Render | N/A |
| `DJANGO_SUPERUSER_EMAIL` | No (command) | Required on Render | N/A |
| `DJANGO_SUPERUSER_PASSWORD` | No (command) | Required on Render | N/A |

---

## Adding a New Django App

```bash
# Create the app
python manage.py startapp <app_name>

# Add to INSTALLED_APPS in config/settings.py
# Place app at project root (e.g. /authentication, /common)

# Project apps use real Django migrations:
# 1. Write your models
# 2. docker compose exec web python manage.py makemigrations <app_name>
# 3. docker compose exec web python manage.py migrate   # applies to local Docker DB
# Follow "Changing a Table" in skills/database.md to get the SQL onto prod
```
