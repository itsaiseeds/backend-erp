#!/bin/bash
set -e

# Dont push to prod without commenting out the following line. It will apply migrations on every deploy and can cause issues if not handled properly.
# echo "Applying migrations ..."
# python manage.py migrate

echo "Collecting static files ..."
python manage.py collectstatic --noinput

echo "Running createsuperuser_if_not_exists ..."
python manage.py createsuperuser_if_not_exists

echo "Starting gunicorn ..."
exec gunicorn --bind 0.0.0.0:8000 config.wsgi:application
