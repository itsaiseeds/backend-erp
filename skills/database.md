# Database

> Schema management for the Backend ERP project — a hybrid of Django migrations (project apps) and raw SQL (built-in Django apps).

---

## Schema Management Model

Schema is managed with a **hybrid** approach:

| Target | Managed by | Mechanism |
|---|---|---|
| Project apps (`authentication`, `common`, `config`) | **Django migrations** | `makemigrations` + `migrate` |
| Built-in Django apps (`auth`, `contenttypes`, `sessions`, `admin`) | **Raw SQL** | `sql/ddl.sql` + `sql/dml.sql` |

This is controlled in `config/settings.py`:

```python
# Built-in Django apps' schema is managed via sql/ddl.sql -> keep their
# migrations disabled. Our own apps (authentication, common, config) use
# normal Django migrations.
MIGRATION_MODULES = {
    app.split(".")[-1]: None for app in INSTALLED_APPS if app.startswith("django.")
}
```

So migrations run **only** for the project's own apps. `python manage.py migrate` runs at container startup via `scripts/entrypoint.sh`.

---

## Two Environments, Two Different Schema Paths

| | Local (Docker PostgreSQL) | Production (Neon) |
|---|---|---|
| Tables are created | **Django migrations** run against the local DB | Schema applied **manually via SQL** (Neon does **not** run `migrate`) |
| How | `docker compose exec web python manage.py migrate` | Paste DDL into the Neon SQL Editor / write replica |
| Source of truth for containers | committed `migrations/` files | manual SQL derived from local |

**Key rule:** `migrate` is only ever run on the **local** Docker database. Production schema is changed **only** by you pasting SQL manually. Migrations are used locally as a **tool to produce the SQL** that you then apply to Neon.

---

## Changing a Table (Models → Prod)

This is the standard workflow for adding or changing a table, on **both** local and prod.

### 1. Create / Edit the model

Edit the model class (e.g. `authentication/models/user.py`, or a `common/models/*.py` base).

### 2. Migrate on the local server

Generate + apply migrations against the local Docker PostgreSQL:

```bash
# inside the web container (recommended)
docker compose exec web python manage.py makemigrations <app_name>
docker compose exec web python manage.py migrate
```

Or directly with the venv Python used for local management commands:

```bash
python manage.py makemigrations <app_name>
python manage.py migrate
```

This applies the schema change to the **local** Docker database. The migration also runs in prod at deploy via `entrypoint.sh` — **but** prod schema is controlled by you manually (see next steps), so treat the local run as producing the authoritative DDL.

### 3. Generate the SQL from DBeaver

Open the changed table in **DBeaver** (connected to the local Docker DB) and copy its **table DDL** (DBeaver → table → SQL → DDL). This gives the `CREATE TABLE` / `ALTER TABLE` statements your model change produced.

> `sql/ddl.sql` is the local reference for the built-in Django-app tables. Keep it in sync if the change touches one of them. Project-app table DDL lives in the committed migrations, but the DDL you extract from DBeaver is what you run on prod.

### 4. Apply the same SQL to production

Paste the DDL you copied into the **Neon** database (via the Neon SQL Editor or `psql` against the write replica) so the same change is applied there.

> **Prod schema is manual SQL only.** Neon does not run `migrate`. When a migration is committed, prod may attempt `migrate` at deploy, but you must verify / apply the schema yourself — never rely on it.

### 5. Any breaking changes: deploy first, then change the field (zero downtime)

For a **breaking change** (e.g. adding a `NOT NULL` constraint, or any change that would fail against existing data), apply it in phases to cause **minimum downtime**:

1. **Prepare the data** — ensure no existing row will violate the new rule. Run a script / business logic to guarantee the field is populated (no `NULL`s) before the constraint is added.
2. **Deploy the code first** — push/deploy the code change to prod.
3. **As the last step**, make the DDL change in Neon (e.g. add the `NOT NULL` constraint).

> Never add the restrictive DDL before the code that depends on it is live. Additive changes can go in whenever; destructive/restrictive changes go in **last**, after code and data are in place.

---

## SQL Files (built-in Django apps)

| File | Purpose |
|---|---|
| `sql/ddl.sql` | `CREATE TABLE` for the built-in Django apps (schema) |
| `sql/dml.sql` | Seeds reference data: content types + permissions |

**Both files are dev-only.** Production (Neon) manages its schema independently.

### `sql/ddl.sql`

Creates the tables required by Django's built-in apps:

| Table | App |
|---|---|
| `django_migrations` | Django internals (required even with migrations disabled) |
| `django_content_type` | contenttypes |
| `auth_permission` | auth |
| `auth_group` | auth |
| `auth_group_permissions` | auth |
| `django_session` | sessions |
| `django_admin_log` | admin |

> `auth_user`, `auth_user_groups`, and `auth_user_user_permissions` were pruned — with `AUTH_USER_MODEL = 'authentication.User'` they are dead tables (the real user table `authentication_*` is migration-managed).

### `sql/dml.sql`

Seeds the reference data Django needs:

1. **6 content types** (one per model Django knows about)
2. **24 permissions** (add/change/delete/view × 6 models)

The default superuser is **not** seeded in SQL — it is created at runtime by `createsuperuser_if_not_exists` (see `scripts/entrypoint.sh`).

Key details:
- All `ON CONFLICT DO NOTHING` — idempotent
- Sequence values explicitly reset via `setval()` after inserts
- Wrapped in `BEGIN` / `COMMIT`

---

## Reload Database

### Commands

```bash
# Full reload: drop database + create tables + seed data
bash scripts/reload_db.sh --step all

# Schema only: drop database + create tables (no seed data)
bash scripts/reload_db.sh --step ddl

# Seed data only: insert data without dropping tables
bash scripts/reload_db.sh --step dml
```

> **Prerequisite:** The `db` container must be running.
> Start it with: `docker compose up -d`

> **Safety:** This script only connects to local Docker PostgreSQL (`.env.dev`).
> It will NEVER connect to or modify the production Neon database.

---

## Production Safety

| Rule | Details |
|---|---|
| `reload_db.sh` only targets Docker PostgreSQL | Reads `.env.dev` (localhost), never touches Neon |
| DDL/DML files are dev-only reference | Never run against production |
| Schema changes for prod | Apply manually — via Neon SQL Editor or `psql` against the write replica |
| `migrate` runs only locally | Prod schema is changed by pasting SQL manually |
| No `DATABASE_URL` in `.env.dev` | Only individual `POSTGRES_*` vars for local Docker |

---

## Connection Parameters

| Variable | `.env.dev` (local Docker) | Render env (production Neon) |
|---|---|---|
| `POSTGRES_DB` | `django` | `neondb` |
| `POSTGRES_USER` | `django` | `neondb_owner` |
| `POSTGRES_PASSWORD` | `change-this-password` | (from Neon) |
| `POSTGRES_HOST` | `localhost` | (from Neon) |
| `POSTGRES_PORT` | `5432` | `5432` |

The `reload_db.sh` script always reads from `.env.dev` (localhost).

---

## Connecting with DBeaver

### Local Docker PostgreSQL

| Field | Value |
|---|---|
| Host | `localhost` |
| Port | `5432` |
| Database | `django` |
| Username | `django` |
| Password | `change-this-password` |

### Production Neon DB

| Field | Value |
|---|---|
| Host | (from Neon, e.g. `ep-misty-block-aya29p71-pooler.c-5.us-east-2.aws.neon.tech`) |
| Port | `5432` |
| Database | `neondb` |
| Username | `neondb_owner` |
| Password | (from `.env`) |
| SSL | Require |

---

## Adding Content Types and Permissions for New Models

Built-in apps are seeded via `sql/dml.sql`. When adding a new SQL-managed model that Django needs to know about, add its content type and the 4 CRUD permissions:

```sql
INSERT INTO django_content_type (id, app_label, model) VALUES
    (7, 'your_app', 'your_model')
ON CONFLICT DO NOTHING;

INSERT INTO auth_permission (id, name, content_type_id, codename) VALUES
    (25, 'Can add your model',    7, 'add_your_model'),
    (26, 'Can change your model', 7, 'change_your_model'),
    (27, 'Can delete your model', 7, 'delete_your_model'),
    (28, 'Can view your model',   7, 'view_your_model')
ON CONFLICT DO NOTHING;

SELECT setval('django_content_type_id_seq', 7);
SELECT setval('auth_permission_id_seq', 28);
```

---

## Gotchas

- **`django_migrations` table must exist** even with migrations disabled — Django queries it internally
- **Migrations for project apps only** — never `makemigrations` for a built-in app (their schema is in `ddl.sql`)
- **`migrate` local-only** — Neon schema is changed by manual SQL, so the committed migrations act as a record + a local tool to generate the DDL
- **Breaking changes go last** — deploy code first, then alter the field on Neon
- **Sequence resets** — after inserting rows with explicit IDs, always call `setval()` to keep sequences in sync
- **Idempotency** — all inserts use `ON CONFLICT DO NOTHING`, all creates use `IF NOT EXISTS`
- **DB container must be running** — `reload_db.sh` will fail if `docker compose ps db` shows the container is down
- **Never use `reload_db.sh` against production** — it only targets Docker PostgreSQL
