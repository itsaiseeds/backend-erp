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
| **Schema management** | Raw SQL (no Django migrations) |
| **Seed data** | Raw SQL, dev-only |
| **Testing** | pytest + pytest-django |
| **CI/CD** | GitHub Actions → Render |
| **Deployment** | Render (web + cron) + Neon DB (serverless PostgreSQL) |

---

## Files

| File | What it covers |
|---|---|
| [skills/database.md](skills/database.md) | DDL, DML, reload script, schema conventions |
| [skills/setup.md](skills/setup.md) | Environment files, first-time setup, daily workflow |
| [skills/django.md](skills/django.md) | Settings, apps, middleware, MIGRATION_MODULES |
| [skills/docker.md](skills/docker.md) | Dockerfile, docker-compose, services, volumes |
| [skills/conventions.md](skills/conventions.md) | Code style, patterns, naming, adding new features |

---

## Quick Reference

### Start developing
```bash
docker compose build                            # build the image
docker compose up -d                            # start PostgreSQL + Django
bash scripts/reload_db.sh --step all            # create tables + seed data
# Django is now running at http://localhost:8000/admin/
# Login: admin / admin  or  xZist / admin@123
```

### Run the Django server
```bash
docker compose up -d                            # start in detached mode
docker compose up                               # start with logs visible
docker compose up web                           # start only Django (db must be running)
docker compose up -d --build                    # rebuild and start
docker compose restart                          # restart all services
docker compose down                             # stop all services
docker compose down -v                          # stop and destroy database data
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

### Add a new table
1. Write `CREATE TABLE` in `sql/ddl.sql`
2. Write any seed `INSERT`s in `sql/dml.sql`
3. Run `bash scripts/reload_db.sh --step all`
4. Update this skills index if the change is architectural

### Key files you will touch often
- `config/settings.py` — Django config
- `sql/ddl.sql` — schema
- `sql/dml.sql` — seed data
- `scripts/reload_db.sh` — DB management script
- `scripts/run.sh` — single entry point for all commands
- `.env.dev` — local connection params
- `docker-compose.yml` — service definitions
- `render.yaml` — Render deployment blueprint
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
- Push to `master` → Render auto-deploys
- First deploy: run initial schema against Neon via Neon SQL Editor or psql
- Set `POSTGRES_PASSWORD` in Render dashboard (not in render.yaml)
- `createsuperuser_if_not_exists` runs automatically on deploy (idempotent)
- Cron pings app every 10 min to prevent cold starts
