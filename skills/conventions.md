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

### Schema (DDL)
- One `CREATE TABLE` per model, in `sql/ddl.sql`
- Always use `CREATE TABLE IF NOT EXISTS`
- Always use `BIGSERIAL` for auto-increment primary keys
- Always add indexes on FK columns
- Wrap all statements in `BEGIN` / `COMMIT`
- Place tables in dependency order (referenced tables first)

### Seed Data (DML)
- One `INSERT` block per model, in `sql/dml.sql`
- Always use `ON CONFLICT DO NOTHING` for idempotency
- Always reset sequences with `SELECT setval('table_id_seq', N);`
- Wrap all statements in `BEGIN` / `COMMIT`
- Dev only — never seed production

### Adding a new model
1. Write `CREATE TABLE` in `sql/ddl.sql`
2. Add content type row to `sql/dml.sql` (if Django needs to know about it)
3. Add permissions to `sql/dml.sql` (4 per model: add/change/delete/view)
4. Add any seed data to `sql/dml.sql`
5. Run `bash scripts/reload_db.sh --step all`

---

## Django Conventions

### Settings
- Single `config/settings.py` file (no split base/dev/prod)
- All config from environment variables where possible
- `MIGRATION_MODULES` auto-disables migrations for all apps

### Apps
- Use `python manage.py startapp <name>` to create
- Add to `INSTALLED_APPS` in `config/settings.py`
- Migrations are automatically disabled by `MIGRATION_MODULES`

### Models
- Write models as documentation/reference — the actual schema is in SQL
- Models must match the SQL schema exactly (same column names, types, constraints)

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

- Do not run `makemigrations` or `migrate` — migrations are disabled
- Do not run DML SQL against production
- Do not hardcode database credentials in Python files
- Do not create tables outside of `sql/ddl.sql`
- Do not add seed data outside of `sql/dml.sql`
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
