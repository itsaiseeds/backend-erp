# Conventions

> Code style, patterns, and rules for working on this project.

---

## Project Layout

```
backend-erp/
├── config/             # Django project package (settings, urls, wsgi)
├── api/                # REST API (base views, permissions, sales_admin + android namespaces)
├── authentication/     # Custom User + Admin / SalesPerson models + admin site
├── aggregator/         # Geo master data (Country/State/City/Pincode/Address)
├── common/             # Abstract bases + admin mixins (timestamps, soft delete, created_by)
├── scripts/            # Shell scripts (reload_db.sh, run.sh, entrypoint.sh)
├── sql/                # Full-schema + seed + prod-DDL files (ddl.sql, dml.sql, admin_perf.sql, session_auth_24h.sql)
├── skills/             # Project knowledge base
├── web/                # Flutter admin web app
│   ├── lib/            # Flutter source code
│   └── build/web/      # Flutter build output (committed to git)
├── tests/              # pytest tests (unit + integration)
├── docs/               # knowledge graph + auto-generated OpenAPI spec
├── skills.md           # Skills index
├── .env                # Production env (gitignored)
├── .env.dev            # Local dev env (committed)
├── docker-compose.yml  # Service definitions
├── Dockerfile          # Container build (no Flutter SDK)
└── manage.py           # Django CLI
```

When you create a new Django app, place it at the project root:
```
backend-erp/
├── myapp/
│   ├── __init__.py
│   ├── models.py
│   ├── views.py
│   ├── urls.py
│   └── admin.py
```

---

## Database Conventions

### Schema
- The **entire schema is SQL-managed** — no migration files exist. `sql/ddl.sql`
  is the full-schema reference for every app (built-in + project).
- Always use `CREATE TABLE IF NOT EXISTS`, `BIGSERIAL` PKs, indexes on FK
  columns, wrap in `BEGIN`/`COMMIT`, reference tables first.
- Prod (Neon) schema is applied **manually** — copy DDL out of DBeaver (local
  DB) and paste it into Neon; `migrate` is never part of the workflow.

### Seed Data (DML)
- `sql/dml.sql` seeds content types (14) + permissions (56) + reconciliation
  users (superuser `9999999999` with TOTP, no-TOTP user `8888888888`).
- Always use `ON CONFLICT DO NOTHING` for idempotency
- Always reset sequences with `SELECT setval('table_id_seq', N);`
- Wrap all statements in `BEGIN` / `COMMIT`
- Dev only — never seed production
- `createsuperuser_if_not_exists` additionally guarantees a superuser on fresh
  prod deploys (reads `DJANGO_SUPERUSER_*` or falls back to `9999999999/admin`
  when `DEBUG`).

### Changing a table
1. Edit the model
2. Update `sql/ddl.sql` (and `sql/dml.sql` / `sql/admin_perf.sql` as needed)
3. Rebuild local: `bash scripts/reload_db.sh --step all`
4. Copy the changed table's DDL from DBeaver
5. Apply the SQL manually to Neon (prod)
6. Breaking changes: prepare data → deploy code first → apply the DDL last

---

## Django Conventions

### Settings
- Single `config/settings.py` file (no split base/dev/prod)
- All config from environment variables where possible
- `MIGRATION_MODULES` disables migrations only for built-in `django.*` apps; project apps use normal migrations

### Apps
- Use `python manage.py startapp <name>` to create
- Add to `INSTALLED_APPS` in `config/settings.py`
- Place the app at the project root (e.g. `/aggregator`)
- All apps (built-in and project) are SQL-managed via `sql/ddl.sql`; there are no migration files

### Models
- Project-app models define the real schema, mirrored in `sql/ddl.sql`
- Prod schema is applied manually (edit model → update SQL → DBeaver DDL → Neon)

### Auth / roles
- Login is **TOTP** (authenticator app) for everyone except staff (Django admin
  password login). There is no SMS/OTP request endpoint.
- **Role creation:** only superusers can create Admins; superusers **and**
  Admins can create SalesPeople. The SPA learns this from the
  `can_create_admin` / `can_create_sales_person` fields on the TOTP login response.
- Auth classes live in `api/authentication.py` (`SessionAuthentication`,
  `ExpiringTokenAuthentication` with 24h TTL).

### URLs
- Each app defines its own `urls.py`
- Include app URLs in `api/urls.py` / `config/urls.py`

---

## Code Style

- Follow Django's coding style (PEP 8)
- No comments unless the user explicitly asks for them
- Use meaningful variable/function names
- Keep functions small and focused

---

## Scripts

- All scripts go in `scripts/`
- Use `set -euo pipefail` for fail-fast behavior
- Check prerequisites before running (e.g., Docker running)
- Print clear status messages

---

## Git

- `.env` is gitignored (production secrets)
- `.env.dev` is committed (dev connection params with placeholders)
- `web/build/web/` is committed (Flutter build output — developer responsibility)
- `web/.dart_tool/` is gitignored (Flutter cache)
- Never commit real passwords or secret keys
- Commit messages should be concise and descriptive
- **Only commit, push, or create PRs when explicitly asked** — do not do so automatically after making changes

---

## File Naming

| Type | Convention | Example |
|---|---|---|
| Django apps | lowercase, underscores | `inventory`, `purchase_orders` |
| SQL files | lowercase, uppercase section | `ddl.sql`, `dml.sql` |
| Scripts | lowercase, underscores | `reload_db.sh` |
| Skills docs | lowercase, topic-based | `database.md`, `setup.md` |

---

## Anti-Patterns to Avoid

- Do not create migration files — the schema is managed entirely in `sql/ddl.sql`
- Do not rely on prod running `migrate` to change the schema — apply it manually to Neon
- Do not apply a breaking/restrictive DDL (e.g. `NOT NULL` constraint) before the code and data are ready — deploy first, alter last
- Do not hardcode database credentials in Python files
- Do not run DML/seed SQL against production
- Do not commit `.env` (production secrets)
- Do not push Flutter changes without rebuilding (`bash scripts/run.sh flutter`)
- Do not install Flutter SDK in Docker — the build output is committed to git
- Do not use `/api/test-sentry/` — it was removed in the master merge (no error-tracking probe endpoint)

---

## Testing

### Framework
- **pytest** + **pytest-django** — all tests go in `tests/`

### Running (via `scripts/run.sh`, inside the web container)
```bash
bash scripts/run.sh test               # unit + integration
bash scripts/run.sh test-unit          # unit only
bash scripts/run.sh test-integration   # integration only
bash scripts/run.sh lint               # ruff
bash scripts/run.sh typecheck          # mypy
```

### Writing tests
- Test files: `tests/test_<name>.py`
- Test functions: `def test_<name>():`
- Use `assert` for assertions (pytest style, not `unittest.TestCase`)
- Keep tests simple and focused — one assertion per test when possible
- Every test class/method docstring must state its copy/paste pytest node id
  (see `.agents/skills/run-tests/SKILL.md`)
- Integration tests use `tests/integration/base.py` helpers and build a
  throwaway `django_test` DB from `sql/ddl.sql` + `dml.sql` (then `migrate --fake`)

### CI
- `.github/workflows/tests.yml` runs `test-unit` + `test-integration` + `lint`
  inside the web container on every PR to `master`
- Branch protection requires the `Tests / test` check to pass
