#!/usr/bin/env bash
set -euo pipefail

# Wait for Postgres to be ready (host: db, port: 5432)
echo "Waiting for Postgres (db:5432)..."
until nc -z db 5432; do
  sleep 1
done
echo "✓ Postgres is up."

# Wait for Redis to be ready
echo "Waiting for Redis (redis:6379)..."
until nc -z redis 6379; do
  sleep 1
done
echo "✓ Redis is up."

# Wait for MinIO to be ready
echo "Waiting for MinIO (minio:9000)..."
until nc -z minio 9000; do
  sleep 1
done
echo "✓ MinIO is up."

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
    user = User.objects.create_superuser(username=username, email=email, password=password)
    # Set status to 'V' (Verified) for admin
    user.status = 'V'
    user.save()
    print(f"Created superuser: {username} / {email}")
else:
    # Update existing superuser to ensure status is 'V'
    user = User.objects.get(username=username)
    if user.status != 'V':
        user.status = 'V'
        user.save()
        print(f"Updated superuser '{username}' status to V")
    else:
        print(f"Superuser '{username}' already exists with status=V. Skipping creation.")
PY

exec python manage.py runserver 0.0.0.0:8000
