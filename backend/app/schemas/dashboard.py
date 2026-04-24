from pydantic import BaseModel


class DashboardSummaryResponse(BaseModel):
    user_email: str
    active_threads: int
    total_messages: int
    backend_status: str
    total_transactions: int = 0
    flagged_transactions: int = 0
    open_support_tickets: int = 0
    pending_compliance_items: int = 0
