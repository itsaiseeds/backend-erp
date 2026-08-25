# Docker

> Container setup for development and production.

---

## Services

### `web` (Django)

| | |
|---|---|
| **Base image** | `python:3.14-slim` |
| **Dev command** | `python manage.py runserver 0.0.0.0:8000` |
| **Prod command** | `gunicorn --bind 0.0.0.0:8000 config.wsgi:application` |
| **Port** | 8000 |
| **Volume** | `.:/app` (bind mount for live reload) |
| **Env file** | `.env` |
| **Depends on** | `db` (healthy) |

### `db` (PostgreSQL)

| | |
|---|---|
| **Image** | `postgres:18` |
| **Port** | 5432 (mapped to host for DBeaver access) |
| **Volume** | `postgres_data:/var/lib/postgresql` (persistent) |
| **Healthcheck** | `pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}` every 5s |
| **Timezone** | UTC (forced via `postgres -c timezone=UTC`) |

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

The `db` container must already be running. This is useful when you've already started the database separately.

### Rebuild after changes

```bash
docker compose up -d --build
```

Rebuilds the Docker image (after changes to `Dockerfile`, `requirements.txt`, or project code) and restarts.

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
docker collect exec web python manage.py createsuperuser

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

## Dockerfile

```dockerfile
FROM python:3.14-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "config.wsgi:application"]
```

- Good layer caching: `requirements.txt` copied and installed before project code
- Production CMD uses gunicorn (overridden to `runserver` in docker-compose for dev)

---

## Networking

The `web` service connects to `db` via Docker's internal DNS using the service name `db` as the hostname. This is why `.env` (used by Docker Compose) has `POSTGRES_HOST=db`.

The `db` port (5432) is mapped to the host, so you can connect from DBeaver or other tools at `localhost:5432`.

---

## Healthcheck

The `db` service uses:
```
pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}
```

The `web` service waits for this via `depends_on: condition: service_healthy`. This prevents Django from starting before PostgreSQL is ready to accept connections.

---

## Gotchas

- **`web` command override** — docker-compose overrides the Dockerfile CMD with `runserver` for dev. In production, use the Dockerfile's gunicorn CMD.
- **Volume mount** — `.:/app` means local file changes are reflected immediately in the container. This is great for dev but means you must not have stale `.pyc` files (hence `PYTHONDONTWRITEBYTECODE=1`).
- **`postgres_data` volume** — persists even after `docker compose down`. Use `docker compose down -v` to destroy it.
- **Timezone** — PostgreSQL is forced to UTC via `postgres -c timezone=UTC` to avoid the `Asia/Calcutta` error in DBeaver.
