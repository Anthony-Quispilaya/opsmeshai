import asyncio
import random
from collections import Counter
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from agents.llm import LLMResponder
from backend.app.api.deps import get_current_user
from backend.app.db.session import get_db
from backend.app.models.agent_action import AgentAction
from backend.app.models.audit_log import AuditLog
from backend.app.models.automation_rule import AutomationRule
from backend.app.models.compliance_record import ComplianceRecord
from backend.app.models.support_ticket import SupportTicket
from backend.app.models.transaction import Transaction
from backend.app.models.user import User
from backend.app.schemas.ops import (
    AgentActionResponse,
    AuditLogResponse,
    AutomationRunResponse,
    AutomationRuleResponse,
    ComplianceRecordCreateRequest,
    DailyBriefingResponse,
    ComplianceRecordUpdateRequest,
    ComplianceRecordResponse,
    InsightsResponse,
    RejectAgentActionRequest,
    SupportTicketCreateRequest,
    SupportTicketUpdateRequest,
    SupportTicketResponse,
    TransactionCreateRequest,
    TransactionUpdateRequest,
    TransactionResponse,
)
from backend.app.services.agent_actions import AgentActionService
from backend.app.services.automation_rules import AutomationRuleService
from backend.app.services.onboarding import ensure_phone_thread
from backend.app.services.photon_outbound import send_photon_bridge_message
from backend.app.core.config import get_settings

_FRAUD_SCENARIOS = [
    {"merchant": "Dark Web Exchange",    "item_name": "Crypto Transfer",        "amount": 8500.00, "category": "crypto",    "location": "Unknown VPN",      "risk_score": 97, "notes": "IP flagged by threat intelligence feed"},
    {"merchant": "Unnamed Wire Service", "item_name": "International Wire",     "amount": 4750.00, "category": "transfers", "location": "Eastern Europe",    "risk_score": 91, "notes": "Recipient account opened 3 days ago"},
    {"merchant": "Shadow Crypto Desk",   "item_name": "BTC Purchase",           "amount": 6200.00, "category": "crypto",    "location": "Anonymous Relay",   "risk_score": 95, "notes": "No KYC on file for counterparty"},
    {"merchant": "Offshore Holdings LLC","item_name": "Wire Transfer",          "amount": 9900.00, "category": "transfers", "location": "Cayman Islands",    "risk_score": 98, "notes": "Just under $10k reporting threshold"},
    {"merchant": "Cash King ATM",        "item_name": "Cash Advance",           "amount": 2000.00, "category": "cash",      "location": "Las Vegas Strip",   "risk_score": 85, "notes": "3rd large withdrawal in 2 hours"},
    {"merchant": "Anonymous Marketplace","item_name": "Unverified Purchase",    "amount": 3300.00, "category": "crypto",    "location": "Unknown",           "risk_score": 88, "notes": "No merchant verification on file"},
    {"merchant": "Rapid FX Bureau",      "item_name": "Currency Exchange",      "amount": 5100.00, "category": "transfers", "location": "Miami, FL",         "risk_score": 86, "notes": "Destination currency: Monero (XMR)"},
    {"merchant": "Ghost Card Terminal",  "item_name": "POS Transaction",        "amount": 1800.00, "category": "cash",      "location": "Unknown Terminal",  "risk_score": 83, "notes": "Card-not-present, no CVV match"},
]

router = APIRouter(prefix="/ops", tags=["ops"])
_llm = LLMResponder()
_actions = AgentActionService()
_automation = AutomationRuleService()


def _risk_from_transaction(amount: float, category: str, flagged: bool) -> int:
    risk = 15
    if amount >= 2000:
        risk += 55
    elif amount >= 500:
        risk += 30
    elif amount >= 150:
        risk += 12
    if category.lower() in {"travel", "electronics", "luxury", "cash", "crypto"}:
        risk += 15
    if flagged:
        risk = max(risk, 65)
    return min(100, risk)


def _clean(value: str | None, fallback: str) -> str:
    value = (value or "").strip()
    return value or fallback


async def _audit(
    db: AsyncSession,
    event_type: str,
    domain: str,
    action_taken: str,
    entity_id: str | None,
) -> None:
    db.add(
        AuditLog(
            id=str(uuid4()),
            event_type=event_type,
            domain=domain,
            action_taken=action_taken,
            reasoning="Manual dashboard action",
            source="dashboard",
            related_entity_id=entity_id,
        )
    )
    await db.flush()


@router.get("/transactions", response_model=list[TransactionResponse])
async def list_transactions(
    limit: int = Query(default=50, le=200),
    flagged_only: bool = Query(default=False),
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> list[TransactionResponse]:
    q = select(Transaction).order_by(desc(Transaction.created_at)).limit(limit)
    if flagged_only:
        q = q.where(Transaction.flagged.is_(True))
    result = await db.execute(q)
    return result.scalars().all()  # type: ignore[return-value]


@router.post("/transactions", response_model=TransactionResponse)
async def create_transaction(
    payload: TransactionCreateRequest,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> TransactionResponse:
    category = _clean(payload.category, "retail")
    risk_score = payload.risk_score
    if risk_score is None:
        risk_score = _risk_from_transaction(payload.amount, category, payload.flagged)
    tx = Transaction(
        id=str(uuid4()),
        amount=payload.amount,
        merchant=_clean(payload.merchant, "Unknown"),
        item_name=_clean(payload.item_name, "") or None,
        location=_clean(payload.location, "Unknown"),
        category=category,
        risk_score=risk_score,
        flagged=payload.flagged or risk_score >= 71,
        notes=payload.notes,
        source="dashboard",
    )
    db.add(tx)
    await _audit(
        db,
        "transaction_added",
        "transactions",
        f"Added dashboard transaction: ${tx.amount:.2f} at {tx.merchant}",
        tx.id,
    )
    await db.commit()
    await db.refresh(tx)
    return tx  # type: ignore[return-value]


@router.patch("/transactions/{transaction_id}", response_model=TransactionResponse)
async def update_transaction(
    transaction_id: str,
    payload: TransactionUpdateRequest,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> TransactionResponse:
    tx = await db.get(Transaction, transaction_id)
    if tx is None:
        raise HTTPException(status_code=404, detail="Transaction not found")
    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        if isinstance(value, str):
            value = value.strip()
        setattr(tx, field, value)
    await _audit(
        db,
        "transaction_updated",
        "transactions",
        f"Updated dashboard transaction: ${tx.amount:.2f} at {tx.merchant}",
        tx.id,
    )
    await db.commit()
    await db.refresh(tx)
    return tx  # type: ignore[return-value]


@router.delete("/transactions/{transaction_id}", status_code=204)
async def delete_transaction(
    transaction_id: str,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> None:
    tx = await db.get(Transaction, transaction_id)
    if tx is None:
        raise HTTPException(status_code=404, detail="Transaction not found")
    description = f"${tx.amount:.2f} at {tx.merchant}"
    await db.delete(tx)
    await _audit(db, "transaction_deleted", "transactions", f"Deleted dashboard transaction: {description}", None)
    await db.commit()


@router.get("/support-tickets", response_model=list[SupportTicketResponse])
async def list_support_tickets(
    limit: int = Query(default=50, le=200),
    status: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> list[SupportTicketResponse]:
    q = select(SupportTicket).order_by(desc(SupportTicket.created_at)).limit(limit)
    if status:
        q = q.where(SupportTicket.status == status)
    result = await db.execute(q)
    return result.scalars().all()  # type: ignore[return-value]


@router.post("/support-tickets", response_model=SupportTicketResponse)
async def create_support_ticket(
    payload: SupportTicketCreateRequest,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> SupportTicketResponse:
    ticket = SupportTicket(
        id=str(uuid4()),
        customer_identifier=payload.customer_identifier,
        description=payload.description.strip(),
        category=_clean(payload.category, "general"),
        status=payload.status,
        priority=payload.priority,
        source="dashboard",
    )
    db.add(ticket)
    await _audit(
        db,
        "support_ticket_created",
        "support",
        f"Created dashboard support ticket: {ticket.category}",
        ticket.id,
    )
    await db.commit()
    await db.refresh(ticket)
    return ticket  # type: ignore[return-value]


@router.patch("/support-tickets/{ticket_id}", response_model=SupportTicketResponse)
async def update_support_ticket(
    ticket_id: str,
    payload: SupportTicketUpdateRequest,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> SupportTicketResponse:
    ticket = await db.get(SupportTicket, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="Support ticket not found")
    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        if isinstance(value, str):
            value = value.strip()
        setattr(ticket, field, value)
    await _audit(
        db,
        "support_ticket_updated",
        "support",
        f"Updated dashboard support ticket: {ticket.category}",
        ticket.id,
    )
    await db.commit()
    await db.refresh(ticket)
    return ticket  # type: ignore[return-value]


@router.delete("/support-tickets/{ticket_id}", status_code=204)
async def delete_support_ticket(
    ticket_id: str,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> None:
    ticket = await db.get(SupportTicket, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="Support ticket not found")
    category = ticket.category
    await db.delete(ticket)
    await _audit(db, "support_ticket_deleted", "support", f"Deleted dashboard support ticket: {category}", None)
    await db.commit()


@router.get("/compliance", response_model=list[ComplianceRecordResponse])
async def list_compliance(
    limit: int = Query(default=50, le=200),
    status: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> list[ComplianceRecordResponse]:
    q = select(ComplianceRecord).order_by(desc(ComplianceRecord.created_at)).limit(limit)
    if status:
        q = q.where(ComplianceRecord.status == status)
    result = await db.execute(q)
    return result.scalars().all()  # type: ignore[return-value]


@router.post("/compliance", response_model=ComplianceRecordResponse)
async def create_compliance_record(
    payload: ComplianceRecordCreateRequest,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> ComplianceRecordResponse:
    record = ComplianceRecord(
        id=str(uuid4()),
        record_type=_clean(payload.record_type, "general"),
        description=payload.description.strip(),
        status=payload.status,
        policy_flag=payload.policy_flag,
        severity=payload.severity,
        recommendation=payload.recommendation,
        source="dashboard",
    )
    db.add(record)
    await _audit(
        db,
        "compliance_record_added",
        "compliance",
        f"Added dashboard compliance record: {record.record_type}",
        record.id,
    )
    await db.commit()
    await db.refresh(record)
    return record  # type: ignore[return-value]


@router.patch("/compliance/{record_id}", response_model=ComplianceRecordResponse)
async def update_compliance_record(
    record_id: str,
    payload: ComplianceRecordUpdateRequest,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> ComplianceRecordResponse:
    record = await db.get(ComplianceRecord, record_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Compliance record not found")
    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        if isinstance(value, str):
            value = value.strip()
        setattr(record, field, value)
    await _audit(
        db,
        "compliance_record_updated",
        "compliance",
        f"Updated dashboard compliance record: {record.record_type}",
        record.id,
    )
    await db.commit()
    await db.refresh(record)
    return record  # type: ignore[return-value]


@router.delete("/compliance/{record_id}", status_code=204)
async def delete_compliance_record(
    record_id: str,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> None:
    record = await db.get(ComplianceRecord, record_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Compliance record not found")
    record_type = record.record_type
    await db.delete(record)
    await _audit(db, "compliance_record_deleted", "compliance", f"Deleted dashboard compliance record: {record_type}", None)
    await db.commit()


@router.get("/audit-logs", response_model=list[AuditLogResponse])
async def list_audit_logs(
    limit: int = Query(default=50, le=200),
    domain: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> list[AuditLogResponse]:
    q = select(AuditLog).order_by(desc(AuditLog.created_at)).limit(limit)
    if domain:
        q = q.where(AuditLog.domain == domain)
    result = await db.execute(q)
    return result.scalars().all()  # type: ignore[return-value]


@router.get("/agent-actions", response_model=list[AgentActionResponse])
async def list_agent_actions(
    limit: int = Query(default=25, le=100),
    status: str | None = Query(default="pending"),
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> list[AgentActionResponse]:
    q = select(AgentAction).order_by(desc(AgentAction.created_at)).limit(limit)
    if status:
        q = q.where(AgentAction.status == status)
    result = await db.execute(q)
    return result.scalars().all()  # type: ignore[return-value]


@router.post("/agent-actions/generate", response_model=list[AgentActionResponse])
async def generate_agent_actions(
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> list[AgentActionResponse]:
    actions = await _actions.generate_recommendations(db)
    await db.commit()
    return actions  # type: ignore[return-value]


@router.post("/agent-actions/{action_id}/approve", response_model=AgentActionResponse)
async def approve_agent_action(
    action_id: str,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> AgentActionResponse:
    action = await db.get(AgentAction, action_id)
    if action is None:
        raise HTTPException(status_code=404, detail="Agent action not found")
    action = await _actions.approve(db, action)
    await db.commit()
    await db.refresh(action)
    return action  # type: ignore[return-value]


@router.post("/agent-actions/{action_id}/reject", response_model=AgentActionResponse)
async def reject_agent_action(
    action_id: str,
    payload: RejectAgentActionRequest,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> AgentActionResponse:
    action = await db.get(AgentAction, action_id)
    if action is None:
        raise HTTPException(status_code=404, detail="Agent action not found")
    action = await _actions.reject(db, action, payload.reason)
    await db.commit()
    await db.refresh(action)
    return action  # type: ignore[return-value]


@router.get("/automation-rules", response_model=list[AutomationRuleResponse])
async def list_automation_rules(
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> list[AutomationRuleResponse]:
    result = await db.execute(select(AutomationRule).order_by(AutomationRule.created_at))
    return result.scalars().all()  # type: ignore[return-value]


@router.post("/automation-rules/seed", response_model=list[AutomationRuleResponse])
async def seed_automation_rules(
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> list[AutomationRuleResponse]:
    rules = await _automation.seed_defaults(db)
    await db.commit()
    return rules  # type: ignore[return-value]


@router.post("/automation-rules/run", response_model=AutomationRunResponse)
async def run_automation_rules(
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> AutomationRunResponse:
    result = await _automation.run_enabled(db)
    await db.commit()
    return AutomationRunResponse(**result)


@router.post("/simulate-fraud", response_model=list[TransactionResponse])
async def simulate_fraud(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[TransactionResponse]:
    scenarios = random.sample(_FRAUD_SCENARIOS, k=3)
    created: list[Transaction] = []
    for s in scenarios:
        tx = Transaction(
            id=str(uuid4()),
            merchant=s["merchant"],
            item_name=s["item_name"],
            amount=s["amount"],
            category=s["category"],
            location=s["location"],
            risk_score=s["risk_score"],
            flagged=True,
            notes=s["notes"],
            source="simulation",
        )
        db.add(tx)
        created.append(tx)

    await db.flush()

    # Build alert lines
    lines = "\n".join(
        f"  • ${tx.amount:,.0f} at {tx.merchant} ({tx.location}) — risk {tx.risk_score}/100"
        for tx in created
    )
    alert = (
        f"🚨 FRAUD ALERT — OpsMesh AI\n\n"
        f"{len(created)} suspicious transactions detected:\n\n"
        f"{lines}\n\n"
        f"All flagged automatically. Reply \"show flagged transactions\" to review "
        f"or \"explain [merchant name]\" for details."
    )

    settings = get_settings()
    if settings.feature_messaging_imessage and current_user.preferred_phone_number:
        try:
            thread = await ensure_phone_thread(db, current_user)
            await asyncio.to_thread(
                send_photon_bridge_message,
                "imessage",
                thread.id,
                current_user.preferred_phone_number,
                alert,
            )
        except Exception:
            pass

    db.add(AuditLog(
        id=str(uuid4()),
        event_type="fraud_simulation",
        domain="transactions",
        action_taken=f"Simulated {len(created)} suspicious transactions and sent phone alert",
        reasoning="Manual fraud simulation triggered from dashboard",
        source="dashboard",
    ))
    await db.commit()
    for tx in created:
        await db.refresh(tx)
    return created  # type: ignore[return-value]


@router.get("/daily-briefing", response_model=DailyBriefingResponse)
async def get_daily_briefing(
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> DailyBriefingResponse:
    flagged_count = int(
        await db.scalar(select(func.count(Transaction.id)).where(Transaction.flagged.is_(True))) or 0
    )
    high_risk_count = int(
        await db.scalar(select(func.count(Transaction.id)).where(Transaction.risk_score >= 71)) or 0
    )
    open_tickets = int(
        await db.scalar(select(func.count(SupportTicket.id)).where(SupportTicket.status == "open")) or 0
    )
    pending_compliance = int(
        await db.scalar(select(func.count(ComplianceRecord.id)).where(ComplianceRecord.status == "pending")) or 0
    )
    # Pull live data for next actions — never read from the stale agent_actions table
    top_flagged = list(
        (
            await db.execute(
                select(Transaction)
                .where(Transaction.flagged.is_(True))
                .order_by(desc(Transaction.risk_score))
                .limit(2)
            )
        ).scalars().all()
    )
    urgent_tickets = list(
        (
            await db.execute(
                select(SupportTicket)
                .where(SupportTicket.status == "open", SupportTicket.priority == "high")
                .order_by(desc(SupportTicket.created_at))
                .limit(1)
            )
        ).scalars().all()
    )
    flagged_compliance = list(
        (
            await db.execute(
                select(ComplianceRecord)
                .where(ComplianceRecord.status == "pending", ComplianceRecord.policy_flag.is_(True))
                .order_by(desc(ComplianceRecord.created_at))
                .limit(1)
            )
        ).scalars().all()
    )

    recommended_actions: list[str] = []
    for tx in top_flagged:
        label = f"{tx.merchant}" + (f" — {tx.item_name}" if tx.item_name else "")
        recommended_actions.append(f"Review flagged transaction: {label} (risk {tx.risk_score}/100)")
    for tk in urgent_tickets:
        snippet = tk.description[:60] + ("…" if len(tk.description) > 60 else "")
        recommended_actions.append(f"Escalate urgent ticket: {snippet}")
    for cr in flagged_compliance:
        recommended_actions.append(f"Resolve policy-flagged {cr.record_type.replace('_', ' ')} compliance item")
    if not recommended_actions:
        if open_tickets > 0:
            recommended_actions.append(f"Review {open_tickets} open support ticket{'s' if open_tickets != 1 else ''}")
        if pending_compliance > 0:
            recommended_actions.append(f"Review {pending_compliance} pending compliance item{'s' if pending_compliance != 1 else ''}")
        if not recommended_actions:
            recommended_actions.append("No urgent actions — all queues are clear")

    highlights = [
        f"{flagged_count} flagged transaction{'s' if flagged_count != 1 else ''}, including {high_risk_count} high-risk item{'s' if high_risk_count != 1 else ''}.",
        f"{open_tickets} open support ticket{'s' if open_tickets != 1 else ''} need{'s' if open_tickets == 1 else ''} queue coverage.",
        f"{pending_compliance} compliance record{'s' if pending_compliance != 1 else ''} pending review.",
    ]

    summary = (
        f"Today: {flagged_count} flagged transactions, {open_tickets} open tickets, "
        f"and {pending_compliance} pending compliance records."
    )
    if _llm.enabled:
        prompt = (
            "Create a crisp executive operations briefing in one sentence. "
            "Use only these facts:\n"
            + "\n".join(highlights + [f"Next actions: {', '.join(recommended_actions)}"])
        )
        try:
            summary = await asyncio.to_thread(_llm.generate_reply, prompt)
        except Exception:  # noqa: BLE001
            pass

    return DailyBriefingResponse(
        generated_at=datetime.now(timezone.utc),
        summary=summary,
        highlights=highlights,
        recommended_actions=recommended_actions,
    )


@router.get("/insights", response_model=InsightsResponse)
async def get_insights(
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> InsightsResponse:
    flagged_count = int(
        await db.scalar(select(func.count(Transaction.id)).where(Transaction.flagged.is_(True))) or 0
    )
    open_tickets = int(
        await db.scalar(select(func.count(SupportTicket.id)).where(SupportTicket.status == "open")) or 0
    )
    pending_compliance = int(
        await db.scalar(select(func.count(ComplianceRecord.id)).where(ComplianceRecord.status == "pending")) or 0
    )

    top_risk_result = await db.execute(
        select(Transaction).where(Transaction.flagged.is_(True)).order_by(desc(Transaction.risk_score)).limit(1)
    )
    top_risk = top_risk_result.scalar_one_or_none()

    ticket_cats_result = await db.execute(
        select(SupportTicket.category).where(SupportTicket.status == "open")
    )
    ticket_cats = [row[0] for row in ticket_cats_result.all()]
    top_category = Counter(ticket_cats).most_common(1)[0][0] if ticket_cats else None

    summary = _build_insights_summary(
        flagged_count, open_tickets, pending_compliance, top_risk, top_category
    )

    if _llm.enabled and (flagged_count > 0 or open_tickets > 0 or pending_compliance > 0):
        prompt = (
            f"Summarize these ops metrics in 2 sentences for an executive: "
            f"{flagged_count} flagged transactions, {open_tickets} open support tickets, "
            f"{pending_compliance} pending compliance items"
            + (f", top risk: ${top_risk.amount:.0f} at {top_risk.merchant}" if top_risk else "")
            + (f", most common ticket type: {top_category}" if top_category else "")
            + ". Be specific and direct."
        )
        try:
            summary = await asyncio.to_thread(_llm.generate_reply, prompt)
        except Exception:
            pass

    return InsightsResponse(
        summary=summary,
        flagged_transactions=flagged_count,
        open_tickets=open_tickets,
        pending_compliance=pending_compliance,
        highest_risk_amount=top_risk.amount if top_risk else None,
        highest_risk_merchant=top_risk.merchant if top_risk else None,
        top_ticket_category=top_category,
    )


def _build_insights_summary(
    flagged: int,
    tickets: int,
    compliance: int,
    top_risk: Transaction | None,
    top_category: str | None,
) -> str:
    parts = []
    if flagged > 0:
        parts.append(f"{flagged} flagged transaction{'s' if flagged != 1 else ''}")
    if tickets > 0:
        cat = f" ({top_category.replace('_', ' ')})" if top_category else ""
        parts.append(f"{tickets} open support ticket{'s' if tickets != 1 else ''}{cat}")
    if compliance > 0:
        parts.append(f"{compliance} pending compliance item{'s' if compliance != 1 else ''}")
    if top_risk:
        parts.append(f"highest risk: ${top_risk.amount:.0f} at {top_risk.merchant}")
    return ". ".join(parts).capitalize() + "." if parts else "All clear — no active alerts."
