#!/bin/sh
set -e

echo "Waiting for database..."
while ! python -c "
import os, psycopg2
try:
    psycopg2.connect(
        dbname=os.environ.get('DB_NAME','moviedb'),
        user=os.environ.get('DB_USER','postgres'),
        password=os.environ.get('DB_PASSWORD','postgres'),
        host=os.environ.get('DB_HOST','db'),
        port=os.environ.get('DB_PORT','5432'),
    )
    print('DB ready')
except Exception as e:
    exit(1)
" 2>/dev/null; do
    echo "  DB not ready, retrying in 2s..."
    sleep 2
done

echo "Running migrations..."
python manage.py migrate --noinput

echo "Collecting static files..."
python manage.py collectstatic --noinput --clear 2>/dev/null || true

echo "Starting server..."
exec gunicorn core.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers 2 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile -
