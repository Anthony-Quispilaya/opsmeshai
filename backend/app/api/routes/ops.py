import asyncio
from collections import Counter

from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from agents.llm import LLMResponder
from backend.app.api.deps import get_current_user
from backend.app.db.session import get_db
from backend.app.models.audit_log import AuditLog
from backend.app.models.compliance_record import ComplianceRecord
from backend.app.models.support_ticket import SupportTicket
from backend.app.models.transaction import Transaction
from backend.app.models.user import User
from backend.app.schemas.ops import (
    AuditLogResponse,
    ComplianceRecordResponse,
    InsightsResponse,
    SupportTicketResponse,
    TransactionResponse,
)

router = APIRouter(prefix="/ops", tags=["ops"])
_llm = LLMResponder()


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
