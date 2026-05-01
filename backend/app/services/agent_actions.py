from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.agent_action import AgentAction
from backend.app.models.audit_log import AuditLog
from backend.app.models.compliance_record import ComplianceRecord
from backend.app.models.support_ticket import SupportTicket
from backend.app.models.transaction import Transaction


class AgentActionService:
    async def generate_recommendations(self, db: AsyncSession) -> list[AgentAction]:
        created: list[AgentAction] = []
        created.extend(await self._recommend_transaction_reviews(db))
        created.extend(await self._recommend_support_escalations(db))
        created.extend(await self._recommend_compliance_reviews(db))
        return created

    async def approve(self, db: AsyncSession, action: AgentAction) -> AgentAction:
        if action.status != "pending":
            return action

        if action.action_type == "support_escalation" and action.entity_id:
            ticket = await db.get(SupportTicket, action.entity_id)
            if ticket:
                ticket.priority = "high"
                ticket.status = "in_review"
        elif action.action_type == "compliance_approval" and action.entity_id:
            record = await db.get(ComplianceRecord, action.entity_id)
            if record:
                record.status = "approved"
        elif action.action_type == "transaction_review" and action.entity_id:
            tx = await db.get(Transaction, action.entity_id)
            if tx:
                tx.flagged = True

        action.status = "approved"
        action.resolved_at = datetime.now(timezone.utc)
        await self._audit(
            db,
            "agent_action_approved",
            action.domain,
            f"Approved agent action: {action.title}",
            action.rationale,
            action.id,
        )
        await db.flush()
        return action

    async def reject(self, db: AsyncSession, action: AgentAction, reason: str | None = None) -> AgentAction:
        if action.status != "pending":
            return action
        action.status = "rejected"
        action.resolved_at = datetime.now(timezone.utc)
        await self._audit(
            db,
            "agent_action_rejected",
            action.domain,
            f"Rejected agent action: {action.title}",
            reason or action.rationale,
            action.id,
        )
        await db.flush()
        return action

    async def _recommend_transaction_reviews(self, db: AsyncSession) -> list[AgentAction]:
        rows = (
            await db.execute(
                select(Transaction)
                .where(Transaction.flagged.is_(True))
                .order_by(desc(Transaction.risk_score), desc(Transaction.created_at))
                .limit(3)
            )
        ).scalars().all()
        actions: list[AgentAction] = []
        for tx in rows:
            action = await self._create_once(
                db,
                domain="transactions",
                action_type="transaction_review",
                entity_type="transaction",
                entity_id=tx.id,
                title=f"Review {tx.merchant} risk flag",
                description=f"${tx.amount:.2f} at {tx.merchant} has risk score {tx.risk_score}/100.",
                priority="high" if tx.risk_score >= 71 else "medium",
                confidence=min(0.98, max(0.55, tx.risk_score / 100)),
                rationale="Flagged transaction should be reviewed before closing the risk alert.",
                payload={"risk_score": tx.risk_score, "amount": tx.amount, "merchant": tx.merchant},
            )
            if action:
                actions.append(action)
        return actions

    async def _recommend_support_escalations(self, db: AsyncSession) -> list[AgentAction]:
        rows = (
            await db.execute(
                select(SupportTicket)
                .where(SupportTicket.status == "open", SupportTicket.priority == "high")
                .order_by(desc(SupportTicket.created_at))
                .limit(3)
            )
        ).scalars().all()
        actions: list[AgentAction] = []
        for ticket in rows:
            action = await self._create_once(
                db,
                domain="support",
                action_type="support_escalation",
                entity_type="support_ticket",
                entity_id=ticket.id,
                title=f"Escalate {ticket.category.replace('_', ' ')} ticket",
                description=ticket.description[:240],
                priority="high",
                confidence=0.82,
                rationale="High-priority open ticket should move into review.",
                payload={"status": ticket.status, "priority": ticket.priority, "category": ticket.category},
            )
            if action:
                actions.append(action)
        return actions

    async def _recommend_compliance_reviews(self, db: AsyncSession) -> list[AgentAction]:
        rows = (
            await db.execute(
                select(ComplianceRecord)
                .where(ComplianceRecord.status == "pending", ComplianceRecord.policy_flag.is_(True))
                .order_by(desc(ComplianceRecord.created_at))
                .limit(3)
            )
        ).scalars().all()
        actions: list[AgentAction] = []
        for record in rows:
            action = await self._create_once(
                db,
                domain="compliance",
                action_type="compliance_approval",
                entity_type="compliance_record",
                entity_id=record.id,
                title=f"Review {record.record_type.replace('_', ' ')} compliance item",
                description=record.description[:240],
                priority="high" if record.severity == "high" else "medium",
                confidence=0.78,
                rationale=record.recommendation or "Policy-flagged compliance record needs a decision.",
                payload={
                    "status": record.status,
                    "severity": record.severity,
                    "policy_flag": record.policy_flag,
                    "recommendation": record.recommendation,
                },
            )
            if action:
                actions.append(action)
        return actions

    async def _create_once(
        self,
        db: AsyncSession,
        *,
        domain: str,
        action_type: str,
        entity_type: str,
        entity_id: str | None,
        title: str,
        description: str,
        priority: str,
        confidence: float,
        rationale: str,
        payload: dict,
    ) -> AgentAction | None:
        existing = await db.scalar(
            select(AgentAction).where(
                AgentAction.status == "pending",
                AgentAction.action_type == action_type,
                AgentAction.entity_type == entity_type,
                AgentAction.entity_id == entity_id,
            )
        )
        if existing:
            return None

        action = AgentAction(
            id=str(uuid4()),
            title=title,
            description=description,
            domain=domain,
            action_type=action_type,
            entity_type=entity_type,
            entity_id=entity_id,
            priority=priority,
            confidence=confidence,
            rationale=rationale,
            payload=payload,
            source="agent",
        )
        db.add(action)
        await self._audit(
            db,
            "agent_action_created",
            domain,
            f"Created agent action: {title}",
            rationale,
            action.id,
        )
        await db.flush()
        return action

    async def _audit(
        self,
        db: AsyncSession,
        event_type: str,
        domain: str,
        action_taken: str,
        reasoning: str | None,
        entity_id: str,
    ) -> None:
        db.add(
            AuditLog(
                id=str(uuid4()),
                event_type=event_type,
                domain=domain,
                action_taken=action_taken,
                reasoning=reasoning,
                source="agent",
                related_entity_id=entity_id,
            )
        )
