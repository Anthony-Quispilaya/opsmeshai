from datetime import datetime

from pydantic import BaseModel


class TransactionResponse(BaseModel):
    id: str
    amount: float
    merchant: str
    location: str
    category: str
    risk_score: int
    flagged: bool
    notes: str | None
    source: str
    created_at: datetime

    class Config:
        from_attributes = True


class SupportTicketResponse(BaseModel):
    id: str
    customer_identifier: str | None
    description: str
    category: str
    status: str
    priority: str
    source: str
    created_at: datetime

    class Config:
        from_attributes = True


class ComplianceRecordResponse(BaseModel):
    id: str
    record_type: str
    description: str
    status: str
    policy_flag: bool
    severity: str | None
    recommendation: str | None
    source: str
    created_at: datetime

    class Config:
        from_attributes = True


class AuditLogResponse(BaseModel):
    id: str
    event_type: str
    domain: str
    action_taken: str
    reasoning: str | None
    source: str
    related_entity_id: str | None
    created_at: datetime

    class Config:
        from_attributes = True


class InsightsResponse(BaseModel):
    summary: str
    flagged_transactions: int
    open_tickets: int
    pending_compliance: int
    highest_risk_amount: float | None
    highest_risk_merchant: str | None
    top_ticket_category: str | None
