# OpsMesh AI

Messaging-first, multi-agent AI operations platform with a Next.js frontend, FastAPI backend, Postgres storage, orchestration agents, and Photon bridge support for multi-channel messaging.

## Project Root And Paths

All commands below assume this repo root:

```bash
/home/anthony/OpenMeshAI/opsmesh-ai
```

Key folders:

- `app/` - Next.js app routes (dashboard + auth)
- `components/` - shared UI components
- `backend/` - FastAPI backend package and API logic
- `db/` - Alembic config and migrations
- `agents/` - orchestration, tools, and agent tests
- `messaging/` - channel abstractions and Photon bridge
- `scripts/` - utility scripts (including data seeding)
- `docs/` - specs, QA docs, and local dev ops notes

## Tech Stack

- Frontend: Next.js 15 + React 19 + TypeScript + Tailwind
- Backend: FastAPI + SQLAlchemy + Alembic
- Database: Postgres 16 (Docker Compose)
- Messaging: local stub or Photon SDK bridge mode

## One-Time Setup

From `/home/anthony/OpenMeshAI/opsmesh-ai`:

```bash
cp .env.example .env
npm install
python3 -m venv .venv
.venv/bin/pip install -e ./backend
```

Edit `.env` to match your local setup:

Required baseline values:

- `NEXT_PUBLIC_APP_URL=http://localhost:3000`
- `NEXT_PUBLIC_API_URL=http://localhost:8002`
- `API_URL=http://localhost:8002`
- `BACKEND_CORS_ORIGINS=http://localhost:3000`
- `ALLOWED_ORIGINS=http://localhost:3000`
- `DATABASE_URL=postgresql+asyncpg://opsmesh:opsmesh@localhost:5432/opsmesh`
- `JWT_SECRET=<use-a-long-random-value>`
- `JWT_ISSUER=opsmesh-ai`
- `SESSION_COOKIE_NAME=opsmesh_session`
- `OPENAI_MODEL=gpt-5.4`
- `EMBEDDING_MODEL=text-embedding-3-small`
- `MESSAGING_TRANSPORT_MODE=photon_sdk`
- `ENABLE_INBOUND_AUTO_REPLY=true`
- `FEATURE_MESSAGING_SMS=true`
- `FEATURE_MESSAGING_WHATSAPP=true`
- `FEATURE_MESSAGING_IMESSAGE=true`
- `FEATURE_MESSAGING_SNAPCHAT=false`

Photon bridge values:

- `PHOTON_BRIDGE_URL=http://127.0.0.1:8787`
- `PHOTON_BRIDGE_TOKEN=dev-bridge-token`
- `PHOTON_WEBHOOK_SECRET=dev-photon-secret`

Optional/feature values:

- `OPENAI_API_KEY=<optional, set when using hosted LLM features>`
- `VECTOR_DB_URL=http://localhost:6333`
- `PHOTON_PROJECT_ID=<optional>`
- `PHOTON_PROJECT_SECRET=<optional>`
- `PHOTON_BRIDGE_THREAD_ID=<optional, enables automatic persistence for inbound bridge events>`
- `OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318`
- `OTEL_SERVICE_NAME=opsmesh-api`
- `LOG_LEVEL=info`

Photon-only setup note: no Twilio fields are required.

## Run Everything Locally (Recommended Order)

Use separate terminals for each long-running service.

### Terminal 1 - Database

```bash
cd /home/anthony/OpenMeshAI/opsmesh-ai
docker compose up -d postgres
```

### Terminal 2 - Backend API

```bash
cd /home/anthony/OpenMeshAI/opsmesh-ai
.venv/bin/alembic -c db/alembic.ini upgrade head
.venv/bin/uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8002
```

Backend URLs:

- API docs: [http://localhost:8002/docs](http://localhost:8002/docs)
- Health endpoint: [http://localhost:8002/api/v1/health](http://localhost:8002/api/v1/health)

### Terminal 3 - Frontend

```bash
cd /home/anthony/OpenMeshAI/opsmesh-ai
npm run dev
```

Frontend URLs:

- App: [http://localhost:3000](http://localhost:3000)
- Auth pages: [http://localhost:3000/login](http://localhost:3000/login), [http://localhost:3000/register](http://localhost:3000/register)
- Main pages: [http://localhost:3000/](http://localhost:3000/), [http://localhost:3000/settings](http://localhost:3000/settings)

### Terminal 4 (Optional) - Photon Bridge

Only needed when using Photon SDK transport mode:

```bash
cd /home/anthony/OpenMeshAI/opsmesh-ai
npm run photon:bridge
```

Default bridge port is `8787`.

## Seed Demo Data

After backend + database are running:

```bash
cd /home/anthony/OpenMeshAI/opsmesh-ai
.venv/bin/python scripts/seed_data.py
```

This seeds transactions, support tickets, compliance records, and audit logs.

## Test And Validation Commands

From `/home/anthony/OpenMeshAI/opsmesh-ai`:

```bash
npm run lint
npm run build
.venv/bin/pytest agents/tests
```

## Useful API Endpoints

- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `GET /api/v1/me`
- `GET /api/v1/dashboard/summary`
- `POST /api/v1/conversations`
- `POST /api/v1/conversations/{thread_id}/messages`
- `POST /api/v1/messaging/send`
- `POST /api/v1/messaging/webhooks/{channel}`

## Stop Services

From `/home/anthony/OpenMeshAI/opsmesh-ai`:

```bash
docker compose down
```

## Notes

- Use the virtualenv binaries (`.venv/bin/...`) for `alembic`, `uvicorn`, `pytest`, and Python scripts.
- For local operations notes (including recovery/admin commands), see `docs/local-dev-ops.yml`.
