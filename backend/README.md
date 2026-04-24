# OpsMesh Backend (Sprint 2)

## Run locally

1. Start PostgreSQL from repo root:

```bash
docker compose up -d postgres
```

2. Create a venv and install dependencies (from repo root):

```bash
python3 -m venv .venv
.venv/bin/pip install -e ./backend
```

3. Run migrations (from repo root). **Do not use system `alembic`**—it may import SQLAlchemy 1.x and error on `mapped_column`.

```bash
.venv/bin/alembic -c db/alembic.ini upgrade head
```

4. Start API (from repo root):

```bash
.venv/bin/uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

## Auth smoke test

```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"demo@opsmesh.ai","password":"ChangeMe123!","full_name":"Demo User"}'

TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"demo@opsmesh.ai","password":"ChangeMe123!"}' | python -c "import sys, json; print(json.load(sys.stdin)['access_token'])")

curl http://localhost:8000/api/v1/me -H "Authorization: Bearer $TOKEN"
```

## Sprint 3 conversation + agent smoke test

```bash
THREAD_ID=$(curl -s -X POST http://localhost:8000/api/v1/conversations \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title":"Agent Demo"}' | python3 -c "import sys, json; print(json.load(sys.stdin)['id'])")

curl -X POST "http://localhost:8000/api/v1/conversations/$THREAD_ID/messages" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"content":"echo hello from sprint 3"}'
```

## Sprint 4 messaging smoke test

```bash
# Outbound send
curl -X POST http://localhost:8000/api/v1/messaging/send \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"channel\":\"sms\",\"thread_id\":\"$THREAD_ID\",\"recipient\":\"+15555550123\",\"text\":\"hello from opsmesh\"}"
```

```bash
# Inbound webhook (signature uses PHOTON_WEBHOOK_SECRET / photon_webhook_secret)
BODY='{"event_id":"evt-123","provider_message_id":"pm-123","thread_id":"'"$THREAD_ID"'","sender":"+15550009999","text":"hello inbound"}'
SIG=$(python3 - <<'PY'
import hmac, hashlib, os
body = os.environ["BODY"].encode()
secret = os.environ.get("PHOTON_WEBHOOK_SECRET", "dev-photon-secret").encode()
print(hmac.new(secret, body, hashlib.sha256).hexdigest())
PY
)

curl -X POST http://localhost:8000/api/v1/messaging/webhooks/sms \
  -H "Content-Type: application/json" \
  -H "x-photon-signature: $SIG" \
  -d "$BODY"
```

## Photon SDK bridge mode (Sprint 4 completion gap)

The backend supports two transport modes:

- `MESSAGING_TRANSPORT_MODE=stub` (default, current local adapter behavior)
- `MESSAGING_TRANSPORT_MODE=photon_sdk` (routes outbound + inbound through `spectrum-ts`)

### Start the Photon bridge

From repo root:

```bash
npm run photon:bridge
```

Bridge env (optional defaults shown):

- `PHOTON_BRIDGE_PORT=8787`
- `PHOTON_CALLBACK_URL=http://127.0.0.1:8000/api/v1/messaging/photon/events`
- `PHOTON_BRIDGE_TOKEN=dev-bridge-token`
- `PHOTON_BRIDGE_THREAD_ID=<existing-thread-id>` (required if you want inbound `app.messages` events persisted automatically)
- `PHOTON_PROJECT_ID` + `PHOTON_PROJECT_SECRET` (optional for project-backed providers; terminal provider works without credentials)

### Backend bridge config

Set in `.env`:

```bash
MESSAGING_TRANSPORT_MODE=photon_sdk
PHOTON_BRIDGE_URL=http://127.0.0.1:8787
PHOTON_BRIDGE_TOKEN=dev-bridge-token
```

Restart backend after changing env.
