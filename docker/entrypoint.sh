#!/bin/sh
set -e

echo "Waiting for postgres at ${POSTGRES_HOST:-db}:${POSTGRES_PORT:-5432}..."
uv run python -c "
import os, sys, time, psycopg
for _ in range(60):
    try:
        psycopg.connect(
            host=os.environ.get('POSTGRES_HOST', 'db'),
            port=os.environ.get('POSTGRES_PORT', '5432'),
            user=os.environ.get('POSTGRES_USER', 'postgres'),
            password=os.environ.get('POSTGRES_PASSWORD', 'postgres'),
            dbname=os.environ.get('POSTGRES_DB', 'backend_devops_interview'),
        ).close()
        sys.exit(0)
    except psycopg.OperationalError:
        time.sleep(1)
sys.exit(1)
"

echo "Applying migrations..."
uv run python manage.py migrate --noinput

exec "$@"
