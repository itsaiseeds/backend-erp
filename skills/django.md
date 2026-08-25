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

```python
MIGRATION_MODULES = {app.split(".")[-1]: None for app in INSTALLED_APPS}
```

This disables Django's migration system for ALL installed apps. Produces:

```python
{
    'admin': None,
    'auth': None,
    'contenttypes': None,
    'sessions': None,
    'messages': None,
    'staticfiles': None,
}
```

**Implication:** When you add a new app to `INSTALLED_APPS`, it is automatically included in `MIGRATION_MODULES`. You must manage its schema via raw SQL in `sql/ddl.sql`.

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
3. The `MIGRATION_MODULES` dict comprehension auto-disables migrations for it
4. Write models as reference — define actual schema in `sql/ddl.sql`
5. Add content types + permissions to `sql/dml.sql` if the app has models
6. Create URL patterns in `<app_name>/urls.py` and include in `config/urls.py`

---

## Gotchas

- **`import os` is duplicated** in `settings.py` (lines 14 and 79) — harmless but messy
- **`SECRET_KEY` and `DEBUG`** are not read from environment — needs fixing before production
- **No `STATIC_ROOT`** — `collectstatic` will fail until this is added
- **No REST framework** — no API tooling installed yet
