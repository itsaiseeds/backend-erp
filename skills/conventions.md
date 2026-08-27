# Conventions

> Code style, patterns, and rules for working on this project.

---

## Project Layout

```
backend-erp/
├── config/             # Django project package (settings, urls, wsgi)
├── scripts/            # Shell scripts (reload_db.sh, run.sh, entrypoint.sh)
├── sql/                # Raw SQL files (ddl.sql, dml.sql)
├── skills/             # Project knowledge base
├── web/                # Flutter admin web app
│   ├── lib/            # Flutter source code
│   └── build/web/      # Flutter build output (committed to git)
├── tests/              # pytest tests
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
- Project apps (`authentication`, `common`, `config`) use **Django migrations** — run `makemigrations` + `migrate` locally
- Built-in Django apps use **raw SQL** in `sql/ddl.sql` (their migrations stay disabled)
- For built-in apps: always use `CREATE TABLE IF NOT EXISTS`, `BIGSERIAL` PKs, indexes on FK columns, wrap in `BEGIN`/`COMMIT`, reference tables first
- Prod (Neon) schema is applied **manually** — migrate runs only locally

### Seed Data (DML)
- `sql/dml.sql` seeds reference data for built-in apps (content types + permissions)
- Always use `ON CONFLICT DO NOTHING` for idempotency
- Always reset sequences with `SELECT setval('table_id_seq', N);`
- Wrap all statements in `BEGIN` / `COMMIT`
- Dev only — never seed production
- The superuser is created at runtime by `createsuperuser_if_not_exists` — do not seed it via SQL

### Changing a table
1. Edit the model
2. `makemigrations` + `migrate` on local Docker
3. Copy the changed table's DDL from DBeaver
4. Apply the SQL manually to Neon (prod)
5. Breaking changes: prepare data → deploy code first → apply the DDL last

---

## Django Conventions

### Settings
- Single `config/settings.py` file (no split base/dev/prod)
- All config from environment variables where possible
- `MIGRATION_MODULES` disables migrations only for built-in `django.*` apps; project apps use normal migrations

### Apps
- Use `python manage.py startapp <name>` to create
- Add to `INSTALLED_APPS` in `config/settings.py`
- Project apps get real migrations; built-in apps stay SQL-managed via `MIGRATION_MODULES`

### Models
- Project-app models define the real schema — generated via migrations
- Prod schema is applied manually (local migrate → DBeaver DDL → Neon)

### URLs
- Each app defines its own `urls.py`
- Include app URLs in `config/urls.py`

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

- Do not run `makemigrations` for a built-in `django.*` app — their schema is in `sql/ddl.sql`
- Do not rely on prod running `migrate` to change the schema — apply it manually to Neon
- Do not apply a breaking/restrictive DDL (e.g. `NOT NULL` constraint) before the code and data are ready — deploy first, alter last
- Do not hardcode database credentials in Python files
- Do not manage built-in-app schema outside of `sql/ddl.sql`; do not create built-in-app tables from migrations
- Do not add built-in-app seed data outside of `sql/dml.sql`
- Do not run DML/seed SQL against production
- Do not commit `.env` (production secrets)
- Do not push Flutter changes without rebuilding (`bash scripts/run.sh flutter`)
- Do not install Flutter SDK in Docker — the build output is committed to git

---

## Testing

### Framework
- **pytest** + **pytest-django** — all tests go in `tests/`

### Running tests
```bash
pytest              # run all tests
pytest -v           # verbose output
pytest tests/test_sample.py   # run a specific file
```

### Writing tests
- Test files: `tests/test_<name>.py`
- Test functions: `def test_<name>():`
- Use `assert` for assertions (pytest style, not `unittest.TestCase`)
- Keep tests simple and focused — one assertion per test when possible

### CI
- GitHub Actions runs `pytest` on every PR to `master`
- PRs cannot merge if tests fail
- Enable branch protection: require the `tests` status check to pass

### Where to put tests
```
tests/
├── __init__.py
├── test_sample.py       # trivial sanity tests
└── test_<app_name>.py   # app-specific tests (when apps exist)
```
