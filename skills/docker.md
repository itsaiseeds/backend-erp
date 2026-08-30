# Docker

> Container setup for development and production.

---

## Services

### `web` (Django)

| | |
|---|---|
| **Base image** | `python:3.14-slim` |
| **Dev command** | `scripts/entrypoint.sh` (gunicorn) |
| **Port** | 8000 |
| **Volume** | `.:/app` (bind mount) |
| **Env file** | `.env.dev` |
| **Depends on** | `db` (healthy) |

### `db` (PostgreSQL)

| | |
|---|---|
| **Image** | `postgres:18` |
| **Port** | 5432 (mapped to host for DBeaver access) |
| **Volume** | `postgres_data:/var/lib/postgresql` (persistent) |
| **Command** | `postgres -c timezone=UTC -c shared_buffers=128MB` (caps shared buffers so Postgres doesn't auto-tune to ~25% of host RAM and OOM small CI runners) |
| **Healthcheck** | `pg_isready -U django -d django` (5s interval) |

---

## Running the Django Server

### Start all services

```bash
docker compose up -d
```

This starts both the Django web server and PostgreSQL. Django is available at `http://localhost:8000/admin/`.

### Start and see logs

```bash
docker compose up
```

Same as above but keeps the terminal attached so you can see log output.

### Start only the Django server

```bash
docker compose up web
```

The `db` container must already be running.

### Rebuild after changes

```bash
docker compose up -d --build
```

Rebuilds the Docker image and restarts. The Flutter build in `web/build/web/` is copied into the image — no Flutter SDK needed in Docker.

### Restart services

```bash
docker compose restart
```

### Stop services

```bash
docker compose down
```

### Stop and destroy database data

```bash
docker compose down -v
```

---

## Reloading the Database

```bash
# Full reload: drop tables + create tables + seed data
bash scripts/reload_db.sh --step all

# Schema only: drop + create tables
bash scripts/reload_db.sh --step ddl

# Seed data only: insert data
bash scripts/reload_db.sh --step dml
```

> **Prerequisite:** The `db` container must be running (`docker compose up -d`).

---

## Checking Service Status

```bash
# Show all containers
docker compose ps

# View all logs
docker compose logs -f

# View only web logs
docker compose logs -f web

# View only db logs
docker compose logs -f db
```

---

## Running Django Management Commands

```bash
# Open Django shell
docker compose exec web python manage.py shell

# Create a superuser
docker compose exec web python manage.py createsuperuser

# Collect static files
docker compose exec web python manage.py collectstatic

# Any other management command
docker compose exec web python manage.py <command>
```

---

## Accessing PostgreSQL Directly

```bash
# Open psql inside the db container
docker compose exec db psql -U django -d django

# Or connect from DBeaver on localhost:5432
```

---

## Volumes

| Volume | Purpose |
|---|---|
| `postgres_data` | PostgreSQL data persistence across container restarts |

---

## Container entrypoint (`scripts/entrypoint.sh`)

At startup the container does (in order):

1. `collectstatic --noinput`
2. `createsuperuser_if_not_exists` (idempotent)
3. Start the server:
   - `DEBUG` truthy (as in `.env.dev`) → `python manage.py runserver 0.0.0.0:8000`
     (dev live reload, works on the bind mount)
   - otherwise → `gunicorn --workers ${GUNICORN_WORKERS:-1} --threads ${GUNICORN_THREADS:-4} config.wsgi:application`

**`migrate` is commented out** — the schema is pre-applied SQL (see
`skills/database.md`). Invoked via `bash` so it needs no `+x` bit:
`ENTRYPOINT ["bash", "scripts/entrypoint.sh"]`.

## Dockerfile

```dockerfile
FROM python:3.14-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt
COPY . .
RUN chmod +x scripts/entrypoint.sh
ENV POSTGRES_DB=django
ENV POSTGRES_USER=django
ENV POSTGRES_PASSWORD=placeholder
ENV POSTGRES_HOST=localhost
ENV POSTGRES_PORT=5432
EXPOSE 8000
ENTRYPOINT ["bash", "scripts/entrypoint.sh"]
```

- Flutter build (`web/build/web/`) is committed to git — no Flutter SDK in Docker
- `collectstatic` / `migrate` **do not run during the build** (the DB isn't
  reachable from the build context); the entrypoint runs them at startup
- Good layer caching: `requirements.txt` copied and installed before project code

---

## Networking

The `web` service connects to `db` via Docker's internal DNS using the service name `db` as the hostname. This is why `.env.dev` has `POSTGRES_HOST=db`.

The `db` port (5432) is mapped to the host, so you can connect from DBeaver at `localhost:5432`.

---

## Healthcheck

The `db` service uses:
```
pg_isready -U django -d django
```

The `web` service waits for this via `depends_on: condition: service_healthy`.

---

## Gotchas

- **Volume mount** — `.:/app` means local file changes are reflected immediately in the container.
- **`postgres_data` volume** — persists even after `docker compose down`. Use `docker compose down -v` to destroy it.
- **Timezone** — the `db` container runs with `timezone=UTC`; Django's app-level `TIME_ZONE` is `Asia/Kolkata` (set in `config/settings.py` + the DB `-c timezone` option).
- **`shared_buffers=128MB`** — deliberate cap so Postgres doesn't OOM small CI runners.
- **`migrate` is commented out of the entrypoint** — schema comes from the SQL files, never from migrations.
- **Dev vs prod server** — DEBUG truthy runs `runserver` (auto-reload on the bind mount); prod runs gunicorn.
- **Flutter build** — Run `bash scripts/run.sh flutter` locally before `docker compose build` if you've changed Flutter code.
