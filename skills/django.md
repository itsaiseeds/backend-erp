# Django Configuration

> How Django is configured in this project.

---

## Settings Module

`config/settings.py` — the single settings file. No settings split (base/dev/prod).
Nearly every value is env-driven with sensible fallbacks. **KISS:** one file to
read, no inheritance chain to hunt through.

---

## INSTALLED_APPS

```python
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "rest_framework",
    "rest_framework.authtoken",
    "drf_spectacular",
    "authentication",
    "common",
    "config",
    "api",
    "aggregator",
]
```

Project apps: `authentication` (User/Admin/SalesPerson + TOTP), `common` (abstract
bases + admin helpers), `api` (REST layer), `aggregator` (geo master data).

---

## MIGRATION_MODULES (Critical)

Disables migrations **only** for built-in Django apps:

```python
MIGRATION_MODULES = {
    app.split(".")[-1]: None for app in INSTALLED_APPS if app.startswith("django.")
}
```

**Implication:** the project keeps **no migration files at all** (YAGNI — no
migration machinery to invent or maintain). The whole schema — built-in and
project apps — lives in one authoritative `sql/ddl.sql` (plus `sql/dml.sql`
seed data); `migrate` is commented out of `scripts/entrypoint.sh`. With no
migrations, pytest-Django's test DB is synced straight from the models and
`tests/common.py` re-seeds the `sql/dml.sql` rows. Local DB rebuilds go
through `bash scripts/reload_db.sh --step all`.

---

## Database

```python
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("POSTGRES_DB", "django"),
        "USER": os.environ.get("POSTGRES_USER", "django"),
        "PASSWORD": os.environ.get("POSTGRES_PASSWORD", ""),
        "HOST": os.environ.get("POSTGRES_HOST", "localhost"),
        "PORT": os.environ.get("POSTGRES_PORT", "5432"),
        "CONN_MAX_AGE": int(os.environ.get("CONN_MAX_AGE", "60")),
        "CONN_HEALTH_CHECKS": True,
        "OPTIONS": {"options": "-c timezone=Asia/Kolkata"},
    }
}
```

- `CONN_MAX_AGE` keeps connections pooled across requests (big latency win
  against managed Postgres); set `CONN_MAX_AGE=0` to opt out.
- The session timezone is Asia/Kolkata at the DB connection level.

---

## Key Settings

| Setting | Value | Notes |
|---|---|---|
| `AUTH_USER_MODEL` | `authentication.User` | Custom user, `phone_number` is the username |
| `DEFAULT_AUTO_FIELD` | `django.db.models.BigAutoField` | 64-bit IDs everywhere |
| `TIME_ZONE` / `USE_TZ` | `Asia/Kolkata` / `True` | TZ-aware datetimes |
| `DEBUG` / `SECRET_KEY` | env-driven fallbacks | `DEBUG` defaults truthy for dev; Render sets `False` + real key |
| `ALLOWED_HOSTS` | env-driven, comma-separated | default empty |
| `PASSWORD_HASHERS` | Argon2 first, PBKDF2... fallback | Argon2 verifies ~5-10x faster; old hashes rehash on next set/reset |
| `TOKEN_TTL_HOURS` | `24` (env) | Bearer-token expiry clock |
| `SESSION_COOKIE_AGE` | `86400` | 24h, matches the token TTL |
| `STATIC_ROOT` | `staticfiles` | Served via WhiteNoise (`CompressedManifestStaticFilesStorage`) |
| `FLUTTER_BUILD_DIR` | `web/build/web` | Served by `config/views.flutter_catch_all`, not collectstatic |

---

## Middleware Stack (in order)

1. `corsheaders.middleware.CorsMiddleware`
2. `SecurityMiddleware`
3. `whitenoise.middleware.WhiteNoiseMiddleware`
4. `SessionMiddleware`
5. `CommonMiddleware`
6. `CsrfViewMiddleware`
7. `AuthenticationMiddleware`
8. `MessageMiddleware`
9. `XFrameOptionsMiddleware`

CORS + WhiteNoise sit in front of Django's own stack. The global
`CsrfViewMiddleware` still runs, but DRF routes effectively bypass it because
DRF wraps its view handlers in `csrf_exempt` (see `skills/api.md`).

---

## Django REST Framework

```python
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "api.authentication.SessionAuthentication",
        "api.authentication.ExpiringTokenAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}
```

- Default auth = session (admin web) + expiring bearer token (Android), both
  custom classes from `api/authentication.py`.
- `TOKEN_TTL_HOURS` (default 24) and `SESSION_COOKIE_AGE` (86400) share the same
  login clock.
- drf-spectacular generates OpenAPI at `/api/schema/` and Swagger at `/api/docs/`
  (both superuser-only).

## Error tracking (Sentry / GlitchTip)

```python
SENTRY_DSN = os.environ.get("SENTRY_DSN", "")
if SENTRY_DSN and not DEBUG:
    sentry_sdk.init(dsn=SENTRY_DSN, ... auto_session_tracking=True ...)
```

Only initialises when `SENTRY_DSN` is set **and** `DEBUG` is false. The
`/api/test-sentry/` endpoint (`api/test_sentry.py`) raises on purpose to probe
it. In development there is no Sentry, so the probe just returns a Django 500.

## URL Configuration

`config/urls.py`:

- `/admin/` → Django admin
- `/api/` → `api.urls` (sales_admin, android v1, test-sentry)
- `/api/schema/` + `/api/docs/` → drf-spectacular (superuser only)
- `/sales-admin/...` → Flutter catch-all (`config/views.py`)

## Adding a New App

1. `python manage.py startapp <app_name>`
2. Add `'<app_name>'` to `INSTALLED_APPS` in `config/settings.py`
3. Place it at the project root (e.g. `/aggregator`, `/authentication`)
4. Add its tables to `sql/ddl.sql` and its content types/permissions (+ any seed
   rows) to `sql/dml.sql`, then `bash scripts/reload_db.sh --step all` locally
5. Apply the same DDL manually to Neon (prod) — see `skills/database.md`

---

## Gotchas

- **No migration files exist.** Don't reach for `makemigrations`/`migrate` to
  change schema — edit the model, then update `sql/ddl.sql`/`sql/dml.sql`.
- The pytest test DB is synced straight from the models (no migrations);
  `tests/common.py` re-seeds the `sql/dml.sql` rows.
- `credentials`-style secrets (`SECRET_KEY`, `POSTGRES_PASSWORD`) come from env;
  `.env` (prod) is gitignored, `.env.dev` (dev) is committed with placeholders.
- Old PBKDF2 hashes keep working; passphrases only move to Argon2 on the next
  password set/reset (see `sql/admin_perf.sql` header).