# Sprint 4 — Messaging + Photon Bridge (Current-State Aligned)

## Objective

Deliver a Photon-first messaging pipeline for inbound and outbound events with user phone mapping and delivery tracking.

## What is implemented and active

- Messaging endpoints:
  - `POST /api/v1/messaging/send`
  - `POST /api/v1/messaging/webhooks/{channel}`
  - `POST /api/v1/messaging/photon/events`
- Photon-only transport mode (`MESSAGING_TRANSPORT_MODE=photon_sdk`).
- Outbound sends through local Photon bridge (`/send`) with bridge token.
- Inbound event persistence with idempotency in `messaging_events`.
- Sender-to-user routing via `users.preferred_phone_number`.
- Optional inbound auto-reply path via orchestrator.

## Key alignment updates

- Twilio fallback paths are removed from active backend logic.
- iMessage onboarding now depends on project credentials and bridge runtime env.
- Current operational reality includes bridge troubleshooting (`EADDRINUSE`, env loading, allowlist errors).

## High-impact modules

- `backend/app/api/routes/messaging.py`
- `backend/app/services/photon_outbound.py`
- `messaging/photon-bridge/index.mjs`
- `backend/app/models/messaging_event.py`
- `db/migrations/versions/20260422_0003_messaging_events.py`

## Runbook additions

- Start bridge with env loaded:
  - `set -a && source .env && set +a && npm run photon:bridge`
- Health check:
  - `curl -i http://127.0.0.1:8787/health`

## Exit criteria (retroactive)

- Photon bridge path is the canonical messaging transport.
- Inbound/outbound events persist reliably and are user-scoped by phone mapping.
