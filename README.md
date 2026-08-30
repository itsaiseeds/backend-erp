# SaiSeeds Backend ERP

Backend API for the SaiSeeds **sales-administration web app** (Flutter) and the **salesperson Android app**.

- **Django** 5.2 LTS + **Django REST Framework** REST API
- **PostgreSQL** 18 via **Docker Compose** locally, **Neon** (serverless Postgres) in production
- **Flutter** admin web app served by the same Django process
- **OTP-based** authentication (no passwords for non-superusers; superusers log in with password / Django admin)
- Auto-generated **OpenAPI/Swagger** docs, container-native **pytest** suite, **GitHub Actions** CI gating merges to `master`

> Start with the **[knowledge graph](docs/knowledge-graph.md)** to navigate the
> codebase, then read **[skills/](skills.md)** for workflow-level detail.

---

## Tech stack

| Layer | Choice |
|---|---|
| Framework | Django 5.2 LTS, DRF 3.15, drf-spectacular |
| Python | 3.14 (container) |
| Database | PostgreSQL 18 (dev/compose), Neon (prod) |
| web / app server | gunicorn (container entrypoint) |
| Frontends | Flutter web build (committed to repo, `/sales-admin/`) + Android app (API client) |
| Tooling | ruff (lint), mypy + django-stubs (typecheck), pytest + pytest-django (tests) |
| Infra | Docker Compose, GitHub Actions, Render, Neon |

## Repository layout

```
config/            Django project (settings, urls, wsgi, Flutter catch-all)
api/               REST API: flag-driven base views, permissions, namespaces
  ├── sales_admin/     admin website endpoints (OTP auth flow)
  └── android/         Android app API (v1, being built)
authentication/    Custom user + Admin / SalesPerson / MobileVerification models
common/            Abstract base models (timestamps, soft delete, public/random id)
sql/               ddl.sql (full schema) + dml.sql (seed data) — dev reference
scripts/           run.sh (all commands), reload_db.sh, entrypoint.sh, integration_db.sh
tests/             pytest: unit + live-server integration suite
web/               Flutter admin app source + committed build output
docs/              knowledge graph + auto-generated API reference
skills/            domain knowledge (setup, database, conventions, …)
```

See [docs/knowledge-graph.md](docs/knowledge-graph.md) for the full component
map and relationships.

## Prerequisites

- Docker & Docker Compose
- Flutter SDK (only when rebuilding the admin web app)
- Git for Windows / Git Bash (scripts are `bash`)

## Quickstart

```bash
# 1. Build the Flutter admin web app (once, or after web/lib changes)
bash scripts/run.sh flutter

# 2. Build + start everything (Django + PostgreSQL)
docker compose up -d --build

# 3. Create tables + seed data
bash scripts/reload_db.sh --step all

# 4. Open the app
#    http://localhost:8000/admin/          Django admin
#    http://localhost:8000/sales-admin/    Flutter admin app
#    http://localhost:8000/api/docs/       Swagger UI
```

The first superuser is created on container start by
`createsuperuser_if_not_exists` (dev fallback: `9999999999` / `admin`), or use the Django admin's superuser flow.

## Daily workflow

| Task | Command |
|---|---|
| Build Flutter app | `bash scripts/run.sh flutter` |
| Start services | `bash scripts/run.sh up` |
| Stop | `bash scripts/run.sh down` |
| Status / logs | `bash scripts/run.sh status` / `bash scripts/run.sh logs` |
| Reload local DB | `bash scripts/run.sh reload-db` (or `bash scripts/reload_db.sh --step all`) |
| Django shell | `bash scripts/run.sh shell` |
| psql | `bash scripts/run.sh psql` |
| Regenerate API docs | `bash scripts/run.sh schema` (writes `docs/api/openapi.yml`) |

After changing `requirements.txt` or the `Dockerfile`, rebuild the image:
`docker compose build` (the running container is not updated in place).

## Tests

All tests run **inside the `web` Python image** in short-lived one-off
containers — the host Python never needs Django (start the `db` service with
`docker compose up -d db` first).

| What | Command |
|---|---|
| Everything | `bash scripts/run.sh test` |
| Unit only | `bash scripts/run.sh test-unit` |
| All integration | `bash scripts/run.sh test-integration` |
| One class | `bash scripts/run.sh test-integration tests/integration/test_auth_flow.py::AuthFlowTest` |
| One test | `bash scripts/run.sh test-integration tests/integration/test_auth_flow.py::AuthFlowTest::test_generate_otp_returns_200` |
| Lint / typecheck | `bash scripts/run.sh lint` / `bash scripts/run.sh typecheck` |

Integration tests build a throwaway `django_test` DB from `sql/ddl.sql` +
`sql/dml.sql`, `migrate --fake`, start a real Django server on `127.0.0.1:8001`,
and exercise the endpoints over HTTP.

Inside VS Code, use **Run Task...**: `test`, `test: unit`,
`test-integration: all tests`, or `test-integration: pick a test` (paste a pytest
node id, e.g. `tests/integration/test_auth_flow.py::AuthFlowTest`).

> Convention: every test class/method docstring states its copy/paste pytest
> node id. Full details run flows in the `run-tests` skill.

## Database & schema management

Hybrid model: **Django migrations for project apps** (`authentication`, `common`,
`config`), **raw SQL for built-in Django apps** (`sql/ddl.sql` + `sql/dml.sql`,
controlled by `MIGRATION_MODULES`).

- Local schema: `makemigrations` + `migrate`, or `bash scripts/reload_db.sh --step all`.
- **Production (Neon) schema is manual SQL only** — `migrate` never changes prod.
  Changes flow: edit model → migrate locally → copy the DDL from DBeaver → apply
  it manually to the Neon write replica. Breaking changes: prepare data, **deploy
  code first**, apply the DDL **last**.
- `reload_db.sh` targets **local Docker PostgreSQL only** and can never touch prod.

See [skills/database.md](skills/database.md) for the full workflow.

## Authentication model

- Custom `User` with `phone_number` (10 digits) as the login username.
- **OTP login** for everyone except superusers: `POST /api/sales_admin/auth/otp/request`
  then `POST /api/sales_admin/auth/otp/verify` (returns a DRF `Token`).
- Rolles: **superuser** (password, Django admin), **Admin** (session cookie on the
  web app), **SalesPerson** (bearer token on Android). Role gates live in
  `api/permissions.py` and the flag-driven `BaseApiView`.

## CI/CD & release

- **CI** — `.github/workflows/tests.yml` runs unit tests, integration tests, and
  lint on every PR to `master` in Docker.
- **Merge gate** — branch protection on `master` blocks merges until the
  `Tests / test` status check passes (and requires a PR approval).
- **Deploy** — push to `master` → Render auto-deploys the Docker image
  (gunicorn). A keep-alive cron pings the app every 10 minutes to avoid cold starts.
- **Flutter** — the build in `web/build/web/` is committed; always rebuild it
  before pushing Flutter changes.

## Environment variables

Read by `config/settings.py` (fallbacks exist for `SECRET_KEY`/`DEBUG`/`ALLOWED_HOSTS`):

| Variable | Dev (`docker-compose.yml`) | Prod (Neon/Render) |
|---|---|---|
| `POSTGRES_DB` | `django` | `neondb` |
| `POSTGRES_USER` | `django` | `neondb_owner` |
| `POSTGRES_PASSWORD` | `change-this-password` | from Neon (Render dashboard) |
| `POSTGRES_HOST` | `db` (service name) | from Neon |
| `POSTGRES_PORT` | `5432` | `5432` |
| `ALLOWED_HOSTS` | `localhost,127.0.0.1` | `backend-erp-jlt9.onrender.com` |
| `CORS_ALLOWED_ORIGINS` | (empty) | admin web origin |
| `DJANGO_SUPERUSER_*` | (dev fallback) | from Render dashboard |

`.env.dev` (committed, placeholders) feeds Docker Compose; `.env` (gitignored)
holds production/Neon secrets.

## Safety rules

- `reload_db.sh` and `sql/*.sql` **never run against production.**
- Prod schema changes are **manual SQL on Neon**, applied last for breaking changes.
- No real secrets in git: `.env` is ignored; use env vars / Render dashboard.
- `migrate` runs locally only — never rely on prod running it.

## Further reading

- [Knowledge graph — codebase map](docs/knowledge-graph.md)
- [Skills index](skills.md) — setup, database, conventions, Docker, Django

- [API reference](docs/api/openapi.yml) / [Swagger UI](http://localhost:8000/api/docs/)