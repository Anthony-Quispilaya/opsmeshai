from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.audit_log import AuditLog
from backend.app.models.automation_rule import AutomationRule
from backend.app.services.agent_actions import AgentActionService


DEFAULT_RULES = (
    {
        "name": "High-risk transaction review",
        "description": "Create approval actions for flagged or high-risk transactions.",
        "domain": "transactions",
        "trigger_type": "manual_scan",
        "conditions": {"risk_score_gte": 80, "flagged": True},
        "action_type": "create_agent_action",
        "action_payload": {"recommendation": "transaction_review"},
    },
    {
        "name": "Urgent support escalation",
        "description": "Create approval actions for high-priority open support tickets.",
        "domain": "support",
        "trigger_type": "manual_scan",
        "conditions": {"status": "open", "priority": "high"},
        "action_type": "create_agent_action",
        "action_payload": {"recommendation": "support_escalation"},
    },
    {
        "name": "Policy-flagged compliance review",
        "description": "Create approval actions for pending policy-flagged compliance records.",
        "domain": "compliance",
        "trigger_type": "manual_scan",
        "conditions": {"status": "pending", "policy_flag": True},
        "action_type": "create_agent_action",
        "action_payload": {"recommendation": "compliance_approval"},
    },
)


class AutomationRuleService:
    def __init__(self) -> None:
        self.agent_actions = AgentActionService()

    async def seed_defaults(self, db: AsyncSession) -> list[AutomationRule]:
        rules: list[AutomationRule] = []
        for spec in DEFAULT_RULES:
            existing = await db.scalar(select(AutomationRule).where(AutomationRule.name == spec["name"]))
            if existing:
                rules.append(existing)
                continue
            rule = AutomationRule(id=str(uuid4()), **spec)
            db.add(rule)
            rules.append(rule)
        await db.flush()
        return rules

    async def run_enabled(self, db: AsyncSession) -> dict:
        rules = list(
            (
                await db.execute(
                    select(AutomationRule)
                    .where(AutomationRule.enabled.is_(True))
                    .order_by(AutomationRule.created_at)
                )
            )
            .scalars()
            .all()
        )
        if not rules:
            rules = await self.seed_defaults(db)

        created = await self.agent_actions.generate_recommendations(db)
        now = datetime.now(timezone.utc)
        for rule in rules:
            rule.last_run_at = now

        db.add(
            AuditLog(
                id=str(uuid4()),
                event_type="automation_rules_run",
                domain="automation",
                action_taken=f"Ran {len(rules)} automation rules; created {len(created)} approval actions.",
                reasoning="Manual rules engine run",
                source="automation",
                related_entity_id=None,
            )
        )
        await db.flush()
        return {
            "rules_run": len(rules),
            "actions_created": len(created),
            "message": f"Ran {len(rules)} rules and created {len(created)} approval actions.",
        }
