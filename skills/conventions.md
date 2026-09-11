# Conventions

> Code style, patterns, and rules for working on this project.

---

## Principles

Three principles shape every decision in this codebase. When a shortcut seems
to conflict with a rule below, the principles win.

### DRY — Don't Repeat Yourself

Keep **one source of truth per fact**:
- The schema is defined once in `sql/ddl.sql`; models mirror it and there are
  **no migration files** — never write a second schema definition.
- Status CODE→id is defined once in `StatusIds`
  (`aggregator/models/Status.py`); consumers derive their code sets from it
  (`ORDER_STATUS_CODES = {s.name for s in StatusIds.order_statuses()}`) and
  resolve via `Status.by_id()` — never hardcode codes or ids.
- Reuse before reinvent: `common/` bases (`TimeStampedModel`,
  `SoftDeletedModel`, `CreatedByModel`), model helpers (`is_verified`,
  `is_dispatched`), and the operations layer (`OrderOperations`,
  `ClientOperations`) keep logic out of views and out of other apps.
- If you are about to paste a block for the third time, extract it.

### YAGNI — You Aren't Gonna Need It

- Build the simplest thing today's feature needs. Do not add endpoints,
  models, columns, or abstraction layers "for later" — `android/v1/` stays
  empty until an endpoint is actually needed, and `PublicIdModel` /
  `RandomIdModel` are idle because nothing uses them.
- No speculative machinery: one `config/settings.py` (no base/dev/prod split),
  no migration tooling, no extra compose services, no unused parameters.
- Add a parameter, flag, or configuration knob when a concrete caller exists.

### KISS — Keep It Simple, Stupid

- Prefer the plainest approach that works: raw SQL schema with no ORM
  migrations, thin DRF views delegating to operations helpers, short focused
  functions.
- Keep tests behaviour-driven and simple: one behaviour per test, plain
  `assert`, no over-mocking; assert outcomes, never restate the
  implementation's arithmetic.
- If the solution needs a diagram to be explained, simplify it.

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
├── tests/              # pytest tests (DML-seeded)
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
- `sql/dml.sql` seeds content types (28) + permissions (112) + reconciliation
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
- Single `config/settings.py` file (no split base/dev/prod) — KISS
- All config from environment variables where possible
- `MIGRATION_MODULES` disables migrations for built-in `django.*` apps; project
  apps ship **no migration files** either (YAGNI — the schema lives in
  `sql/ddl.sql`)

### Apps
- Use `python manage.py startapp <name>` to create
- Add to `INSTALLED_APPS` in `config/settings.py`
- Place the app at the project root (e.g. `/aggregator`)
- All apps (built-in and project) are SQL-managed via `sql/ddl.sql`; there are no migration files

### Models
- Project-app models define the real schema, mirrored in `sql/ddl.sql`
- Prod schema is applied manually (edit model → update SQL → DBeaver DDL → Neon)

### Primary keys: `id`, not `pk`
- Every table has an `id` `BIGSERIAL` PK, so reference rows as **`id`** in route
  kwargs, ORM lookups, and attributes — never `pk` (`pk` is just Django's alias).
- URL patterns for single objects use `<int:id>`, and the DRF view receives the
  kwarg as `id` and looks the row up with `id=…`.

### Enums & seeded statuses
- Seed rows that act as enum values (`aggregator_status`, ids 1–9, and
  `aggregator_stage`, ids 1–4, both in `sql/dml.sql`) are mirrored by an
  `enum.IntEnum` (`aggregator/models/Status.py::StatusIds`,
  `aggregator/models/Stage.py::StageIds`): member **name** == seeded
  **code**, member **value** == row **id**. Members are usable directly in ORM
  queries (`Status.objects.get(id=StatusIds.BOOKED)`).
- The enum is the single source of truth for the CODE→id mapping — never
  hardcode a status code string or an id in consumers. Derive sets such as
  `Order.ORDER_STATUS_CODES` / `Client.CLIENT_STATUS_CODES` from it
  (`{s.name for s in StatusIds.order_statuses()}`).
- Resolve a member to its row via `Status.by_id(StatusIds.X)`, never
  `Status.objects.get(code=...)`.
- **Keep `StatusIds` in sync with `dml.sql`:** if a status row is added,
  renamed, or renumbered there, update the enum (and the
  `order_statuses()` / `client_statuses()` id ranges) in the same change. The
  same rule applies to `StageIds` and `aggregator_stage`.
- `Product.stage` is the same pattern applied to a product's seed
  classification: `BREEDER`, `FOUNDATION`, `RESEARCH`, `CERTIFICATE`. It is a
  required FK — resolve it with `Stage.by_id(StageIds.BREEDER)`.

### Unit model: a **packet** is the small unit; a **bag** is the container
A `ProductPackaging` **is a bag** — a container of `packets` small units, each of
`packet_weight` kg (fields `ProductPackaging.packets` and `.packet_weight`). A
bag holds N packets. (This inverts an earlier model where a "packet" held
"bags"; the two nouns were swapped wholesale.)

### Pricing units: `Product` is per-packet, `ProductPackaging` and `OrderItem` are per-bag
- `Product.selling_price` is the **per-packet** rate. It never appears in
  totals math directly — the bag (packaging) is the pricing unit downstream.
  Buying price is deliberately **not** tracked on a product.

### Uploaded files
- Never write uploads straight to disk from a view — go through
  `common.storage.upload_image` / `delete_image`. It validates once (type +
  size) and then picks a backend: the Supabase bucket when `SUPABASE_*` is
  configured, `MEDIA_ROOT` otherwise (dev and tests).
- Store only the returned URL on the row (`Product.image_url`, a `CharField` —
  **not** a `URLField`, because the local backend returns a relative
  `/media/…` path).
- Upload **before** creating the row: files are named by a fresh UUID, so a
  failed upload never leaves a half-created record behind.
- `ProductPackaging.selling_price` is the **whole-bag** list price (Decimal
  12,2, `NOT NULL`, stored). `ProductOperations.add_packaging(...)` defaults it
  to `packets * product.selling_price` at creation; **frozen** once stored.
- `OrderItem.negotiated_selling_price` is the **per-bag** rate for that line
  (same unit as `ProductPackaging.selling_price`), defaulting to the packaging's
  `selling_price`.
- `OrderItem.line_total == negotiated_selling_price * quantity` (quantity counts
  bags). `Order.total_amount` sums line totals; `Order.total_packets` counts
  small units (`quantity * packets`).

### Stock units: two pools — whole bags per packaging, loose packets per product
- Stock is a **daily physical count**, not a running ledger:
  `InventorySnapshot` holds one row per (`snapshot_date`, `product_packaging`).
- Two pools, in two different units, that never mix, tracked at **different
  grains**:
  - `bags` — sealed whole packagings, tracked **per `ProductPackaging`**. Same
    unit as `OrderItem.quantity`, so packaged-order demand compares directly
    with no conversion. Consumed by normal `Order`s.
  - `loose_packets` — unpacked single packets, tracked **per `Product`**.
    Counted per packaging in the snapshot but aggregated to the product for
    availability (`on_hand_loose_packets(product)` sums a product's packaging
    rows), because a `CustomOrder` names a raw product and a packet count —
    never a packaging. Optional (defaults to 0). Consumed only by `CustomOrder`s.
- A packaged order can never be filled from loose stock, and a custom order
  deals only in loose packets — it never breaks open a bag. Moving stock between
  the pools is a physical act recorded by **re-uploading the count**
  (`bags - 1`, `loose_packets + N`) — never by a synthetic movement row.
- **Only the latest `snapshot_date` is retained.** Recording a count for a newer
  date hard-deletes every earlier row (a queryset delete, which bypasses
  `SoftDeletedModel`'s instance-level soft delete by design).
- Reserved and consumed quantities are **derived from order status** (`Order`
  for bags, `CustomOrder` for loose packets), never stored. That is what makes
  verification and dispatch reversible, and what lets outstanding reservations
  survive the daily purge. Do not add counter columns.

### Order verification & custom orders
- `OrderOperations.verify_order` has **three** gates: (1) the actor is an admin
  (or superuser); (2) today's stock count is complete for every packaging
  (`is_stock_count_complete`); (3) **enough available bags** exist for every
  packaging on the order (`available_bags` ≥ needed). Any shortfall blocks it.
- `Admin.can_update_stock_count` gates **writing a stock count and nothing
  else** — it does *not* gate order verification.
- `CustomOrder` is **standalone** (no FK to `Order`), booked **only by a sales
  admin**, and has **no verification step**: `create_custom_order` auto-confirms
  it (born `CONFIRMED`, `verified_by`/`verified_at` set to the creating admin).
  Creation is **blocked unless enough loose packets are in stock**
  (`available_loose_packets` ≥ requested). Its `CustomOrderItem` lines carry
  (`product`, `packets`) — no packaging.

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
- Single-object routes use `<int:id>` (never `<int:pk>`; see "Primary keys" below)

---

## Code Style

- Follow the DRY / YAGNI / KISS principles at the top of this page; style never justifies duplication or speculative complexity
- Follow Django's coding style (PEP 8)
- Uaw comments only when its complex or unclear from code why its written
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
- Do not hardcode status codes or ids — use `StatusIds` / `Status.by_id()` (DRY)
- Do not add models, endpoints, columns, or abstraction layers "for later" (YAGNI)
- Do not reinvent existing machinery — reuse `common/` bases, the operations layer, and `scripts/run.sh` instead of duplicating them (DRY/KISS)
- Do not rely on prod running `migrate` to change the schema — apply it manually to Neon
- Do not apply a breaking/restrictive DDL (e.g. `NOT NULL` constraint) before the code and data are ready — deploy first, alter last
- Do not hardcode database credentials in Python files
- Do not run DML/seed SQL against production
- Do not commit `.env` (production secrets)
- Do not push Flutter changes without rebuilding (`bash scripts/run.sh flutter`)
- Do not install Flutter SDK in Docker — the build output is committed to git
- Do not call `/api/test-sentry/` without a superuser account — it is there to probe error tracking

---

## Testing

### Framework
- **pytest** + **pytest-django** — all tests go in `tests/`

### Running (via `scripts/run.sh`, inside the web container)
```bash
bash scripts/run.sh test               # full pytest suite
bash scripts/run.sh test-unit          # pytest -v (whole suite)
bash scripts/run.sh test-dml           # pytest tests/ -v (whole suite, DML baseline)
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
- DML-backed tests subclass `tests/common.py::DMLTestCase`, which re-seeds the
  `sql/dml.sql` rows inside the test-class transaction.

### CI
- `.github/workflows/tests.yml` runs `test-unit` + `test-dml` + `lint`
  inside the web container on every PR to `master`
- Branch protection requires the `Tests / test` check to pass
