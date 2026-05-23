# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Stack

Django 5.2 + DRF + PostgreSQL 17 + Redis 8 + Google Cloud Storage + Vertex AI. Python 3.12, dependencies managed by Pipenv (`Pipfile` / `Pipfile.lock`). Containerized via Docker Compose — local dev does NOT install Python directly; everything runs inside the `english_app_api` container.

## Running the app

The dev compose stack is split across three files: [docker-compose.yaml](docker-compose.yaml) (backend + redis services), [docker-compose.dev.yaml](docker-compose.dev.yaml) (adds postgres `db`, wires `.env.dev`, runs `entrypoint.dev.sh`), and [docker-compose.prod.yaml](docker-compose.prod.yaml) (no `db` service — prod uses an external Postgres, wires `.env.prod`, runs `entrypoint.prod.sh`).

Docker Compose auto-loads `docker-compose.yaml` + `docker-compose.override.yaml` by default. There is no `override.yaml` here, so dev requires the `-f` flags:

```bash
# Dev (with local Postgres in db service)
docker compose -f docker-compose.yaml -f docker-compose.dev.yaml up -d --build

# Prod (external Postgres)
docker compose -f docker-compose.yaml -f docker-compose.prod.yaml up -d --build
```

[entrypoint.dev.sh](entrypoint.dev.sh) runs `makemigrations` automatically on every container start (prod also does this — see [entrypoint.prod.sh](entrypoint.prod.sh)), then `migrate`, then creates/upgrades the superuser from `DJANGO_SUPERUSER_*` env vars, then seeds from `init/*.sql`. Dev runs all `init/*.sql`; prod runs only `init/seed_00_*.sql` (config/reference data — users, posts, etc. are not re-seeded in prod). Both end with `runserver 0.0.0.0:8000` — there is no gunicorn/uwsgi.

## Common commands

All commands run inside the backend container (service name `backend`, container name `english_app_api`):

```bash
# Shell into container
docker compose exec backend sh

# Migrations
docker compose exec backend python manage.py makemigrations
docker compose exec backend python manage.py migrate

# Tests — full suite / single app / single test
docker compose exec backend python manage.py test
docker compose exec backend python manage.py test accounts
docker compose exec backend python manage.py test tests.tests.SomeTestCase.test_method

# Tail logs
docker compose logs -f english_app_api
docker compose logs -f english_app_db
docker compose logs -f english_app_cache

# Hard reset DB (erases volume — dev only)
docker compose down -v
```

After editing `Pipfile`: `docker compose build backend && docker compose up -d` (the image bakes deps in via `pipenv install --deploy --system`).

## URLs

- API root: `http://localhost:8000/`
- Admin: `/admin/`
- Swagger UI: `/api/docs/`, ReDoc: `/api/redoc/`, OpenAPI JSON: `/api/schema/`
- App routes mounted under `/api/<app>/` — see [english_app/urls.py](english_app/urls.py).

## Architecture

### Apps and ownership

Each Django app owns one bounded slice of the domain. Cross-app references use string FKs (`"accounts.Student"`) to avoid circular imports.

- **[accounts/](accounts/)** — Custom `User` extending `AbstractUser` with `role` (`S`/`T`/`A`) and a 5-state `status` lifecycle (`P` Pending → `I` Incomplete → `W` Waiting → `V` Verified, plus `D` Disabled). Two satellite profile models, `Teacher` and `Student`, hang off `User` via `OneToOneField(primary_key=True)`. Authentication is custom: `accounts.authentication.CustomTokenAuthentication` wraps simplejwt's `JWTAuthentication` to reject users with `status=='D'`; `CustomBasicAuthentication` does the same for HTTP Basic (DEBUG only). Views split across [accounts/views/](accounts/views/) (authentication, registration, password, student, teacher, admin).
- **[tests/](tests/)** — Test bank. `Test` is the base, with `OneToOneField` to `ReceptiveTest` (Reading/Listening) or `ProductiveTest` (Speaking/Writing). DB-level `CheckConstraint` enforces `type='R' ↔ skill∈{R,L}` and `type='P' ↔ skill∈{S,W}`. Receptive tests have `Part → Question → Answer` hierarchy. `WritingCriteriaTemplate`, `SpeakingCriteriaTemplate`, `ReadingCriteriaTemplate` are global rubrics keyed by CEFR `level`. Views, serializers, and utils are subdirectories (not single files): [tests/views/](tests/views/), [tests/serializers/](tests/serializers/), [tests/utils/](tests/utils/).
- **[test_histories/](test_histories/)** — Student submission records (`ProductiveTestHistory`, `ReceptiveTestHistory`) including AI feedback, audio paths, scoring, and streak/level bonus computation.
- **[user_progress/](user_progress/)** — `UserLevel` (XP bands), `CompletedBonus`, `EXPBonusRule`, streak reward rules. Util `sync_student_level_from_cumulative_point` recomputes a student's level FK on points change; call it whenever points are awarded.
- **[storage/](storage/)** — Issues GCS V4 signed URLs ([storage/utils/gcs_presigned.py](storage/utils/gcs_presigned.py)) for direct browser→GCS uploads. Two-step flow: client requests presigned URL → uploads to GCS → calls confirmation endpoint. Categories (`avatars`, `covers`, `credentials`, `tests`) determine path layout and allowed MIME types. S3 variant exists in [storage/utils/s3_presigned.py](storage/utils/s3_presigned.py) but GCS is the default.
- **[assistant/](assistant/)** — AI tutor chat backed by Vertex AI (model from `VERTEX_AI_MODEL` env). `AssistantConversation` with modes `translate|grammar|vocabulary|brainstorm|general`, `AssistantMessage` per turn, and `AssistantQuota` (per-user rolling window — defaults: 50 messages / 12h, see `ASSISTANT_QUOTA_*` in [english_app/settings.py](english_app/settings.py)). Design doc: [docs/ai-assistant-blueprint.md](docs/ai-assistant-blueprint.md).
- **[forum/](forum/)**, **[feedback/](feedback/)**, **[notifications/](notifications/)**, **[statistic/](statistic/)** — Posts/comments/reactions, test feedback, in-app notifications, teacher dashboards.

### Settings switch by `DEBUG`

[english_app/settings.py](english_app/settings.py) toggles several values on `DEBUG`:
- Auth classes (Basic auth is only enabled when `DEBUG=True`).
- OAuth redirect URIs (`OAUTH2_*_DEV_REDIRECT_URI` vs `_PRODUCTION_`).
- GCS bucket (`GCS_DEV_BUCKET` vs `GCS_PRODUCTION_BUCKET`).
- CORS (`DEV_CORS_ALLOW_ALL_ORIGINS` vs `PRODUCTION_CORS_ALLOWED_ORIGINS`).

`USE_TZ=True`, `TIME_ZONE='Asia/Ho_Chi_Minh'` — store UTC, render in ICT.

### drf-spectacular conventions

Two custom auth schemes are registered in [accounts/schema.py](accounts/schema.py): `CustomBearerAuth` (JWT) and `CustomBasicAuth`. They're referenced in `SPECTACULAR_SETTINGS["SECURITY"]`. Existing views use `@extend_schema(...)` with Vietnamese descriptions — that's intentional, not a translation error.

### Migration discipline

`makemigrations` runs automatically inside the container entrypoint. Fresh `0001_initial.py` migration files may appear in your working tree after `docker compose up` if you've never committed migrations for a new app. `git add` migration files alongside model changes.

## Git workflow

See [.github/instructions/git-workflow.instructions.md](.github/instructions/git-workflow.instructions.md) for the full ruleset. Key points:

- Default PR base is **`dev`**, not `main`. `main` is the deployment branch (CD via [.github/workflows/cd.yml](.github/workflows/cd.yml) on push to `main`).
- Conventional Commits required: `<type>(<scope>): <subject>` with lower-case imperative subjects, no trailing period. Allowed types: `feat`, `fix`, `refactor`, `perf`, `test`, `docs`, `build`, `ci`, `chore`, `revert`. Keep commits atomic — split mixed concerns into separate commits, stage explicitly per group (don't use broad staging).
- PR titles must carry both ticket keys: `[DATN-<n>][BE-<nnnn>] <short-title>` derived from branch name (strip `feature/`, `fix/`, ticket keys, separators).
- PR body must include: `Why`, `What Changed`, `DB/Migration Impact`, `API Impact`, `Test Evidence`, `Risks and Rollback`.
- If the same title exists on merged-to-`dev` PRs, append `(ver2)`, `(ver3)`, ...
- If either ticket key is missing from the branch name, ask the user before opening the PR.

## Deployment

Push to `main` triggers SSH-into-VM deploy ([.github/workflows/cd.yml](.github/workflows/cd.yml)): stops containers, `git pull`, `docker compose up -d`, then polls `http://localhost:8000/health` up to 30× / 10s.

## Secrets

- `.env`, `.env.dev`, `.env.prod` are gitignored. Only `.env.example` is tracked.
- `test-nens-english-app-sa-key.json` is the GCS service account key mounted read-only into the container at `/app/test-nens-english-app-sa-key.json` (path in `docker-compose.yaml`). Gitignored.
