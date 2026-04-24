# Sprint 2 — Backend + Database (Current-State Aligned)

## Objective

Ship the first persistent authenticated backend and DB schema that the current product still relies on.

## What is implemented and still active

- FastAPI service with health/docs and versioned router.
- Core SQLAlchemy/Alembic stack for `users`, `threads`, `messages`.
- JWT auth foundation (`/auth/register`, `/auth/login`) and protected `/me`.
- User-scoped dashboard summary endpoint (`/dashboard/summary`).

## Alignment updates since original sprint notes

- Frontend smoke-panel references are removed from product UX.
- Runtime docs now require venv commands:
  - `.venv/bin/alembic -c db/alembic.ini upgrade head`
  - `.venv/bin/uvicorn backend.app.main:app ...`
- Current app uses auth pages (`/login`, `/register`) instead of test panel controls.

## Key modules

- `backend/app/main.py`
- `backend/app/api/routes/auth.py`
- `backend/app/api/routes/users.py`
- `backend/app/api/routes/dashboard.py`
- `backend/app/models/*`
- `db/migrations/versions/20260422_0001_initial_schema.py`

## Runbook

```bash
cd opsmesh-ai
python3 -m venv .venv
.venv/bin/pip install -e ./backend
docker compose up -d postgres
.venv/bin/alembic -c db/alembic.ini upgrade head
.venv/bin/uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

## Exit criteria (retroactive)

- Auth and persistence foundation remains stable for current product flows.
