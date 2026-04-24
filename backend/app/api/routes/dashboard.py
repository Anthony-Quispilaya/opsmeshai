from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.deps import get_current_user
from backend.app.db.session import get_db
from backend.app.models.compliance_record import ComplianceRecord
from backend.app.models.message import Message
from backend.app.models.support_ticket import SupportTicket
from backend.app.models.thread import Thread
from backend.app.models.transaction import Transaction
from backend.app.models.user import User
from backend.app.schemas.dashboard import DashboardSummaryResponse

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummaryResponse)
async def summary(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DashboardSummaryResponse:
    threads_result = await db.execute(
        select(func.count(Thread.id)).where(Thread.owner_id == current_user.id)
    )
    active_threads = int(threads_result.scalar_one() or 0)

    messages_result = await db.execute(
        select(func.count(Message.id))
        .join(Thread, Thread.id == Message.thread_id)
        .where(Thread.owner_id == current_user.id)
    )
    total_messages = int(messages_result.scalar_one() or 0)

    total_transactions = int(await db.scalar(select(func.count(Transaction.id))) or 0)
    flagged_transactions = int(
        await db.scalar(select(func.count(Transaction.id)).where(Transaction.flagged.is_(True))) or 0
    )
    open_support_tickets = int(
        await db.scalar(select(func.count(SupportTicket.id)).where(SupportTicket.status == "open")) or 0
    )
    pending_compliance_items = int(
        await db.scalar(select(func.count(ComplianceRecord.id)).where(ComplianceRecord.status == "pending")) or 0
    )

    return DashboardSummaryResponse(
        user_email=current_user.email,
        active_threads=active_threads,
        total_messages=total_messages,
        backend_status="connected",
        total_transactions=total_transactions,
        flagged_transactions=flagged_transactions,
        open_support_tickets=open_support_tickets,
        pending_compliance_items=pending_compliance_items,
    )
