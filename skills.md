# Backend ERP — Skills Index

> Master knowledge base for the Saiseeds Backend ERP project.
> Every file under `skills/` covers one domain. Read them before making changes.

---

## Project at a Glance

| | |
|---|---|
| **Framework** | Django 5.2 LTS |
| **Database** | PostgreSQL 18 |
| **Python** | 3.14 |
| **Container** | Docker Compose (web + db) |
| **Schema management** | Hybrid: Django migrations (project apps) + Raw SQL (built-in apps) |
| **Seed data** | Raw SQL, dev-only (built-in apps); superuser via runtime command |
| **Testing** | pytest + pytest-django |
| **CI/CD** | GitHub Actions → Render |
| **Deployment** | Render (web + cron) + Neon DB (serverless PostgreSQL) |

---

## Files

| File | What it covers |
|---|---|
| [docs/knowledge-graph.md](docs/knowledge-graph.md) | Codebase map: every component, model, route, and how they connect |
| [skills/database.md](skills/database.md) | DDL, DML, reload script, schema conventions |
| [skills/setup.md](skills/setup.md) | Environment files, first-time setup, daily workflow |
| [skills/django.md](skills/django.md) | Settings, apps, middleware, MIGRATION_MODULES |
| [skills/docker.md](skills/docker.md) | Dockerfile, docker-compose, services, volumes |
| [skills/conventions.md](skills/conventions.md) | Code style, patterns, naming, adding new features |

---

## Quick Reference

### Start developing
```bash
bash scripts/run.sh flutter                       # build Flutter web app
docker compose build                              # build the Docker image
docker compose up -d                              # start PostgreSQL + Django
bash scripts/reload_db.sh --step all              # create tables + seed data
# Django is now running at http://localhost:8000/admin/
# Flutter app at http://localhost:8000/sales-admin/
# Login: admin / admin  or  xZist / admin@123
```

### Build Flutter app
```bash
bash scripts/run.sh flutter                       # build for production
```

### Run the Django server
```bash
docker compose up -d                              # start in detached mode
docker compose up                                 # start with logs visible
docker compose up web                             # start only Django (db must be running)
docker compose up -d --build                      # rebuild and start
docker compose restart                            # restart all services
docker compose down                               # stop all services
docker compose down -v                            # stop and destroy database data
```

### Reload the database
```bash
bash scripts/reload_db.sh --step all            # drop + create tables + seed data
bash scripts/reload_db.sh --step ddl            # drop + create tables only
bash scripts/reload_db.sh --step dml            # insert seed data only
```

### Check status and logs
```bash
docker compose ps                               # show container status
docker compose logs -f                          # tail all logs
docker compose logs -f web                      # tail Django logs only
docker compose logs -f db                       # tail PostgreSQL logs only
```

### Run management commands
```bash
docker compose exec web python manage.py shell
docker compose exec web python manage.py createsuperuser
docker compose exec web python manage.py collectstatic
```

### Change a table (local + prod)
1. Edit the model (`authentication/models/*.py`, `common/models/*.py`)
2. Migrate on local:
   - `docker compose exec web python manage.py makemigrations <app>`
   - `docker compose exec web python manage.py migrate`
3. Copy the changed table's DDL from DBeaver (local Docker DB)
4. Paste the DDL into the Neon / prod write replica (prod schema is manual SQL only)
5. For breaking changes: prepare data → **deploy code first** → apply the DDL as the **last step**

### Key files you will touch often
- `config/settings.py` — Django config
- `sql/ddl.sql` — schema
- `sql/dml.sql` — seed data
- `scripts/reload_db.sh` — DB management script
- `scripts/run.sh` — single entry point for all commands (including Flutter build)
- `web/lib/` — Flutter admin app source code
- `web/build/web/` — Flutter build output (committed to git)
- `.env.dev` — local connection params
- `docker-compose.yml` — service definitions
- `Dockerfile` — container build (no Flutter SDK)
- `tests/` — test files

### Run tests
```bash
pytest                                      # run all tests
pytest -v                                   # verbose output
pytest tests/test_sample.py                 # run specific file
```

### Run management commands
```bash
docker compose exec web python manage.py createsuperuser_if_not_exists  # idempotent superuser creation
docker compose exec web python manage.py shell                          # Django shell
docker compose exec web python manage.py createsuperuser                # interactive superuser creation
```

### Deploy to Render
- Push to `master` → Render auto-deploys (Docker build)
- Flutter build is committed to git — no Flutter SDK in Docker
- If Flutter changed: run `bash scripts/run.sh flutter` and commit `web/build/web/` before pushing
- First deploy: run initial schema against Neon via Neon SQL Editor or psql
- Set `POSTGRES_PASSWORD` and `DJANGO_SUPERUSER_*` in Render dashboard
- `createsuperuser_if_not_exists` runs automatically on deploy (idempotent)
- Cron pings app every 10 min to prevent cold starts
