# OpsMesh AI — System Specification

**Version:** 0.1 (foundation)  
**Status:** Draft — drives implementation sprints

---

## 1. Purpose and scope

OpsMesh AI is a **production-oriented operations platform** that lets teams interact with enterprise systems through **natural language**, backed by **retrieval-augmented generation (RAG)**, **multi-agent workflows**, and **messaging-first** delivery (SMS, WhatsApp, iMessage, Snapchat adapters). It provides **dashboards and analytics**, **evaluations**, **guardrails**, and **observability** suitable for regulated and high-trust environments.

**In scope (target end state):** web app shell and dashboards, authenticated API, agent orchestration with tool execution, connectors and RAG pipeline, messaging ingress/egress via a Photon-centric integration layer, eval suite, structured logging/tracing/metrics.

**Out of scope for initial sprints:** full legal/compliance certification; carrier-specific certifications are tracked as constraints per sprint.

---

## 2. Architecture overview

High-level topology:

```text
Channels (SMS / WA / iMessage / Snap)
        │
        ▼
  messaging/  ←── Photon + channel adapters + webhooks
        │
        ▼
  backend/ (FastAPI)  ←── auth, sessions, REST/WebSocket
        │
        ├── agents/  (orchestrator, router, specialists)
        ├── integrations/  (CRM, ticketing, data APIs)
        ├── RAG (vector store + ingestion in backend + db)
        │
        ▼
  db/ (PostgreSQL) + object/file store (as needed)
        │
        ▼
  app/ (Next.js) — dashboards, admin, conversation views
        │
        ▼
  observability/ + evals/ — traces, metrics, eval runs
```

**Principles:** clear boundaries between transport (messaging), API surface (backend), cognition (agents), and persistence (db). All channel-specific quirks stay behind `messaging/` adapters. Business rules and safety checks are explicit (guardrail agent + policy layer).

---

## 3. System components

| Component | Responsibility |
|-----------|----------------|
| **Next.js app (`app/`)** | UI shell, design system, dashboards, real-time or polling views for conversations and ops metrics. |
| **FastAPI backend (`backend/`)** | HTTP API, WebSocket if needed, auth, tenancy hooks, orchestration entrypoints, webhook verification. |
| **Agents (`agents/`)** | Orchestrator, router, retrieval, workflow, guardrail, evaluation agents; tool registry and execution. |
| **Integrations (`integrations/`)** | Typed clients for third-party APIs; OAuth/token refresh patterns; rate limiting. |
| **Messaging (`messaging/`)** | Photon integration, per-channel parsers/formatters, delivery receipts, idempotency keys. |
| **Evals (`evals/`)** | Datasets, scorers, regression suites, CI-friendly runners. |
| **Observability (`observability/`)** | Shared logging config, OTel helpers, metric names, dashboard definitions (or export). |
| **Database (`db/`)** | SQLAlchemy/Alembic or equivalent migrations; canonical schema for users, threads, messages, documents, runs. |

---

## 4. Agent system design

**Orchestrator** owns the lifecycle of a single “turn”: intake → route → delegate → merge → respond. It enforces timeouts, cancellation, and policy invocation.

**Router agent** classifies user intent (question vs action vs escalation), selects candidate specialists, and produces a structured routing decision (JSON schema).

**Retrieval agent** plans searches (metadata filters, rewrites), calls the RAG layer, and returns cited chunks with scores. It does not invent facts beyond retrieved context.

**Workflow agent** executes multi-step procedures using **tools** (HTTP actions, internal APIs, human-in-the-loop placeholders). Outputs are structured for audit.

**Guardrail agent** (and synchronous policy middleware) checks inputs/outputs for PII leakage, prompt injection patterns, disallowed topics, and tool-call safety. Can short-circuit or rewrite with audit trail.

**Evaluation agent** (offline/batch) scores traces against rubrics; online it may only trigger sampling to avoid latency spikes.

**Tool execution system:** registered tools with JSON schemas, capability scopes per role, idempotency for side effects, and redacted logging.

---

## 5. Data flow

1. **Inbound message** hits `messaging/` → normalized **canonical message** (thread id, channel, sender, body, attachments metadata).
2. Backend persists message, loads thread context and tenant policy.
3. Orchestrator invokes router → optional retrieval → workflow/guardrail path.
4. **Outbound** response serialized per channel in `messaging/`; delivery status recorded.
5. **Async jobs** (ingestion, re-embedding, eval runs) via queue or worker process (sprint-dependent; schema reserves job tables).

**RAG path:** documents ingested → chunked → embedded → stored in vector index with foreign keys to source metadata in PostgreSQL. Query path: embed query → hybrid search (keyword + vector where applicable) → rerank (optional) → context assembly with citations.

---

## 6. Messaging flow

- **Photon** is the primary abstraction for send/receive; channel adapters implement a shared interface: `send`, `parse_inbound`, `verify_webhook`, `normalize_attachments`.
- **Webhooks** verified with provider secrets; replay protection via nonce or event id storage.
- **Idempotency:** channel provider message ids stored uniquely to avoid duplicate processing.
- **Human escalation:** workflow agent can hand off to a defined “operator” queue (future sprint); API contract stubbed early.

---

## 7. Eval system

- **Unit-level:** tool-call JSON schema validation, router output schema tests.
- **Dataset evals:** golden Q&A, RAG grounding checks (citation required), safety suites.
- **Regression:** store traces (redacted) + expected outcomes; CI runs subset on each PR; nightly full suite.
- **Metrics:** task success rate, groundedness, latency p95, guardrail trigger rate.

---

## 8. Observability system

- **Structured logging** with request id, thread id, tenant id, agent step (no raw secrets).
- **OpenTelemetry** traces spanning API → agents → tool calls → DB (sampling in prod).
- **Metrics:** HTTP latency, agent step durations, retrieval hit rate, message send failures.
- **Dashboards:** app surfaces for ops; optional export to Grafana-style stacks documented in sprint 6.

---

## 9. Security and compliance (design targets)

- Auth: short-lived JWT or session cookies + refresh strategy; RBAC for admin vs operator vs read-only.
- Secrets only via environment or secret manager; never in repo.
- Data minimization in logs; PII tagging for redaction pipeline.

---

## 10. Non-goals and risks

- **Non-goal:** implementing full carrier onboarding in sprint 1; use mocks/sandboxes first.
- **Risk:** channel API drift → mitigate with adapter version pins and contract tests.
- **Risk:** agent over-permissioning → least-privilege tool tokens and explicit approval flows for destructive tools.

---

## 11. References

Sprint breakdown: `docs/_specs/sprints/sprint-*.md`.  
QA checklists: `docs/_qa/`.
