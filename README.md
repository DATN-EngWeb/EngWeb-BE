## Backend (Django) – Docker Dev Guide

### 1) Environment setup

- Requirement: Docker Desktop.
- Create `.env` from the example:
```
copy .env.example .env
```
- Only replace `SECRET_KEY` with your own secret (do not commit it). Other variables can stay as defaults for development.

- `.env.example` variables (quick reference):
```
# Django
SECRET_KEY=... (must be replaced)
DEBUG=true
ALLOWED_HOSTS=localhost,127.0.0.1

# Database
DB_ENGINE=django.db.backends.postgresql
DB_NAME=english_app
DB_USER=english
DB_PASSWORD=english
DB_HOST=db
DB_PORT=5432

# Postgres container
POSTGRES_DB=english_app
POSTGRES_USER=english
POSTGRES_PASSWORD=english

# Redis
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0

# Superuser
DJANGO_SUPERUSER_USERNAME=admin
DJANGO_SUPERUSER_EMAIL=admin@gmail.com
DJANGO_SUPERUSER_PASSWORD=admin
```

### 2) Build & run

- Start (PowerShell):
```
docker compose up -d --build
```
- Tail logs per service until you see these markers:
  - Postgres (`english_app_db`): `database system is ready to accept connections`
  - Redis (`english_app_cache`): `Ready to accept connections tcp`
  - Backend (`english_app_api`): `Starting development server at http://0.0.0.0:8000/`
```
docker compose logs -f english_app_db
docker compose logs -f english_app_cache
docker compose logs -f english_app_api
```
- Access:
  - App: http://localhost:8000/
  - Admin: http://localhost:8000/admin/
  - Swagger UI: http://localhost:8000/api/docs/
  - OpenAPI schema: http://localhost:8000/api/schema/
  - MinIO: http://localhost:9000/

### 3) Day-to-day commands

- Apply migrations manually (when you add new migrations):
```
docker compose exec backend python manage.py migrate
```
- Make migrations (when changing models):
```
docker compose exec backend python manage.py makemigrations
```
- Shell into the container:
```
docker compose exec backend sh
```
- Add packages (edit `requirements.txt` then rebuild):
```
docker compose build backend && docker compose up -d
```
- Run tests:
```
docker compose exec backend python manage.py test
```
- Stream logs:
```
docker compose logs -f backend
```
- Stop and remove (including volumes – this will erase DB data):
```
docker compose down -v
```

### 4) Runtime architecture

- `backend/Dockerfile` runs `/app/entrypoint.sh` (CMD).
- `entrypoint.sh` does: wait for Postgres → migrate → create superuser from `.env` → `runserver 0.0.0.0:8000`.
- Compose loads `.env` only for `db` and `redis`; `backend` uses the image CMD.

### 5) Swagger (drf-spectacular)

- Endpoints:
  - `/api/docs/` – Swagger UI
  - `/api/redoc/` – ReDoc
  - `/api/schema/` – OpenAPI JSON
- Sample endpoint: `GET /api/health/` (AllowAny) for quick checks.

### 6) Troubleshooting

- Postgres missing password:
  - Add `POSTGRES_PASSWORD` (and `POSTGRES_USER`, `POSTGRES_DB`) to `.env`, then `docker compose down -v && docker compose up -d`.
- psycopg/libpq errors:
  - The image installs `libpq5, libpq-dev, netcat-openbsd`. Rebuild if you used a cached image.
- 0.0.0.0 cannot be opened in browser:
  - 0.0.0.0 is a bind address; access via http://localhost:8000 instead.


