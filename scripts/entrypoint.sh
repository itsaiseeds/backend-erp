#!/bin/bash
set -e

echo "Running createsuperuser_if_not_exists ..."
python manage.py createsuperuser_if_not_exists

echo "Starting gunicorn ..."
exec gunicorn --bind 0.0.0.0:8000 config.wsgi:application
