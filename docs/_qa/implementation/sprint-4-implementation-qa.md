# Sprint 4 Implementation QA (Current-State Alignment)

## Delivered features still active

- Photon bridge-backed outbound sends and inbound event ingestion.
- Signature/token checks and idempotent message event persistence.
- Sender phone mapping to user-owned thread.

## Current operational verification notes

- Bridge must run with env exported (`source .env` before `npm run photon:bridge`).
- Common failures now documented:
  - missing project credentials in bridge process
  - bridge port conflict (`EADDRINUSE`)
  - provider allowlist restriction (`Target not allowed for this project`)

## Verification checklist

- [X] Outbound API calls bridge and stores event rows.
- [X] Inbound path validates signatures/tokens and persists messages.
- [X] Duplicate inbound events are suppressed.
- [X] Bridge health endpoint responds on `127.0.0.1:8787/health`.
