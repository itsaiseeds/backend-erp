# SaiSeeds Backend ERP — Knowledge Graph

> Machine/navigation map of the codebase: every component (node), what it does,
> and how it connects to everything else. Start here before touching a system,
> then dive into [`skills/`](../skills.md) for workflow-level detail.
>
> See also: [skills.md](../skills.md) (index of domain docs), `docs/api/openapi.yml`
> (auto-generated API reference).

## 1. Architecture at a glance

```mermaid
graph TD
    subgraph RUNS["Runtime (docker compose)"]
        GW["entrypoint.sh<br/>(runserver in dev, gunicorn in prod)"] --> WSGI["config.wsgi"]
        WSGI --> URLS["config.urls"]
        DB[(PostgreSQL 18<br/>service: db)]
        URLS --> ADMIN["django /admin/"]
        URLS --> FL["Flutter web app<br/>/sales-admin/ (config/views.py)"]
        URLS --> SCHEMA["/api/schema/ + /api/docs/<br/>(drf-spectacular, superuser)"]
    end

    subgraph AUTHCLASSES["Shared auth (api/authentication.py)"]
        SESSAUTH["SessionAuthentication<br/>(sales admin — cookie, 401 semantics)"]
        EXPTAUTH["ExpiringTokenAuthentication<br/>(Android — bearer token, 24h TTL)"]
    end

    subgraph API["API layer (api/)"]
        URLS --> APIROOT["api/urls.py"]
        APIROOT --> SA["/api/sales_admin/"]
        SA --> OTPREQ["GenerateOTPView"]
        SA --> OTPVER["VerifyOTPView"]
        SA --> ADMV["AdminsView (superuser)"]
        SA --> SPLV["SalesPeopleView (admin/superuser)"]
        APIROOT --> AND["/api/android/v1/ (empty)"]
        APIROOT --> TSENTRY["TestSentryView<br/>(/api/test-sentry/, superuser)"]
        ADMINV["AdminApiView (session)"] --> BASE["BaseApiView<br/>(auth flags)"]
        ANDV["AndroidBaseView (token)"] --> BASE
        SESSAUTH --> BASE
        EXPTAUTH --> BASE
        OTPVER -. pre-auth .-> DB
    end

    subgraph DOMAIN["Domain (authentication/)"]
        U["User (custom user)"]
        U --> ADMINP["Admin (1:1)"]
        U --> SPP["SalesPerson (1:1)"]
    end

    subgraph AGG["Domain (aggregator/)"]
        CTRY["Country"]
        ST["State"]
        CIT["City"]
        PIN["Pincode"]
        ADDR["Address"]
        CTRY --> ST
        ST --> CIT
        CIT --> PIN
        CIT --> ADDR
        ST --> ADDR
        CTRY --> ADDR
        PIN --> ADDR
        SPP --> CIT
    end

    subgraph COMMON["Reusable bases (common/)"]
        TS["TimeStampedModel"]
        SD["SoftDeletedModel"]
        CB["CreatedByModel"]
        PID["PublicIdModel (idle)"]
        RID["RandomIdModel (idle)"]
    end

    subgraph DATA["Schema (sql/)"]
        DDL["ddl.sql (full schema, all apps)"]
        DML["dml.sql (content types + perms + seed users)"]
        APF["admin_perf.sql (pg_trgm admin indexes)"]
        S24["session_auth_24h.sql (prod FK + TTL indexes)"]
    end

    DB --> DATA
    ADMINP --> U
    SPP --> U
    ADMINP --> SD
    ADMINP --> CB
    SPP --> SD
    SPP --> CB
    ADDR --> CB
    CTRY --> CB
    ST --> CB
    CIT --> CB
    PIN --> CB
    U --> TS
    ADMINP --> TS
    SPP --> TS

    subgraph QA["Quality (pytest → CI)"]
        UNIT["tests/ (unit: sample, expiring token)"]
        IT["tests/integration/ (django_test from ddl+dml)"]
        CI["GitHub Actions: Tests / test<br/>gate on PR → master"]
    end
    IT --> DB
    UNIT --> CI
    IT --> CI
```

## 2. Node registry

### Entry points & infrastructure

| Node | Path | Purpose | Edges |
|---|---|---|---|
| `web` service | `docker-compose.yml`, `Dockerfile` | Python 3.14-slim image; bind-mounts repo at `/app`; port 8000 | starts → `scripts/entrypoint.sh`; depends_on → `db` (healthy) |
| `db` service | `docker-compose.yml` | PostgreSQL 18, port 5432, named volume `postgres_data`; `pg_isready` healthcheck; `shared_buffers=128MB`; timezone UTC | provider ← web, tests, DBeaver |
| Container entrypoint | `scripts/entrypoint.sh` | Starts collectstatic → `createsuperuser_if_not_exists` → then runs **dev `runserver`** when `DEBUG=true` (live reload on bind mount) or **gunicorn** otherwise (`--workers`/`--threads` env). **`migrate` is commented out** — the whole schema is pre-applied SQL (see `sql/` below). Invoked via `bash` (Dockerfile `ENTRYPOINT ["bash", ...]`) so it needs no `+x` | runs → `config.wsgi` / `manage.py runserver` |
| WSGI / ASGI | `config/wsgi.py`, `config/asgi.py` | Gunicorn hooks in here | → `config.urls` |
| Root URLconf | `config/urls.py` | Mounts `/admin/`, `/api/`, `/api/schema|docs/` (superuser-only), `/sales-admin/...` catch-all | → `api/urls.py`, `config.views.flutter_catch_all`, drf-spectacular views |
| Flutter catch-all | `config/views.py` | Serves `web/build/web/` (committed build output) for all `/sales-admin/*` routes; SPA fallback to `index.html` | serves ← `web/` |

### Configuration

| Node | Path | Purpose | Edges |
|---|---|---|---|
| `config/settings.py` | single settings module | env-driven (`SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS` have fallbacks); DRF default auth = `SessionAuthentication` + `ExpiringTokenAuthentication`, permission `IsAuthenticated`; Argon2-first password hashers; `CONN_MAX_AGE=60` + `CONN_HEALTH_CHECKS` + db `timezone=Asia/Kolkata`; WhiteNoise static with `STATIC_ROOT=staticfiles`; `SESSION_COOKIE_AGE=86400` + `TOKEN_TTL_HOURS=24`; `CORS_ALLOW_CREDENTIALS`; Sentry init when `SENTRY_DSN` set and not DEBUG | configures → all apps; reads → env vars |
| Superuser bootstrap | `config/management/commands/createsuperuser_if_not_exists.py` | Idempotent superuser create; dev fallback `9999999999/admin` when `DEBUG=True`; `DJANGO_SUPERUSER_*` env otherwise | called by → entrypoint |

### API layer

| Node | Path | Purpose | Edges |
|---|---|---|---|
| `BaseApiView` | `api/views.py` | Flag-driven base (`auth_required`, `admin_required`, `superuser_required`) → DRF `get_permissions()`; also defines `fire_and_forget` (post-commit background thread) | base ← `AdminApiView`, `AndroidBaseView` |
| Shared auth classes | `api/authentication.py` | `SessionAuthentication` (DRF session but with a real `WWW-Authenticate` challenge so anonymous = **401**, not 403) + `ExpiringTokenAuthentication` (24h TTL via `TOKEN_TTL_HOURS`; an expired token is deleted on first use) | used by → base views + `settings.REST_FRAMEWORK` defaults |
| `AdminApiView` | `api/admin.py` | Sales-admin website base: **session cookie** auth + requires `Admin` profile | → `BaseApiView`, `.permissions.IsAdminUser` |
| `AndroidBaseView` | `api/android/base.py` | Salesperson Android base: **bearer `ExpiringTokenAuthentication`** + requires `SalesPerson` profile | → `BaseApiView`, `.permissions.IsSalesPerson` |
| Permissions | `api/permissions.py` | `IsRolePermission` meta-class + `IsAdminUser`, `IsSuperUser`, `IsSalesPerson` | keyed off → `User.is_admin_user/is_superuser/is_salesperson` |
| Top API router | `api/urls.py` | `/api/android/`, `/api/sales_admin/` | → namespace URLconfs |
| `GenerateOTPView` | `api/sales_admin/GenerateOTPView.py` | `POST /api/sales_admin/auth/otp/request` — pre-auth, `AllowAny`; creates a `MobileVerification` challenge; deliberately vague response | creates → `MobileVerification`; looks up → `User` |
| `VerifyOTPView` | `api/sales_admin/VerifyOTPView.py` | `POST /api/sales_admin/auth/otp/verify` — pre-auth, `AllowAny`; validates OTP, marks used, returns DRF `Token` + user payload | reads → `MobileVerification`, `User`, `rest_framework.authtoken`; calls → `MobileVerification.mark_used()` |
| `AdminsView` | `api/sales_admin/AdminsView.py` | `GET`/`POST /api/sales_admin/admins` — **superuser only**; POST takes `name`/`email`/`phone_number`/`can_update_stock_count`/`city` and creates a verified user + `Admin` profile + **fallback `SalesPerson`** in one transaction; GET lists non-deleted admins only | serializer defined in the view; reads → `Admin`, `SalesPerson`, `City`; calls → `create_verified_user`, `admin_payload` |
| `SalesPeopleView` | `api/sales_admin/SalesPeopleView.py` | `GET`/`POST /api/sales_admin/sales-people` — admin OR superuser (`IsAdminOrSuperUser`); POST creates a verified user + `SalesPerson` profile (**city only**); GET lists non-deleted sales people only | serializer defined in the view; reads → `SalesPerson`, `City`; calls → `create_verified_user`, `salesperson_payload` |
| `UserOperations` | `authentication/UserOperations.py` | User creation (`create_verified_user`) + output payload builders (`admin_payload`, `salesperson_payload`). Payloads never expose `user_id`/`is_deleted`/`deleted_by`; admins carry no `city`/`address`, salespeople carry city only; missing values fall back to `N/A` | used by → `AdminsView`, `SalesPeopleView`; reads → `User`, `Admin`, `SalesPerson` |
| `CitiesByStateView` | `api/utilities/CitiesByStateView.py` | `GET /api/utilities/cities?state=Maharashtra` — **public** (`AllowAny`), case-insensitive state lookup → `[{"id", "name"}, ...]`; `400` when `state` missing, `404` for unknown state | reads → `aggregator.State`, `City` |
| Utilities routes | `api/utilities/urls.py` | `cities` lookup under the `/api/utilities/` namespace | → `CitiesByStateView` |
| Sales admin routes | `api/sales_admin/urls.py` | Namespaced routes (`auth/otp/*`, `admins`, `sales-people`) | → `GenerateOTPView`, `VerifyOTPView`, `AdminsView`, `SalesPeopleView` |
| Android v1 | `api/android/v1/urls.py` | Versioned namespace, currently empty (endpoints built out one module each) | — |

> Naming gotcha: `api/admin.py` defines the **`AdminApiView` base controller**, not
> the Django admin site (which lives in `authentication/admin.py`).

### Domain — authentication

| Node | Path | Purpose | Edges |
|---|---|---|---|
| `User` | `authentication/models/User.py` | Custom user (`AbstractBaseUser` + `PermissionsMixin`); `phone_number` is `USERNAME_FIELD` (10 digits, no country code); password only for staff; everyone else logs in via **TOTP authenticator app**; `created_by`/`verified_by` self-FK invariants (superusers self-reference); TOTP helpers (`generate_totp_secret`, `enable_totp`, `verify_totp`, provisioning URI); role helpers `role`, `is_salesperson`, `is_admin_user`, `is_verified_user`, `can_login_with_password` | extends → `TimeStampedModel`; related ← `Admin`, `SalesPerson` |
| `Admin` | `authentication/models/Admin.py` | Application admin profile (1:1). Only a superuser may create one; `can_update_stock_count` flag | extends → `TimeStampedModel`, `SoftDeletedModel`, `CreatedByModel`; 1:1 → `User` |
| `SalesPerson` | `authentication/models/SalesPerson.py` | Salesperson profile (1:1). Only an Admin (or superuser) may create one; `city` FK | extends → `TimeStampedModel`, `SoftDeletedModel`, `CreatedByModel`; 1:1 → `User`; FK → `aggregator.City` |
| Admin site | `authentication/admin.py` | Registers `User`, `Admin`, `SalesPerson`; enforces who may grant `Admin`/`SalesPerson` roles; unregisters stock `Group` admin | configures → Django `admin` |
| Validator | `authentication/validators.py` | `^\d{10}$` 10-digit phone validator | used by → `User.phone_number` |

### Domain — aggregator (geo master data)

| Node | Path | Purpose | Edges |
|---|---|---|---|
| `Country` | `aggregator/models/Country.py` | `name` + `iso_code` (both unique, indexed); root of the geo hierarchy | extends → `TimeStampedModel`, `SoftDeletedModel`, `CreatedByModel`; 1:N → `State` |
| `State` | `aggregator/models/State.py` | `name` + optional `code`; unique `(country, name)` | 1:N → `City` |
| `City` | `aggregator/models/City.py` | `name`; unique `(state, name)`; `country` property; `ordering = name` | 1:N → `Pincode`, `Address`; ← `SalesPerson.city` |
| `Pincode` | `aggregator/models/Pincode.py` | `code`; unique `(city, code)`; `state`/`country` convenience properties | 1:N → `Address` |
| `Address` | `aggregator/models/Address.py` | Denormalised pincode/city/state/country chain so any level can be listed/filtered; `clean()` validates the chain matches | FK → all four geo nodes |
| aggregator admin | `aggregator/admin.py` | `SoftDeleteModelAdmin` + `autocomplete_fields`/`list_select_related` so related picks don't N+1 | configures → Django `admin` |

### Reusable bases — common

| Node | Path | Purpose | Used by |
|---|---|---|---|
| `TimeStampedModel` | `common/models/timestamped.py` | `created_at` (`indian_now`) / `updated_at`; `indian_now()` = Asia/Kolkata localtime | `User`, `Admin`, `SalesPerson`, aggregator models |
| `CreatedByModel` | `common/models/created_by.py` | `created_by` user audit FK (`PROTECT`, auto-filled with `request.user` by `AuditFieldsAdminMixin` if you use ModelAdmin) | `Admin`, `SalesPerson`, all aggregator models |
| `SoftDeletedModel` | `common/models/soft_deleted.py` | Soft delete: `is_deleted`/`deleted_at`/`deleted_by`; managers `objects` (hide deleted) + `all_objects`; `delete()` requires `deleted_by` with the `delete_<model>` permission; `hard_delete()`, `restore()` | `Admin`, `SalesPerson`, aggregator models |
| Admin helpers | `common/admin.py`, `common/models/` | `AuditFieldsAdminMixin` (read-only audit fieldsets, auto `created_by`) + `SoftDeleteModelAdmin` (soft delete through the admin) | aggregator + auth admins |
| `PublicIdModel` | `common/models/public_id.py` | 12-char `public_id` for user-facing refs (intended for orders/invoices) | (no concrete use yet) |
| `RandomIdModel` | `common/models/random_id.py` | random `UUIDField` column | (no concrete use yet) |

### Schema & data

| Node | Path | Purpose | Edges |
|---|---|---|---|
| `sql/ddl.sql` | full schema | **Every** table — Django built-ins (`django_migrations`, `django_content_type`, `auth_*`, `django_session`, `django_admin_log`), custom apps (`authentication_*`, `aggregator_*`), and `authtoken_token`. Dev/test reference; prod schema applied manually on Neon | consumed by → `reload_db.sh`, `integration_db.sh`, integration tests |
| `sql/dml.sql` | seed data | Content types (14) + permissions (56, 4 per model) + **reconciliation superuser** `9999999999` (with TOTP secret `JBSWY3DPEHPK3PXP`) + a no-TOTP user `8888888888` for the negative-path test. Idempotent `ON CONFLICT DO NOTHING`, `setval()` sequence resets, wrapped in txn | consumed by → same as above |
| `sql/admin_perf.sql` | prod DDL | `pg_trgm` extension + GIN trigram indexes on `authentication_user(name, email)` for Django admin `ILIKE` search | applied to → local/test DBs, Neon (manual) |
| `sql/session_auth_24h.sql` | prod DDL | `authtoken_token.user_id` FK (DRF only adds it via migrate) + `created` index for the TTL expiry sweep | applied to → Neon (manual) |
| `MIGRATION_MODULES` | `config/settings.py` | Disables migrations for built-in `django.*` apps via a dict comprehension (settings comment additionally states the project apps are schema-managed). **No migration files exist** — the repo has one empty `authentication/migrations/` dir. The *entire* schema is SQL-managed; integration tests run `manage.py migrate --fake` to mark the pre-built tables as applied | drives → `migrate` behaviour |

### Tooling & quality

| Node | Path | Purpose | Edges |
|---|---|---|---|
| `scripts/run.sh` | single entry point | `build/up/down/restart/reload-db/logs/status/shell/psql/flutter/schema/test/test-unit/test-integration/lint/typecheck`. Tests/lint/typecheck run in **short-lived one-off `web` containers** (`compose run --rm --no-deps --entrypoint ""`) to avoid booting gunicorn | calls → `reload_db.sh`, `integration_db.sh`, compose |
| `scripts/reload_db.sh` | local DB reload | `--step all/ddl/dml`; **local Docker Postgres only, never prod** | reads → `sql/ddl.sql`, `sql/dml.sql`, `.env.dev` |
| `scripts/integration_db.sh` | test DB builder | Build/drop throwaway `django_test` DB from DDL+DML | consumed by integration tests (now via `tests/integration/base.py`) |
| Unit tests | `tests/test_sample.py`, `tests/test_expiring_token.py` | Sanity pytest + token-TTL unit test | none |
| Integration framework | `tests/integration/` | `base.py` (`IntegrationDbContext`, `LiveServer`, `IntegrationTestCase`) + `conftest.py` fixtures; builds `django_test` from `sql/ddl.sql`+`dml.sql`+`admin_perf.sql`, `migrate --fake`, runs real `runserver` on `127.0.0.1:8001`, exercises HTTP via `requests.Session` | depends on → `db`; consumed by → `test_sentry_probe.py` |
| CI | `.github/workflows/tests.yml` | Builds images, starts `db`, runs `test-unit` + `test-integration` + `lint` in one-off containers | gate on → PRs to `master`; renders check `Tests / test` |
| Branch protection | GitHub settings | `master` requires `Tests / test` to pass + PR review | enforced by → GitHub |
| Skills | `skills/*.md`, `.agents/skills/run-tests/SKILL.md` | Domain knowledge + test-run instructions (node-id docstring convention) | read before editing |

## 3. Data model

```mermaid
erDiagram
    USER ||--o| ADMIN : "admin_profile (1:1)"
    USER ||--o| SALESPERSON : "salesperson_profile (1:1)"
    USER o|--o| USER : "created_by / verified_by (self-FK)"
    SALESPERSON o|--o| CITY : "city FK"
    COUNTRY ||--o{ STATE : "states"
    STATE ||--o{ CITY : "cities"
    CITY ||--o{ PINCODE : "pincodes"
    CITY ||--o{ ADDRESS : "city"
    STATE ||--o{ ADDRESS : "state"
    COUNTRY ||--o{ ADDRESS : "country"
    PINCODE ||--o{ ADDRESS : "pincode"

    USER {
        char phone_number "10 digits, unique, USERNAME_FIELD"
        char name
        email email
        bool is_verified is_staff is_superuser is_active
        bool totp_enabled
        char totp_secret "base32, nullable"
        fk created_by "self; superusers self-reference"
        fk verified_by "required when is_verified"
        dt date_joined
    }
    ADMIN {
        fk user "1:1, CASCADE"
        bool can_update_stock_count
        fk created_by "PROTECT; acting request.user"
        bool is_deleted "soft delete"
    }
    SALESPERSON {
        fk user "1:1, CASCADE"
        fk city "→ aggregator_city"
        fk created_by "PROTECT; acting request.user"
        bool is_deleted "soft delete"
    }
    COUNTRY {
        char name "unique"
        char iso_code "unique, ISO 3166"
    }
    STATE {
        char name "(country, name) unique"
        char code "nullable, e.g. MH"
        fk country "PROTECT"
    }
    CITY {
        char name "(state, name) unique"
        fk state "PROTECT"
    }
    PINCODE {
        char code "(city, code) unique"
        fk city "PROTECT"
    }
    ADDRESS {
        char address_line_1
        char address_line_2 "optional"
        fk pincode "PROTECT"
        fk city "PROTECT"
        fk state "PROTECT"
        fk country "PROTECT"
    }
```

## 4. URL / routing map

```
/                    -> 404
/admin/              -> Django admin (authentication/admin.py + aggregator/admin.py)
/api/
├── sales_admin/
│   ├── auth/otp/request   POST  GenerateOTPView          (AllowAny)
│   ├── auth/otp/verify    POST  VerifyOTPView            (AllowAny → Token)
│   ├── admins             GET   AdminsView               (superuser; incl. soft-deleted)
│   │                     POST   AdminsView               (superuser; also creates fallback SalesPerson)
│   └── sales-people       GET   SalesPeopleView          (admin OR superuser)
│                         POST   SalesPeopleView          (admin OR superuser)
└── android/
    └── v1/                (empty — being built)
/api/schema/         -> OpenAPI JSON   (drf-spectacular)
/api/docs/           -> Swagger UI
/sales-admin[/...]   -> Flutter build  (config/views.py catch-all)
```

> Auth model: default DRF global = `Session + Token` auth, `IsAuthenticated`.
> Admin/salesperson management views accept both the **session cookie** and the
> OTP-issued bearer **Token**. Pre-auth endpoints (OTP) opt out with
> `authentication_classes = []` and `permission_classes = [AllowAny]`.
> Client base views pick credentials: admin → session cookie; android → bearer
> token.

## 5. Data & schema flow

```
models/*.py ----(DBeaver: copy table DDL)---->  Neon SQL Editor (prod, manual)
                    |
                    v
            sql/ddl.sql (full schema reference)

sql/ddl.sql + sql/dml.sql + sql/admin_perf.sql
    ----reload_db.sh / integration_db.sh / integration tests---->
            local Docker "django" / "django_test" DB

No migration files exist in the repo. `migrate` is commented out of the
entrypoint; integration tests run `manage.py migrate --fake` to mark the
pre-built SQL schema as applied.
```

## 6. Test & release flow

```
feature branch → PR to master
  → GitHub Actions "Tests / test" (test-unit + test-integration + lint)
      ↑ branch protection blocks merge until it passes
master merged → Render auto-deploy (Docker build)
  → entrypoint: collectstatic → createsuperuser_if_not_exists → runserver (dev) / gunicorn (prod)
  → keep-alive cron pings every 10 min (prevents cold starts)
```

## 7. Gotchas / invariants

- **No migrations anywhere.** The whole schema is SQL-managed: `sql/ddl.sql`
  covers every table, `migrate` is commented out of the entrypoint, and tests
  use `manage.py migrate --fake` against the pre-built DDL.
- Prod (Neon) schema is applied **manually** — never rely on `migrate` in prod; never run `reload_db.sh` against prod.
- `web/build/web/` (Flutter) is **committed**; rebuild with `bash scripts/run.sh flutter` before pushing Flutter changes.
- Tests never boot gunicorn: they run in one-off containers and integration tests start their own `runserver` on `127.0.0.1:8001`.
- **Auth/TOTP:** non-staff users log in with an **authenticator app (TOTP)**, not SMS/OTP. Only `POST /api/sales_admin/auth/otp/verify` exists — there is no `otp/request`.
- **Role creation:** only superusers can create Admins; superusers *and* Admins can create SalesPeople. `VerifyOTPView` exposes this to the SPA via `can_create_admin` / `can_create_sales_person`.
- **Token TTL:** bearer tokens die `TOKEN_TTL_HOURS` (24) after their last "login"; `ExpiringTokenAuthentication` deletes an expired token on first use so the next request forces a fresh login. Session cookies share the same 24h through `SESSION_COOKIE_AGE`.
- **401 vs 403:** the custom `SessionAuthentication`/`ExpiringTokenAuthentication` return a `WWW-Authenticate` challenge header, which is what keeps anonymous calls a **401** instead of DRF's default 403.
- **CSRF is *not* enforced by the global middleware on DRF routes** (view handlers are `csrf_exempt`); only DRF `SessionAuthentication` enforces it, so the sales-admin SPA must send the `csrftoken` cookie value as `X-CSRFToken` on every session-authenticated POST/PUT/PATCH/DELETE.
- **Sentry/GlitchTip** only initialises when `SENTRY_DSN` is set and `DEBUG` is false; `/api/test-sentry/` is the wired-up probe.
- `api/admin.py` = `AdminApiView` base, not Django admin.
- Creating an **Admin** automatically creates a **fallback `SalesPerson`** for the same user.
- **Salespersons carry only `city`** — **admins carry neither `city` nor `address`**; any such keys sent to the endpoints are ignored and never persisted, and response payloads never expose `user_id`/`is_deleted`/`deleted_by`.

_Keep this graph in sync when adding apps, endpoints, models, or schema flows._
