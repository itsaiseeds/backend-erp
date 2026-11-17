# SaiSeeds Backend ERP

Backend API for the SaiSeeds **sales-administration web app** (Flutter) and the **salesperson Android app**.

- **Django** 5.2 LTS + **Django REST Framework** REST API
- **PostgreSQL** 18 via **Docker Compose** locally, **Neon** (serverless Postgres) in production
- **Flutter** admin web app served by the same Django process
- **OTP-based** authentication: everyone except staff logs in with a **TOTP
  code from an authenticator app** (no passwords); staff use the Django admin password login
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
authentication/    Custom user + Admin / SalesPerson models (TOTP login)
aggregator/        Geo master data: Country / State / City / Pincode / Address
common/            Abstract base models + admin mixes (timestamp, soft delete, created_by)
sql/               ddl.sql (full schema) + dml.sql (seed data) — dev reference
scripts/           run.sh (all commands), reload_db.sh, entrypoint.sh
tests/             pytest unit and DML-backed Django tests
admin_saiseeds/    Flutter admin app source + committed build output
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
# 1. Build the Flutter admin web app (once, or after admin_saiseeds/lib changes)
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
| All tests | `bash scripts/run.sh test` |
| Unit tests | `bash scripts/run.sh test-unit` |
| DML-backed Django tests | `bash scripts/run.sh test-dml` |
| One unit test | `docker compose run --rm --no-deps --entrypoint "" -T web python -m pytest tests/test_verify_otp_view.py::VerifyOTPTest::test_superuser_can_verify_otp_and_receive_credentials -v` |
| Lint / typecheck | `bash scripts/run.sh lint` / `bash scripts/run.sh typecheck` |

Inside VS Code, use **Run Task...**: `test`, `test: unit`, or
`test: DML-backed Django`.

> Convention: every test class/method docstring states its copy/paste pytest
> node id. Full details run flows in the `run-tests` skill.

## Database & schema management

**Raw SQL only.** There are no migration files — `sql/ddl.sql` is the
full-schema reference for every app (built-in and project), and `sql/dml.sql`
seeds content types, permissions, and reconciliation users.

- Local schema changes: edit the model → update `sql/*.sql` →
  `bash scripts/reload_db.sh --step all`.
- **Production (Neon) schema is manual SQL only** — `migrate` never changes prod
  (it is commented out of the entrypoint; tests use `migrate --fake` against the
  pre-built DDL schema). Changes flow: edit model → update `sql/ddl.sql` →
  copy the DDL from DBeaver → apply it manually to the Neon write replica.
  Breaking changes: prepare data, **deploy code first**, apply the DDL **last**.
- Additional prod DDL lives in `sql/admin_perf.sql` (admin `ILIKE` indexes) and
  `sql/session_auth_24h.sql` (token FK + TTL indexes).
- `reload_db.sh` targets **local Docker PostgreSQL only** and can never touch prod.

See [skills/database.md](skills/database.md) for the full workflow.

## Authentication model

- Custom `User` with `phone_number` (10 digits) as the login username.
- Non-staff users log in with a **TOTP code**: `POST
  /api/sales-admin/auth/otp/verify` (body `phone_number` + `otp`) returns a DRF
  `Token`, opens a browser session (`sessionid` + `csrftoken` cookies), and
  reports the SPA's role-creation rights (`can_create_admin`,
  `can_create_sales_person`). There is no SMS/OTP request endpoint.
- Roles: **superuser** (Django admin password + TOTP), **Admin** (session cookie
  on the web app, only superusers create them), **SalesPerson** (bearer token on
  Android, superusers *and* Admins create them). Role gates live in
  `api/permissions.py` and the flag-driven `BaseApiView`; bearer tokens expire
  after `TOKEN_TTL_HOURS` (24h).

## CI/CD & release

- **CI** — `.github/workflows/tests.yml` runs unit tests, DML-backed Django tests, and
  lint on every PR to `master` in Docker.
- **Merge gate** — branch protection on `master` blocks merges until the
  `Tests / test` status check passes (and requires a PR approval).
- **Deploy** — push to `master` → Render auto-deploys the Docker image
  (gunicorn). A keep-alive cron pings the app every 10 minutes to avoid cold starts.
- **Deploy (AWS)** — push to `master` also runs `.github/workflows/deploy-aws.yml`,
  independent of Render: it rebuilds the Flutter app for the AWS API host, builds
  the image on the runner, ships it over SSH and swaps the container on the EC2 host
  (rolls back if Django doesn't come up). Skipped while the `AWS_API_HOST`
  repository variable is unset. See **AWS (EC2 + nginx)** below.
- **Flutter** — the build in `admin_saiseeds/build/web/` is committed; always rebuild it
  before pushing Flutter changes.

### AWS (EC2 + nginx)

One EC2 instance (Amazon Linux 2023, x86_64) runs gunicorn in Docker behind host nginx.
Postgres stays on Neon and images on Supabase. Files live in `deploy/aws/`; the
instance, volume and Elastic IP are set up by hand (no IaC).

There is no domain yet, so the API is served at `https://<elastic-ip>` with a Let's
Encrypt **IP certificate**. These last only 6 days; the certbot timer renews them
over port 80, so port 80 must stay open and the Elastic IP must never be released
(the apps have it baked in). When a domain exists, point its A record at the IP,
re-run `bootstrap.sh <domain> <email>`, and update `AWS_API_HOST`, `ALLOWED_HOSTS`
and `CSRF_TRUSTED_ORIGINS`.

1. Launch the instance and attach the Elastic IP. Security group: 80 and 443 from
   anywhere, 22 from your IP only.
2. Copy `deploy/aws/` to the box and run `bootstrap.sh` once (installs Docker,
   nginx, certbot, swap and log caps; gets the certificate):

   ```bash
   scp -r deploy/aws ec2-user@<ip>:~/aws-setup
   ssh ec2-user@<ip> 'sudo bash ~/aws-setup/bootstrap.sh <elastic-ip> <email>'
   ```

3. Fill in `/opt/saiseeds/.env` on the box (template: `deploy/aws/env.example`).
4. Create an SSH key pair for CI, add its public key to `~ec2-user/.ssh/authorized_keys`,
   and set in GitHub → Settings → Secrets and variables → Actions:

   | Name | Kind | Value |
   |---|---|---|
   | `AWS_API_HOST` | variable | Elastic IP (or the domain, later) |
   | `EC2_HOST` | secret | Elastic IP |
   | `EC2_USER` | secret | `ec2-user` |
   | `EC2_SSH_KEY` | secret | the CI private key |
   | `EC2_KNOWN_HOSTS` | secret | output of `ssh-keyscan <EC2_HOST>` |

5. Run **Deploy AWS** from the Actions tab (or push to `master`).

On the box: `docker compose -f /opt/saiseeds/docker-compose.prod.yml logs -f web`
for logs; `.env` changes need `... up -d --force-recreate web`;
`sudo certbot renew --dry-run` checks certificate renewal.

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
| `SUPABASE_URL` | (empty → local disk) | Supabase project URL |
| `FCM_SERVICE_ACCOUNT_JSON` | (empty → pushes skipped) | Contents of the Firebase service-account key; enables order push notifications to the Android app (secret) |
| `FCM_PROJECT_ID` | `sales-saiseeds` | Firebase project id |
| `FCM_ANDROID_CHANNEL_ID` | `order_updates` | Notification channel the app creates for order updates |
| `SUPABASE_SECRET_KEY` | (empty → local disk) | Supabase secret key |
| `SUPABASE_STORAGE_BUCKET` | `product-images` | `product-images` (public bucket) |

`.env.dev` (committed, placeholders) feeds Docker Compose; `.env` (gitignored)
holds production/Neon secrets.

Product images have two storage backends, chosen by whether Supabase is
configured (`common/storage/images.py`):

- **`SUPABASE_*` set** — the file goes to a **public** Supabase Storage bucket and
  only its URL is stored on the row (`Product.image_url`). Deployed environments
  must use this: Render's filesystem is ephemeral, so local files die with the
  container. `manage.py check` warns (`common.W001`) when `DEBUG` is off and the
  credentials are missing.
- **`SUPABASE_*` empty** — the file is written under `MEDIA_ROOT` (`media/`,
  gitignored) and `image_url` holds a `MEDIA_URL`-relative path. The dev server
  serves it; the test suite uses a temp `MEDIA_ROOT` per test
  (`tests/conftest.py`). This is the development and CI default, so uploads work
  out of the box with no Supabase account.

## Safety rules

- `reload_db.sh` and `sql/*.sql` **never run against production.**
- Prod schema changes are **manual SQL on Neon**, applied last for breaking changes.
- No real secrets in git: `.env` is ignored; use env vars / Render dashboard.
- `migrate` runs locally only — never rely on prod running it.

## Further reading

- [Knowledge graph — codebase map](docs/knowledge-graph.md)

- [Skills index](skills.md) — setup, database, conventions, Docker, Django

- [API reference](docs/api/openapi.yml) / [Swagger UI](http://localhost:8000/api/docs/)
