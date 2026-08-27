# Django Configuration

> How Django is configured in this project.

---

## Settings Module

`config/settings.py` — the single settings file. No settings split (base/dev/prod).

---

## INSTALLED_APPS

```python
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]
```

Only Django's built-in apps. No custom apps yet.

---

## MIGRATION_MODULES (Critical)

Disables migrations **only** for built-in Django apps (their schema lives in `sql/ddl.sql`):

```python
MIGRATION_MODULES = {
    app.split(".")[-1]: None for app in INSTALLED_APPS if app.startswith("django.")
}
```

**Implication:** built-in apps' schema is managed via `sql/ddl.sql`. Project apps (`authentication`, `common`, `config`) use **normal Django migrations** — run `makemigrations` + `migrate` locally, then apply the resulting SQL to Neon manually (see `skills/database.md`).

---

## Database

```python
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ["POSTGRES_DB"],
        "USER": os.environ["POSTGRES_USER"],
        "PASSWORD": os.environ["POSTGRES_PASSWORD"],
        "HOST": os.environ["POSTGRES_HOST"],
        "PORT": os.environ["POSTGRES_PORT"],
    }
}
```

All 5 parameters are **required** — the app crashes at startup if any are missing.

---

## Key Settings

| Setting | Value | Notes |
|---|---|---|
| `DEFAULT_AUTO_FIELD` | `django.db.models.BigAutoField` | 64-bit IDs everywhere |
| `USE_TZ` | `True` | Timezone-aware datetimes |
| `TIME_ZONE` | `UTC` | Server timezone |
| `DEBUG` | `True` | Hardcoded, not read from env |
| `SECRET_KEY` | Hardcoded insecure key | Not read from env |

---

## Middleware Stack (in order)

1. `SecurityMiddleware`
2. `SessionMiddleware`
3. `CommonMiddleware`
4. `CsrfViewMiddleware`
5. `AuthenticationMiddleware`
6. `MessageMiddleware`
7. `XFrameOptionsMiddleware`

Standard Django middleware. No custom middleware.

---

## URL Configuration

`config/urls.py` — single route:

```python
path('admin/', admin.site.urls)
```

No API endpoints, no custom views.

---

## Adding a New App

1. `python manage.py startapp <app_name>`
2. Add `'<app_name>'` to `INSTALLED_APPS` in `config/settings.py`
3. Place it at the project root (e.g. `/authentication`, `/common`)
4. Project apps use real migrations: `makemigrations` + `migrate` locally, then apply the resulting SQL to prod manually
5. See `skills/database.md` → "Changing a Table" for the full local → prod workflow

---

## Gotchas

- **`import os` is duplicated** in `settings.py` (lines 14 and 79) — harmless but messy
- **`SECRET_KEY` and `DEBUG`** are not read from environment — needs fixing before production
- **No `STATIC_ROOT`** — `collectstatic` will fail until this is added
- **No REST framework** — no API tooling installed yet
