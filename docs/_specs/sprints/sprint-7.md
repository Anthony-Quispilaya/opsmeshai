# Sprint 7 — Messaging Agent Intelligence + Workflow Copilot

## Goal

Move the phone agent from a dashboard-summary bot toward a messaging-first
operations copilot aligned with `docs/opsmesh_job_alignment_brief.md`.

The agent must be able to:

- Speak naturally when the user is only checking presence or chatting.
- Answer grounded operational questions when the user asks about known data.
- Create or update backend records when the user gives a workflow command.
- Support multiple operations domains, not only transactions.
- Preserve auditability when records are changed.

## Product Rule

The phone agent should not treat every question as a dashboard query.

Examples:

- `hey are you active?` should receive a conversational status reply.
- `what can you do?` should explain supported workflows.
- `show high-risk transactions` should query transaction data.
- `create a support ticket for a login issue` should create a support record.
- `add a compliance note for missing receipt` should create a compliance record.

## Current Implementation Added

### Conversational Bypass

`OpsProcessor` should not answer normal conversation. It is responsible for
clear operational work only: create/update/delete/list/analyze records.

Conversational and meta-usage messages now bypass `OpsProcessor` and fall
through to the general orchestrator/LLM path.

Covered chat topics:

- status / availability checks
- greetings
- help / capabilities questions

Capability questions include common variants like:

- `what can you do?`
- `what do you do?`
- `how can you help?`
- `help`

Meta-questions about how to use the agent also stay conversational even if they
mention a data domain:

- `what can I ask about transactions?`
- `what questions can I ask about support tickets?`
- `why did you give me data?`

This prevents messages like `hey are you active?` from falling into
`QUERY_DATA` and producing an irrelevant dashboard overview while also avoiding
hardcoded command-menu replies.

Important design correction: normal chat must be handled by the LLM/orchestrator,
not by scripted strings in the ops processor. Deterministic logic should guard
record mutations and data retrieval, not personality.

If the LLM provider is unavailable, the system should not pretend to be smart
with repeated canned text. The run should be marked failed for observability
until the model connection/API key is fixed.

### Stricter Query Boundary

The fallback classifier now only treats question-mark messages as `QUERY_DATA`
when the text includes an operations-domain term such as:

- transactions, spending, merchant, amount, flagged, risk
- support, ticket, issue, customer, refund, login
- compliance, policy, audit, approval, pending

This gives the AI agent room to behave like a normal assistant when the user is
not asking for operational data.

### Multi-Domain Workflow Coverage

The processor continues to route commands across:

- Transactions
- Support tickets
- Compliance records
- Analysis / triage summaries

Sprint 7 explicitly documents that support and compliance workflows are first-
class phone-agent domains, not side features.

## Engineering Rules For This Area

Follow these rules before changing the phone agent:

1. Decide whether the message is chat, query, analysis, or mutation before
   touching the database.
2. Do not answer with dashboard summaries unless the user asks for operational
   status, counts, lists, risks, queues, or analysis.
3. Mutations must use explicit tool-like paths such as add/update/delete/flag,
   not freeform LLM text.
4. If a mutation target is ambiguous, ask the user to clarify rather than
   guessing.
5. Replies sent over SMS/iMessage should be short, direct, and useful.
6. Support tickets and compliance records must be treated as core workflows,
   equal to transactions.
7. Every backend mutation should produce an audit log entry.
8. Tests should include the exact SMS phrases that caused bugs or confusion.

## Tests Added

`agents/tests/test_ops_processor.py` covers:

- `hey are you active?` skips `OpsProcessor`.
- `I said what do you do?` skips `OpsProcessor`.
- `what can I ask about transactions?` skips `OpsProcessor`, not `QUERY_DATA`.
- `why did you give me data?` skips `OpsProcessor`, not transaction explanation.
- Support-ticket creation routes correctly.
- Compliance-record creation routes correctly.
- Domain questions still route to `QUERY_DATA`.

`agents/tests/test_orchestrator.py` covers:

- Conversational turns raise an `llm_not_configured`/`llm_unavailable` style
  error instead of returning fake hardcoded chat.

## Next Work

- Add structured confidence and rationale to parsed intents.
- Add a lightweight confirmation flow for destructive actions.
- Add eval cases for common SMS phrases and expected routing outcomes.
- Add dashboard visibility into agent intent, action, and audit trace.
- Expand domain-specific parsers for incidents, approvals, escalations, and
  customer handoff workflows.
