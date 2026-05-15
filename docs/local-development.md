# Local Development Runbook

This guide shows how to run OpsMesh AI locally, including the web app, API,
Postgres database, Photon bridge, and database GUI.

All commands assume this repo root:

```bash
cd /home/anthony/OpenMeshAI/opsmesh-ai
```

## What Runs Locally

- Frontend: Next.js app
- Backend: FastAPI app
- Database: Postgres 16 in Docker
- Messaging bridge: Photon bridge
- Database GUI: Adminer

## One-Time Setup

Install frontend and backend dependencies:

```bash
npm install
python3 -m venv .venv
.venv/bin/pip install -e ./backend
```

Create local environment settings if `.env` does not already exist:

```bash
cp .env.example .env
```

Check that `.env` has these baseline values:

```bash
NEXT_PUBLIC_APP_URL=http://localhost:3000
NEXT_PUBLIC_API_URL=http://localhost:8002
API_URL=http://localhost:8002
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:3001
BACKEND_CORS_ORIGINS=http://localhost:3000,http://localhost:3001
DATABASE_URL=postgresql+asyncpg://opsmesh:opsmesh@localhost:5432/opsmesh
PHOTON_BRIDGE_URL=http://127.0.0.1:8787
PHOTON_BRIDGE_TOKEN=dev-bridge-token
PHOTON_WEBHOOK_SECRET=dev-photon-secret
```

If your shell has `DEBUG=release`, unset it before running backend commands:

```bash
unset DEBUG
```

The backend expects `DEBUG` to be a boolean if it is set.

## Run The App

Use separate terminals for long-running services.

### Terminal 1: Postgres

```bash
docker compose up -d postgres
docker compose ps
```

Postgres should show as healthy.

### Terminal 2: Migrations And Backend

```bash
.venv/bin/alembic -c db/alembic.ini upgrade head
.venv/bin/uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8002
```

Backend URLs:

- API health: http://localhost:8002/api/v1/health
- API docs: http://localhost:8002/docs

### Terminal 3: Frontend

```bash
npm run dev
```

Frontend URLs:

- App: http://localhost:3000
- Login: http://localhost:3000/login
- Register: http://localhost:3000/register
- Settings: http://localhost:3000/settings

### Terminal 4: Photon Bridge

Load `.env` before starting the bridge so Photon credentials and bridge thread
settings are available:

```bash
set -a
source .env
set +a
npm run photon:bridge
```

Bridge health:

```bash
curl http://127.0.0.1:8787/health
```

## If Ports Are Already In Use

If another app is already using `3000` or `8000`, run OpsMesh on alternate
ports. This is the setup used during the latest local smoke test.

Backend on `8010`:

```bash
unset DEBUG
ALLOWED_ORIGINS=http://localhost:3010 \
BACKEND_CORS_ORIGINS=http://localhost:3010 \
API_URL=http://localhost:8010 \
.venv/bin/uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8010
```

Frontend on `3010`:

```bash
unset DEBUG
NEXT_PUBLIC_API_URL=http://localhost:8010 \
API_URL=http://localhost:8010 \
NEXT_PUBLIC_APP_URL=http://localhost:3010 \
npm run dev -- --port 3010
```

Photon bridge pointing to backend port `8010`:

```bash
set -a
source .env
set +a
PHOTON_CALLBACK_URL=http://127.0.0.1:8010/api/v1/messaging/photon/events npm run photon:bridge
```

Alternate-port URLs:

- Frontend: http://localhost:3010
- Backend health: http://localhost:8010/api/v1/health
- Backend docs: http://localhost:8010/docs
- Photon bridge: http://127.0.0.1:8787/health

## Database GUI

Start Adminer:

```bash
docker run --name opsmesh-adminer --rm -p 8081:8080 --network opsmesh-ai_default adminer
```

Open:

```text
http://localhost:8081
```

Login fields:

```text
System: PostgreSQL
Server: opsmesh-postgres
Username: opsmesh
Password: opsmesh
Database: opsmesh
```

If you are using a desktop database client such as DBeaver, pgAdmin, or
TablePlus, use:

```text
Host: localhost
Port: 5432
Database: opsmesh
Username: opsmesh
Password: opsmesh
```

## Smoke Checks

Backend health:

```bash
curl http://127.0.0.1:8000/api/v1/health
```

Photon bridge health:

```bash
curl http://127.0.0.1:8787/health
```

Frontend:

```bash
curl -I http://127.0.0.1:3000
curl -I http://127.0.0.1:3000/login
```

For alternate ports, use `8010` for backend and `3010` for frontend.

## Playwright MCP Browser Testing

The repo includes Playwright MCP as a dev dependency. Chromium is installed with
Playwright so MCP clients can open pages for browser-based testing.

Start the Playwright MCP server:

```bash
npm run mcp:playwright
```

Default MCP endpoint:

```text
http://localhost:8931/mcp
```

Use this MCP client config when needed:

```json
{
  "mcpServers": {
    "playwright": {
      "url": "http://localhost:8931/mcp"
    }
  }
}
```

## Seed Demo Data

After Postgres and the backend are running:

```bash
.venv/bin/python scripts/seed_data.py
```

This seeds dashboard data such as transactions, support tickets, compliance
records, and audit logs.

## Stop Services

Stop Postgres:

```bash
docker compose down
```

Stop long-running frontend, backend, Photon bridge, or Adminer processes with
`Ctrl+C` in the terminal where they are running.

If Adminer was started in the background, stop it with:

```bash
docker stop opsmesh-adminer
```

## Troubleshooting

Check ports:

```bash
ss -ltnp
```

Check Postgres:

```bash
docker compose ps
docker compose logs --tail 80 postgres
```

If migrations fail with a `debug` boolean parsing error, run:

```bash
unset DEBUG
.venv/bin/alembic -c db/alembic.ini upgrade head
```

If Photon bridge health shows `hasDefaultThread: false`, make sure `.env` is
loaded before starting `npm run photon:bridge`.
