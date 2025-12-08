#!/usr/bin/env bash
set -euo pipefail

# Wait for Postgres to be ready (host: db, port: 5432)
echo "Waiting for Postgres (db:5432)..."
until nc -z db 5432; do
  sleep 1
done
echo "Postgres is up."

# Create migrations for all apps (development only)
echo "Creating migrations..."
python manage.py makemigrations --noinput

# Apply migrations
echo "Applying migrations..."
python manage.py migrate --noinput

# Create superuser using mandatory env vars (no defaults)
python - <<'PY'
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'english_app.settings')
django.setup()
from django.contrib.auth import get_user_model

username = os.environ['DJANGO_SUPERUSER_USERNAME']
email = os.environ['DJANGO_SUPERUSER_EMAIL']
password = os.environ['DJANGO_SUPERUSER_PASSWORD']

User = get_user_model()
if not User.objects.filter(username=username).exists():
    User.objects.create_superuser(username=username, email=email, password=password)
    print(f"Created superuser: {username} / {email}")
else:
    print(f"Superuser '{username}' already exists. Skipping creation.")
PY

exec python manage.py runserver 0.0.0.0:8000
