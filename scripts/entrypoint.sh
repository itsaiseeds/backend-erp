#!/bin/bash
set -e

WEB_BUILD_DIR="/app/web/build/web"

# Build Flutter if build output is missing (local dev with volume mount)
if [ ! -f "$WEB_BUILD_DIR/index.html" ]; then
    echo "[entrypoint] Flutter build not found. Building ..."
    export PATH="/opt/flutter/bin:$PATH"
    cd /app/web
    flutter pub get
    flutter build web --release --base-href /sales-admin/
    cd /app
    echo "[entrypoint] Flutter build complete."
fi

echo "Running createsuperuser_if_not_exists ..."
python manage.py createsuperuser_if_not_exists

echo "Starting gunicorn ..."
exec gunicorn --bind 0.0.0.0:8000 config.wsgi:application
