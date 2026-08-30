#!/bin/bash
set -e

# Dont push to prod without commenting out the following line. It will apply migrations on every deploy and can cause issues if not handled properly.
# echo "Applying migrations ..."
# python manage.py migrate

echo "Collecting static files ..."
python manage.py collectstatic --noinput

echo "Running createsuperuser_if_not_exists ..."
python manage.py createsuperuser_if_not_exists

# Live reload is LOCAL DEV ONLY. Gunicorn never reloads code on its own, so in
# dev (DEBUG explicitly truthy, as in .env.dev) we run Django's dev server
# (runserver) which reloads on file changes via its stat-based reloader that
# works reliably on bind mounts. Any other environment (prod DEBUG=False, or
# DEBUG unset) must NOT reload, so it always runs plain gunicorn.
DEBUG_VALUE=$(echo "${DEBUG:-false}" | tr '[:upper:]' '[:lower:]')
case "$DEBUG_VALUE" in
    true|1|yes)
        echo "Starting Django dev server with live reload (DEBUG=$DEBUG) ..."
        exec python manage.py runserver 0.0.0.0:8000
        ;;
    *)
        echo "Starting gunicorn ..."
        # Gunicorn default is a single sync worker, which serialises requests on
        # small hosts. Threads multiplex admin/API requests on one process with
        # minimal memory; tune via GUNICORN_WORKERS / GUNICORN_THREADS env.
        exec gunicorn --bind 0.0.0.0:8000 \
            --workers "${GUNICORN_WORKERS:-1}" \
            --threads "${GUNICORN_THREADS:-4}" \
            config.wsgi:application
        ;;
esac
