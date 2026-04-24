# Messaging Module (Sprint 4)

Photon-style abstraction for multi-channel messaging adapters.

## Supported channels

- SMS
- WhatsApp
- iMessage (stubbed interface)
- Snapchat (stubbed interface)

## Environment variables

- `PHOTON_WEBHOOK_SECRET` / backend setting `photon_webhook_secret`
- `FEATURE_MESSAGING_SMS`
- `FEATURE_MESSAGING_WHATSAPP`
- `FEATURE_MESSAGING_IMESSAGE`
- `FEATURE_MESSAGING_SNAPCHAT`
- `ENABLE_INBOUND_AUTO_REPLY`

## Endpoints

- `POST /api/v1/messaging/send` (authenticated)
- `POST /api/v1/messaging/webhooks/{channel}` (signature verified)

## Notes

- Webhooks are idempotent by `(channel, provider_event_id)`.
- Only payload preview is persisted in `messaging_events.payload` to avoid raw PII logs.
- `http_get` tool remains allowlisted and independent from messaging transport.
