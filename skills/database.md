# Database

> Schema management for the Backend ERP project — **raw SQL only**. `sql/ddl.sql`
> is the full-schema reference for every app; there are no migration files.

---

## Schema Management Model

The entire schema is **SQL-managed**:

| Target | Managed by | Mechanism |
|---|---|---|
| Built-in Django apps (`auth`, `contenttypes`, `sessions`, `admin`) | **Raw SQL** | `sql/ddl.sql` + `sql/dml.sql` |
| Project apps (`authentication`, `common`, `config`, `api`, `aggregator`) | **Raw SQL** | `sql/ddl.sql` (full schema) + `sql/dml.sql` (seed) |

Controlled in `config/settings.py`:

```python
MIGRATION_MODULES = {
    app.split(".")[-1]: None for app in INSTALLED_APPS if app.startswith("django.")
}
```

`MIGRATION_MODULES` only disables the built-in `django.*` apps, but the project
apps ship **no migration files** either (the single `authentication/migrations/`
directory is empty). `migrate` is commented out of `scripts/entrypoint.sh`;
with no migrations to apply, Django's test runner syncs each `django_test` DB
straight from the models and the suites seed `dml.sql` via `tests/common.py`.

## Why raw SQL (KISS + DRY / YAGNI)

The schema is managed as plain SQL with **no migration machinery** — no
`makemigrations`, no per-app migration history to keep in sync (YAGNI), one
authoritative schema definition in `sql/ddl.sql` (DRY), and the simplest
possible change flow (KISS): edit model → update `sql/ddl.sql` / `sql/dml.sql`
→ reload locally → copy the DDL to Neon.

---

## Two Environments, Two Different Schema Paths

| | Local (Docker PostgreSQL) | Production (Neon) |
|---|---|---|
| Tables are created | `bash scripts/reload_db.sh --step all` (creates ALL tables from `sql/ddl.sql` + seed) | Schema applied **manually via SQL** (Neon does **not** run `migrate`) |
| How | reload script / DBeaver against `postgres_data` | Paste DDL into the Neon SQL Editor / write replica |
| Source of truth | `sql/ddl.sql` (+ `sql/dml.sql`), toggled in DBeaver | manual SQL derived from local |

**Key rule:** `migrate` is **never** part of the workflow. Local schema changes
= edit model → update `sql/*.sql` → reload. Prod changes = paste the matching
SQL manually into Neon.

---

## Changing a Table (Models → Prod)

This is the standard workflow for adding or changing a table, on **both** local and prod.

### 1. Create / Edit the model

Edit the model class (e.g. `authentication/models/*.py`,
`aggregator/models/*.py`, or a `common/models/*.py` base).

### 2. Update `sql/ddl.sql` (and related SQL)

`sql/ddl.sql` is the full-schema reference — the local and test DBs are built
straight from it, so every new/changed table must be reflected there. Also
touching `sql/dml.sql` (content types / permissions / seed rows) or
`sql/admin_perf.sql` (indexes) as needed.

### 3. Rebuild the local DB

```bash
bash scripts/reload_db.sh --step all     # drop + recreate ALL tables + seed
```

Alternatively `--step ddl` (schema only) or `--step dml` (seed only).

### 4. Generate the SQL from DBeaver

Open the changed table in **DBeaver** (connected to the local Docker DB) and copy
its **table DDL** (DBeaver → table → SQL → DDL). This gives the `CREATE TABLE` /
`ALTER TABLE` statements your model change produced — the SQL you run on prod.

### 5. Apply the same SQL to production

Paste the DDL you copied into the **Neon** database (via the Neon SQL Editor or
`psql` against the write replica) so the same change is applied there.

> **Prod schema is manual SQL only.** Neon does not run `migrate`, and nothing
> in CI applies prod schema for you.

### 6. Any breaking changes: deploy first, then change the field (zero downtime)

For a **breaking change** (e.g. adding a `NOT NULL` constraint, or any change
that would fail against existing data), apply it in phases to cause **minimum downtime**:

1. **Prepare the data** — ensure no existing row will violate the new rule. Run a script / business logic to guarantee the field is populated (no `NULL`s) before the constraint is added.
2. **Deploy the code first** — push/deploy the code change to prod.
3. **As the last step**, make the DDL change in Neon (e.g. add the `NOT NULL` constraint).

> Never add the restrictive DDL before the code that depends on it is live. Additive changes can go in whenever; destructive/restrictive changes go in **last**, after code and data are in place.

---

## SQL Files (dev reference)

| File | Purpose |
|---|---|
| `sql/ddl.sql` | `CREATE TABLE` for **every** app — Django built-ins (`django_migrations`, `django_content_type`, `auth_*`, `django_session`, `django_admin_log`), `authentication_user`, `authentication_user_groups/…_user_permissions`, `authentication_admin`, `authentication_salesperson`, `aggregator_*` (address/city/country/pincode/state), `authtoken_token` |
| `sql/dml.sql` | Seeds content types (28) + permissions (112: add/change/delete/view × 28 models), a reconciliation superuser (`9999999999` with TOTP secret `JBSWY3DPEHPK3PXP`), a no-TOTP user (`8888888888`), and the `aggregator_status` rows (ids 1–9) mirrored by `StatusIds` — used by the DML-seeded tests |
| `sql/admin_perf.sql` | Prod DDL: `pg_trgm` extension + GIN indexes on `authentication_user(name, email)` for Django-admin `ILIKE` search (idempotent) |
| `sql/session_auth_24h.sql` | Prod DDL: `authtoken_token.user_id` FK (DRF adds it only via migrate) + `created` index for the 24h TTL sweep (idempotent) |

**All files are dev/reference only.** Production (Neon) manages its schema
independently — apply `admin_perf.sql` / `session_auth_24h.sql` (and any newer
DDL) there manually.

### `sql/ddl.sql`

Creates the tables for Django's built-in apps **plus** the project apps and
drf-authtoken (`authtoken_token`). `auth_user`, `auth_user_groups`, and
`auth_user_user_permissions` were pruned — with `AUTH_USER_MODEL =
'authentication.User'` they are dead tables; the real user table is
`authentication_user` (and its M2M join tables are kept).

### `sql/dml.sql`

Seeds the reference data Django and the tests need:

1. **28 content types** (auth user/group/permission, contenttypes, sessions,
   admin logentry, authentication user/admin/salesperson, aggregator
   country/state/city/pincode/address)
2. **112 permissions** (add/change/delete/view × 28 models)
3. **Reconciliation users**: superuser `9999999999`/`admin` (TOTP enabled,
   `created_by`/`verified_by` self-referenced) and non-TOTP user `8888888888`
   (used by the DML-seeded tests).

The runtime `createsuperuser_if_not_exists` command is what guarantees a
superuser exists on a fresh prod deploy; the SQL rows are reconciliation seeds
so a local reload yields the same accounts the tests expect.

Key details:
- All `ON CONFLICT DO NOTHING` — idempotent
- Sequence values explicitly reset via `setval()` after inserts
- Wrapped in `BEGIN` / `COMMIT`
- **`aggregator_status` rows (ids 1–9)** are the canonical status seed
  (`1–7` order lifecycle, `8–9` client verification). They are mirrored by the
  `StatusIds` `IntEnum` in `aggregator/models/Status.py`, where member **name**
  == seeded `code` and member **value** == row `id`
  (`order_statuses()` = ids 1–7, `client_statuses()` = ids 8–9). The enum is
  the CODE→id source of truth the code and tests read from — whenever a status
  row is added, renamed, or renumbered in `dml.sql`, update `StatusIds` in the
  same change.

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

`sql/dml.sql` seeds the content types and permissions for every SQL-managed
model (currently 28 content types → 112 permissions). When adding a new
SQL-managed model, append its content type and 4 CRUD permissions **after the
current max IDs** (check `SELECT max(id), setval(...)` in `dml.sql`):

```sql
INSERT INTO django_content_type (id, app_label, model) VALUES
    (29, 'your_app', 'your_model')
ON CONFLICT DO NOTHING;

INSERT INTO auth_permission (id, name, content_type_id, codename) VALUES
    (113, 'Can add your model',    29, 'add_your_model'),
    (114, 'Can change your model', 29, 'change_your_model'),
    (115, 'Can delete your model', 29, 'delete_your_model'),
    (116, 'Can view your model',   29, 'view_your_model')
ON CONFLICT DO NOTHING;

SELECT setval('django_content_type_id_seq', 29);
SELECT setval('auth_permission_id_seq', 116);
```

---

## Gotchas

- **`django_migrations` table must exist** even with migrations disabled — Django queries it internally
- **The whole schema is SQL-managed** — `sql/ddl.sql` is the reference for *every* app; never `makemigrations` for a built-in app (their schema is in `ddl.sql`)
- **No `migrate` in the workflow** — `migrate` is commented out of `scripts/entrypoint.sh`; Neon is changed only by manual SQL; the tests use `migrate --fake` to mark the pre-built DDL schema
- **Breaking changes go last** — deploy code first, then alter the field on Neon
- **Sequence resets** — after inserting rows with explicit IDs, always call `setval()` to keep sequences in sync
- **Idempotency** — all inserts use `ON CONFLICT DO NOTHING`, all creates use `IF NOT EXISTS`
- **DB container must be running** — `reload_db.sh` will fail if `docker compose ps db` shows the container is down
- **Never use `reload_db.sh` against production** — it only targets Docker PostgreSQL
