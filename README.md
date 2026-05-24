# NENS English Learning App — Backend

Backend service for the **NENS English Learning App**, an AI-powered English learning platform that combines test-taking, AI tutoring, social learning, and progress tracking. Built with Django REST Framework, PostgreSQL, Redis, and Google Cloud services.

---

## Table of Contents

- [Features](#features)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Environment Variables](#environment-variables)
- [Common Commands](#common-commands)
- [API Documentation](#api-documentation)
- [Architecture Notes](#architecture-notes)
- [Database & Seed Data](#database--seed-data)
- [Testing](#testing)
- [Deployment](#deployment)
- [Contributing](#contributing)
- [Documentation](#documentation)

---

## Features

- **Authentication & Accounts** — Custom JWT auth, OAuth 2.0 (Google, Facebook), role-based access (Student / Teacher / Admin), 5-state account lifecycle.
- **Test Bank** — Receptive tests (Reading / Listening) and Productive tests (Speaking / Writing) with hierarchical Part → Question → Answer model and CEFR-aligned rubrics.
- **AI Assistant** — Vertex AI-backed chat tutor with multiple modes (translate, grammar, vocabulary, brainstorm, general) and per-user quota windows.
- **Test Histories & Auto-Grading** — Student submissions with AI feedback, audio uploads, scoring, and bonus point computation.
- **Forum** — Posts, comments, reactions tied to student submissions; in-app notifications.
- **Gamification** — XP levels, streaks, completion bonuses, and milestone rewards.
- **File Storage** — Direct browser-to-GCS uploads via V4 signed URLs (two-step upload flow).
- **Observability** — OpenAPI 3 schema with Swagger UI and ReDoc out of the box.

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Language | Python 3.12 |
| Framework | Django 5.2 · Django REST Framework 3.16 |
| Auth | `djangorestframework-simplejwt` (JWT), custom OAuth 2.0 flow |
| Database | PostgreSQL 17 |
| Cache | Redis 8 (via `django-redis`) |
| File Storage | Google Cloud Storage (`django-storages[google]`) |
| AI | Google Vertex AI (`google-cloud-aiplatform`) |
| API Docs | drf-spectacular (OpenAPI 3) |
| Dependency Mgmt | Pipenv |
| Container | Docker · Docker Compose |
| Rate Limiting | `django-ratelimit` |

Full dependency list: [Pipfile](Pipfile).

---

## Project Structure

```
EngWeb-BE/
├── english_app/             # Django project (settings, root urls, wsgi/asgi)
├── accounts/                # Users, Student/Teacher profiles, OAuth, JWT
├── tests/                   # Test bank: Receptive/Productive tests, criteria
├── test_histories/          # Submission records, AI feedback, scoring
├── assistant/               # AI tutor: conversations, messages, quota
├── forum/                   # Posts, comments, reactions
├── feedback/                # Test feedback from teachers
├── notifications/           # In-app notifications
├── statistic/               # Teacher dashboards, analytics
├── storage/                 # GCS signed URL issuance
├── user_progress/           # XP levels, streaks, bonus rules
├── init/                    # SQL seed files (config + sample data)
├── docs/                    # Design docs (AI blueprint, index strategy)
├── docker-compose.yaml      # Base stack (backend + redis)
├── docker-compose.dev.yaml  # Adds local Postgres + dev entrypoint
├── docker-compose.prod.yaml # External Postgres + prod entrypoint
├── entrypoint.dev.sh        # Dev startup: migrate, seed all, runserver
├── entrypoint.prod.sh       # Prod startup: migrate, seed config only
├── Dockerfile               # Python 3.12-slim + system deps + pipenv install
├── Pipfile / Pipfile.lock   # Dependencies
└── manage.py
```

---

## Prerequisites

- **Docker Desktop** (or Docker Engine + Compose v2)
- A **Google Cloud Service Account key** with permissions for Cloud Storage and Vertex AI. Save the JSON key as `test-nens-english-app-sa-key.json` in the project root (gitignored, mounted read-only into the container).
- **OAuth 2.0 credentials** for Google and Facebook if you want to test social login.

> Python and Pipenv are **not** required on the host. All commands run inside the `english_app_api` container.

---

## Quick Start

```bash
# 1. Clone
git clone https://github.com/DATN-EngWeb/EngWeb-BE.git
cd EngWeb-BE

# 2. Create the dev env file
cp .env.example .env.dev
# then edit .env.dev — at minimum, replace SECRET_KEY and OAuth credentials

# 3. Place your GCS service account key in the project root
#    (filename must be: test-nens-english-app-sa-key.json)

# 4. Start the dev stack (Postgres + Redis + backend)
docker compose -f docker-compose.yaml -f docker-compose.dev.yaml up -d --build
```

> Docker Compose does **not** auto-load `docker-compose.dev.yaml`. You must pass `-f` flags explicitly. The dev compose adds the local `db` service and wires the dev entrypoint.

Wait for the backend log to print `Starting development server at http://0.0.0.0:8000/`, then visit:

- **App** — http://localhost:8000/
- **Admin** — http://localhost:8000/admin/ (login with `DJANGO_SUPERUSER_*` from `.env.dev`)
- **Swagger UI** — http://localhost:8000/api/docs/
- **ReDoc** — http://localhost:8000/api/redoc/

---

## Environment Variables

Copy `.env.example` and fill in the secrets. The example file is the source of truth for the full list — below is a summary of the key groups.

| Group | Variables | Notes |
|-------|-----------|-------|
| Django | `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS` | Toggle `DEBUG` to switch dev/prod auth, CORS, GCS bucket |
| Database | `DB_ENGINE`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` | `DB_HOST=db` for dev (local Postgres container) |
| Postgres (init) | `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` | Used by the `db` service on first boot |
| Redis | `REDIS_HOST`, `REDIS_PORT`, `REDIS_DB` | |
| Email (SMTP) | `EMAIL_HOST`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `EMAIL_PORT`, `EMAIL_USE_TLS`, `EMAIL_BACKEND` | Used for OTP / password reset emails |
| Superuser bootstrap | `DJANGO_SUPERUSER_USERNAME`, `DJANGO_SUPERUSER_EMAIL`, `DJANGO_SUPERUSER_PASSWORD` | Created automatically on container start |
| OAuth — Google | `OAUTH2_GOOGLE_KEY`, `OAUTH2_GOOGLE_SECRET`, `OAUTH2_GOOGLE_SCOPE`, `OAUTH2_GOOGLE_DEV_REDIRECT_URI`, `OAUTH2_GOOGLE_PRODUCTION_REDIRECT_URI` | |
| OAuth — Facebook | `OAUTH2_FACEBOOK_KEY`, `OAUTH2_FACEBOOK_SECRET`, `OAUTH2_FACEBOOK_SCOPE`, `OAUTH2_FACEBOOK_DEV_REDIRECT_URI`, `OAUTH2_FACEBOOK_PRODUCTION_REDIRECT_URI` | |
| Google Cloud Storage | `GOOGLE_APPLICATION_CREDENTIALS`, `GCS_PROJECT_ID`, `GCS_PUBLIC_BASE_URL`, `GCS_DEV_BUCKET`, `GCS_PRODUCTION_BUCKET` | `GOOGLE_APPLICATION_CREDENTIALS` points to the mounted JSON key. Active bucket is picked by `DEBUG` |
| Vertex AI | `VERTEX_AI_PROJECT_ID`, `VERTEX_AI_LOCATION`, `VERTEX_AI_MODEL`, `VERTEX_AI_TEMPERATURE` | Powers the AI assistant module. Default model `gemini-2.5-flash` in `asia-southeast1` |
| CORS | `DEV_CORS_ALLOW_ALL_ORIGINS`, `PRODUCTION_CORS_ALLOW_ALL_ORIGINS`, `PRODUCTION_CORS_ALLOWED_ORIGINS` | Dev defaults to allow-all. In prod, set `PRODUCTION_CORS_ALLOW_ALL_ORIGINS=false` and list allowed origins |

Env files (both gitignored — never commit them):

- `.env.dev` — used by `docker-compose.dev.yaml`
- `.env.prod` — used by `docker-compose.prod.yaml`

---

## Common Commands

All commands run inside the backend container (service `backend`, container `english_app_api`):

```bash
# Shell into the container
docker compose exec backend sh

# Migrations
docker compose exec backend python manage.py makemigrations
docker compose exec backend python manage.py migrate

# Create a one-off superuser (if you didn't use env-based bootstrap)
docker compose exec backend python manage.py createsuperuser

# Tail logs
docker compose logs -f english_app_api
docker compose logs -f english_app_db
docker compose logs -f english_app_cache

# Rebuild after editing the Pipfile
docker compose build backend
docker compose -f docker-compose.yaml -f docker-compose.dev.yaml up -d

# Stop everything
docker compose -f docker-compose.yaml -f docker-compose.dev.yaml down

# Hard reset (dev only — wipes the Postgres volume)
docker compose -f docker-compose.yaml -f docker-compose.dev.yaml down -v
```

---

## API Documentation

The OpenAPI 3 schema is generated automatically by drf-spectacular.

| Endpoint | Description |
|----------|-------------|
| `GET /api/docs/` | Swagger UI |
| `GET /api/redoc/` | ReDoc |
| `GET /api/schema/` | Raw OpenAPI 3 JSON |

API apps are mounted under `/api/<app>/`:

```
/api/accounts/         /api/tests/            /api/test-histories/
/api/storage/          /api/forums/           /api/feedback/
/api/statistic/        /api/user-progress/    /api/notifications/
/api/assistant/
```

Two authentication schemes are registered:

- **`CustomBearerAuth`** — JWT bearer tokens (production + dev)
- **`CustomBasicAuth`** — HTTP Basic (dev only, disabled when `DEBUG=False`)

Both reject users with `status='D'` (Disabled).

---

## Architecture Notes

### Compose stack

The stack is split across three compose files:

| File | Adds | Used for |
|------|------|----------|
| [docker-compose.yaml](docker-compose.yaml) | Base: `backend` + `redis` | Common to all environments |
| [docker-compose.dev.yaml](docker-compose.dev.yaml) | `db` (Postgres), `.env.dev`, dev entrypoint | Local development |
| [docker-compose.prod.yaml](docker-compose.prod.yaml) | `.env.prod`, prod entrypoint (external Postgres) | Production deployment |

There is **no** `docker-compose.override.yaml`, so `-f` flags are mandatory.

### Entrypoint behavior

Both [entrypoint.dev.sh](entrypoint.dev.sh) and [entrypoint.prod.sh](entrypoint.prod.sh) follow the same pipeline on each container start:

1. Wait for Postgres and Redis
2. `makemigrations --noinput`
3. `migrate --noinput`
4. Create or upgrade the superuser from `DJANGO_SUPERUSER_*` env vars
5. Seed SQL files from `init/`
   - Dev: **all** `init/*.sql` (configuration + sample users, posts, tests, etc.)
   - Prod: only `init/seed_00_*.sql` (configuration / reference data)
6. `runserver 0.0.0.0:8000`

> Production uses `runserver` for now. There is **no** gunicorn/uwsgi.

### Settings switch by `DEBUG`

[english_app/settings.py](english_app/settings.py) toggles several values on `DEBUG`:

- Auth classes — Basic auth is only enabled when `DEBUG=True`
- OAuth redirect URIs — `*_DEV_REDIRECT_URI` vs `*_PRODUCTION_REDIRECT_URI`
- GCS bucket — `GCS_DEV_BUCKET` vs `GCS_PRODUCTION_BUCKET`
- CORS — wide open in dev, allowlisted in prod

`USE_TZ=True`, `TIME_ZONE='Asia/Ho_Chi_Minh'` — UTC is stored, ICT is rendered.

### Cross-app references

Apps own bounded slices of the domain. Cross-app foreign keys use **string references** (e.g. `"accounts.Student"`) to avoid circular imports.

For a deeper guide on architecture and conventions, see [CLAUDE.md](CLAUDE.md).

---

## Database & Seed Data

PostgreSQL is the system of record. Local dev provisions Postgres 17 inside Docker; production points at an externally managed instance via env vars.

Seed SQL files live in [init/](init/) and are executed by `psql` at container start:

| File | Purpose | Run in prod? |
|------|---------|--------------|
| `seed_00_*.sql` | Reference / configuration data (CEFR rubrics, user levels, bonus rules, streak rewards) | Yes |
| `seed_01_*.sql` … `seed_10_*.sql` | Sample users, tests, submissions, posts | No (dev only) |

Index strategy and query analysis: [docs/database_index_strategy.md](docs/database_index_strategy.md).

---

## Testing

Tests use the built-in Django test runner:

```bash
# Full suite
docker compose exec backend python manage.py test

# Single app
docker compose exec backend python manage.py test accounts

# Single test case / method
docker compose exec backend python manage.py test tests.tests.SomeTestCase.test_method
```

---

## Deployment

Production deployment is triggered automatically on `push` to `main` by [.github/workflows/cd.yml](.github/workflows/cd.yml):

1. SSH into the production VM
2. `docker compose down` the running stack
3. `git pull origin main`
4. `docker compose up -d` with the prod compose files
5. Verify the backend container reports `Up` status

SSH credentials are stored in GitHub Actions secrets (`SSH_HOST`, `SSH_USER`, `SSH_PRIVATE_KEY`, `SSH_PORT`). The production server must have its own `.env.prod` and GCS service account key in place.

---

## Contributing

Full ruleset: [.github/instructions/git-workflow.instructions.md](.github/instructions/git-workflow.instructions.md). Highlights:

- **Default PR base is `dev`**, not `main`. `main` is the deployment branch (push → CD).
- **Conventional Commits** are required:
  ```
  <type>(<scope>): <subject>
  ```
  Allowed types: `feat`, `fix`, `refactor`, `perf`, `test`, `docs`, `build`, `ci`, `chore`, `revert`. Subject in lowercase imperative, no trailing period. Keep commits atomic.
- **PR title format**:
  ```
  [DATN-<n>][BE-<nnnn>] <short-title>
  ```
  Both ticket keys are required. If either is missing from the branch name, ask before opening the PR. Append `(ver2)`, `(ver3)`, … if the same title already exists on a merged-to-`dev` PR.
- **PR body** must include: `Why`, `What Changed`, `DB/Migration Impact`, `API Impact`, `Test Evidence`, `Risks and Rollback`.

When adding or changing models, commit the resulting migration files alongside the model changes.

---

## Documentation

| Doc | Contents |
|-----|----------|
| [CLAUDE.md](CLAUDE.md) | Architecture, conventions, and operational guide |
| [docs/ai-assistant-blueprint.md](docs/ai-assistant-blueprint.md) | AI assistant design (modes, prompts, quota model) |
| [docs/database_index_strategy.md](docs/database_index_strategy.md) | Index strategy, table sizing, query patterns |
| [.github/instructions/git-workflow.instructions.md](.github/instructions/git-workflow.instructions.md) | Branching, commits, PR rules |
