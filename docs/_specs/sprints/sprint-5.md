# Sprint 5 — LLM Upgrade (Current-State Aligned)

## Objective

Improve agent response quality with real LLM generation while preserving existing orchestrator and messaging behavior.

## What is implemented and active

- `agents/llm.py` integrated into `agents/orchestrator.py`.
- Env-driven LLM usage via `OPENAI_API_KEY`, `OPENAI_MODEL`, optional `OPENAI_BASE_URL`.
- Safe fallback remains when provider config is absent/unavailable.
- Messaging pathways still use the same transport and event contracts.

## What is not yet fully delivered

- Full RAG document ingestion/retrieval/citation pipeline is not complete in current code.
- External enterprise connector layer is still planned work.

## High-impact modules

- `agents/llm.py`
- `agents/orchestrator.py`
- `backend/app/api/routes/conversations.py`
- `backend/app/api/routes/messaging.py`

## Runbook

```bash
cd opsmesh-ai
.venv/bin/uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

Set LLM env in `.env`:

```bash
OPENAI_API_KEY=__set_me__
OPENAI_MODEL=__set_me__
```

## Exit criteria (retroactive)

- LLM-backed responses are available and guarded by configuration.
- Existing message routing and auth flows remain stable.
