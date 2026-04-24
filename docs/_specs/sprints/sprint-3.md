# Sprint 3 — Agent Orchestration (Current-State Aligned)

## Objective

Establish the orchestrator/run-trace foundation now used by both conversation API and inbound auto-reply flows.

## What is implemented and active

- `agents/orchestrator.py` executes intent routing and response generation.
- `agent_runs` persistence tracks status, traces, and failures.
- `POST /api/v1/conversations/{conversation_id}/messages` runs agent turns for authenticated users.
- Tool/guardrail behavior remains deterministic-first.

## Alignment updates since original sprint notes

- Frontend `Agent Playground` is no longer part of active UX.
- The backend conversation route still exists and is functional.
- Current frontend emphasizes auth + phone onboarding, while orchestration runs mostly through backend pathways.

## Key modules

- `agents/orchestrator.py`
- `agents/llm.py`
- `backend/app/api/routes/conversations.py`
- `backend/app/models/agent_run.py`
- `db/migrations/versions/20260422_0002_agent_runs.py`

## Runbook

```bash
cd opsmesh-ai
.venv/bin/alembic -c db/alembic.ini upgrade head
.venv/bin/uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

## Exit criteria (retroactive)

- Agent run traces remain persisted and auditable.
- Orchestrator is reusable by both direct conversation API and messaging auto-reply.
