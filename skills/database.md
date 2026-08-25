# Database

> Schema and data management via raw SQL. **No Django migrations.**

---

## Why no migrations?

Django's migration system is disabled via:

```python
MIGRATION_MODULES = {app.split(".")[-1]: None for app in INSTALLED_APPS}
```

This tells Django to never look for or run migrations for any installed app. The database schema is managed entirely through two SQL files:

| File | Purpose | Run in prod? |
|---|---|---|
| `sql/ddl.sql` | Creates tables (schema) | No |
| `sql/dml.sql` | Inserts seed data | No |

**Both files are dev-only.** Production (Neon) manages its schema independently.

---

## SQL Files

### `sql/ddl.sql`

Creates all tables required by Django's built-in apps:

| Table | App |
|---|---|
| `django_migrations` | Django internals (required even with migrations disabled) |
| `django_content_type` | contenttypes |
| `auth_permission` | auth |
| `auth_group` | auth |
| `auth_group_permissions` | auth |
| `auth_user` | auth |
| `auth_user_groups` | auth |
| `auth_user_user_permissions` | auth |
| `django_session` | sessions |
| `django_admin_log` | admin |

Key details:
- All tables use `BIGSERIAL` primary keys (matches `DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'`)
- All `CREATE TABLE IF NOT EXISTS` — safe to re-run
- Wrapped in `BEGIN` / `COMMIT`
- Indexes on all FK columns

### `sql/dml.sql`

Seeds the database with:
1. **6 content types** (one per model Django knows about)
2. **24 permissions** (add/change/delete/view × 6 models)
3. **2 superusers** — `admin` / `admin` and `xZist` / `admin@123`
4. **All 48 permissions** granted to both superusers

Key details:
- All `ON CONFLICT DO NOTHING` — idempotent
- Sequence values explicitly reset via `setval()` after inserts
- Wrapped in `BEGIN` / `COMMIT`

---

## Reload Database

### Commands

```bash
# Full reload: drop all tables + create tables + seed data
bash scripts/reload_db.sh --step all

# Schema only: drop + create tables (no seed data)
bash scripts/reload_db.sh --step ddl

# Seed data only: insert data without dropping tables
bash scripts/reload_db.sh --step dml
```

> **Prerequisite:** The `db` container must be running.
> Start it with: `docker compose up -d`

### What the reload script does

1. Reads connection params from `.env.dev`
2. Checks that Docker and the `db` container are running
3. `--step ddl` or `--step all`: drops all tables in reverse dependency order, then runs `ddl.sql`
4. `--step dml` or `--step all`: runs `dml.sql` to insert seed data
5. All SQL runs inside the Docker `db` container via `docker compose exec`

### When to reload

| Scenario | Command |
|---|---|
| First-time setup | `bash scripts/reload_db.sh --step all` |
| Changed schema (DDL) | `bash scripts/reload_db.sh --step all` |
| Changed seed data (DML) | `bash scripts/reload_db.sh --step all` |
| Need a clean database | `bash scripts/reload_db.sh --step all` |
| Just re-seeding data | `bash scripts/reload_db.sh --step dml` |

---

## Adding a New Table

1. Add `CREATE TABLE` to `sql/ddl.sql` (inside the `BEGIN`/`COMMIT` block)
2. Add any seed `INSERT` to `sql/dml.sql` (inside the `BEGIN`/`COMMIT` block)
3. If the table has an auto-increment ID, add `SELECT setval('table_id_seq', N);` after inserts
4. Run `bash scripts/reload_db.sh --step all`
5. Verify in DBeaver or: `docker compose exec db psql -U django -d django -c "\dt"`

---

## Adding Content Types and Permissions for New Models

When you add a new Django model, you must also add its content type and permissions to `sql/dml.sql`:

```sql
-- Add content type (next available ID)
INSERT INTO django_content_type (id, app_label, model) VALUES
    (7, 'your_app', 'your_model')
ON CONFLICT DO NOTHING;

-- Add permissions (next available IDs)
INSERT INTO auth_permission (id, name, content_type_id, codename) VALUES
    (25, 'Can add your model',    7, 'add_your_model'),
    (26, 'Can change your model', 7, 'change_your_model'),
    (27, 'Can delete your model', 7, 'delete_your_model'),
    (28, 'Can view your model',   7, 'view_your_model')
ON CONFLICT DO NOTHING;

-- Update sequences
SELECT setval('django_content_type_id_seq', 7);
SELECT setval('auth_permission_id_seq', 28);
```

---

## Connection Parameters

| Variable | `.env.dev` (local) | `.env` (Docker/production) |
|---|---|---|
| `POSTGRES_DB` | `django` | `django` |
| `POSTGRES_USER` | `django` | `django` |
| `POSTGRES_PASSWORD` | `change-this-password` | `change-this-password` |
| `POSTGRES_HOST` | `localhost` | `db` |
| `POSTGRES_PORT` | `5432` | `5432` |

The `reload_db.sh` script always reads from `.env.dev` (localhost).

---

## Connecting with DBeaver

| Field | Value |
|---|---|
| Host | `localhost` |
| Port | `5432` |
| Database | `django` |
| Username | `django` |
| Password | `change-this-password` |

> **Note:** The `db` port must be exposed in `docker-compose.yml` for DBeaver to connect.

---

## Gotchas

- **`django_migrations` table must exist** even with migrations disabled — Django queries it internally
- **DML is dev-only** — never run seed scripts against production
- **Sequence resets** — after inserting rows with explicit IDs, always call `setval()` to keep sequences in sync
- **Idempotency** — all inserts use `ON CONFLICT DO NOTHING`, all creates use `IF NOT EXISTS`
- **DB container must be running** — `reload_db.sh` will fail if `docker compose ps db` shows the container is down
