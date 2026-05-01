# Sprint 8 — Automation + Human Approval Workflows

## Goal

Turn OpsMesh from a passive dashboard into an operations workflow system with
AI-recommended actions, human approval, automation rules, briefings, incidents,
trace visibility, and eval coverage.

This sprint is implemented step by step. Each feature must be checked for
existing coverage before work starts, tested after implementation, and only then
used as a foundation for the next feature.

## Feature 1 — Agent Action Inbox

### Status

Implemented first.

### Existing Coverage Check

Before implementation there were references to approval workflows in docs, but
no runtime implementation:

- No `agent_actions` model or table.
- No action inbox API routes.
- No dashboard approval queue.
- No approve/reject workflow over AI recommendations.

### Implementation

Added:

- `agent_actions` table via `20260501_0007_agent_actions.py`.
- `AgentAction` SQLAlchemy model.
- `AgentActionService` recommendation and resolution logic.
- Protected API routes:
  - `GET /api/v1/ops/agent-actions`
  - `POST /api/v1/ops/agent-actions/generate`
  - `POST /api/v1/ops/agent-actions/{id}/approve`
  - `POST /api/v1/ops/agent-actions/{id}/reject`
- Dashboard `Agent Action Inbox` card with generate/approve/reject controls.
- Audit logs for action creation, approval, and rejection.

### Recommendation Types

- `transaction_review`: review flagged/high-risk transaction.
- `support_escalation`: move high-priority open ticket into review.
- `compliance_approval`: approve a pending policy-flagged compliance record.

### Product Behavior

The dashboard can scan current operational data and propose actions. A human can
approve or reject them. Approvals update the underlying record when appropriate
and always create an audit trail.

### Validation

- Python agent tests pass.
- Backend files compile.
- Migration added for persistent action inbox.
- Dashboard verified in browser with the Action Inbox visible on the main page.

## Feature 2 — SMS Approval Commands

### Status

Implemented after Feature 1 validation.

### Existing Coverage Check

Before implementation, SMS could create/query/update core records, but it could
not operate the human approval queue:

- No SMS command for listing pending AI recommendations.
- No SMS command for generating recommendation batches.
- No SMS command for approving or rejecting an agent action.

### Implementation

Added an agent-action command layer at the start of `OpsProcessor.process`.
Messages that explicitly mention approvals, recommendations, pending actions, or
agent actions can now:

- Generate recommended actions: `generate agent actions`
- List pending approvals: `show pending agent actions`
- Approve the latest pending action: `approve latest agent action`
- Reject the latest pending action: `reject latest agent action`

The handler is intentionally narrow so normal conversational messages continue
to fall through to the LLM instead of feeling hardcoded.

### Product Behavior

The user can now review the AI approval queue from iMessage/SMS without opening
the dashboard. Approving/rejecting uses the same `AgentActionService` as the
dashboard, so database updates and audit logs stay consistent.

### Validation

- Backend file compiles.
- Python agent tests pass.
- TypeScript passes.
- Live smoke test:
  - `GET /ops/agent-actions` returned pending actions.
  - `show pending agent actions` returned a concise SMS list.
  - `reject latest agent action` resolved the latest pending action.

## Upcoming Features

## Feature 3 — Automation Rules Engine

### Status

Implemented after Feature 2 validation.

### Existing Coverage Check

Before implementation there were sprint references to automation rules, but no
runtime implementation:

- No `automation_rules` table.
- No rule model or service layer.
- No API for creating or running rules.
- No dashboard controls for rule-based scans.

### Implementation

Added:

- `automation_rules` table via `20260501_0008_automation_rules.py`.
- `AutomationRule` SQLAlchemy model.
- `AutomationRuleService` with default rule seeding and enabled-rule execution.
- Protected API routes:
  - `GET /api/v1/ops/automation-rules`
  - `POST /api/v1/ops/automation-rules/seed`
  - `POST /api/v1/ops/automation-rules/run`
- Dashboard `Automation Rules` card with default creation and run controls.

### Default Rules

- `High-risk transaction review`
- `Urgent support escalation`
- `Policy-flagged compliance review`

### Product Behavior

Rules currently run as approval-generating scans. They create `AgentAction`
records instead of silently changing operational records, keeping automation
professional and auditable while the product matures.

### Validation

- Backend files compile.
- Python agent tests pass.
- TypeScript passes.
- Migration applied cleanly.
- Live API smoke test seeded 3 rules and ran them successfully.
- Browser verification confirmed the Automation Rules card renders seeded rules.

## Feature 4 — Daily AI Briefing

### Status

Implemented after Feature 3 validation.

### Existing Coverage Check

Before implementation, the dashboard had a short insights summary, but no
dedicated briefing surface:

- No daily briefing API response shape.
- No highlights/next-actions briefing endpoint.
- No dashboard briefing card.

### Implementation

Added:

- `DailyBriefingResponse` schema.
- `GET /api/v1/ops/daily-briefing`.
- Dashboard `Daily Briefing` card with:
  - concise summary,
  - generated timestamp,
  - operational signals,
  - recommended next actions.

### Product Behavior

The briefing gives the operator an executive-style morning snapshot of flagged
transactions, support load, compliance backlog, and the most important pending
approval actions. If the LLM is available, it writes the one-sentence summary;
otherwise the endpoint still returns a useful deterministic briefing.

### Validation

- Backend files compile.
- Python agent tests pass.
- TypeScript passes.
- Live API smoke test returned a briefing with 3 signals and 3 next actions.
- Browser verification confirmed the Daily Briefing card renders on the dashboard.

Feature 5: Incident/triage mode.

Feature 6: Agent trace viewer.

Feature 7: Evaluation suite.

Feature 8: Better phone UX suggestions.

Feature 9: Demo mode.
