# Sprint 2 Implementation QA (Current-State Alignment)

## Delivered features still active

- FastAPI backend with health/docs endpoints.
- Postgres schema + Alembic migrations.
- JWT auth + protected profile/dashboard endpoints.

## Alignment notes

- Frontend auth smoke panel has been removed from product UX.
- Use `.venv/bin/alembic` (not system `alembic`) for migrations.

## Verification checklist

- [X] Backend starts and docs load.
- [X] Migrations apply with venv toolchain.
- [X] Register/login + bearer auth works.
- [X] `/me` and `/dashboard/summary` return user-scoped data.
