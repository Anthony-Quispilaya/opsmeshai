from datetime import datetime

from pydantic import BaseModel, Field


class TransactionCreateRequest(BaseModel):
    amount: float = Field(gt=0)
    merchant: str = Field(min_length=1, max_length=255)
    item_name: str | None = Field(default=None, max_length=255)
    location: str = Field(default="Unknown", max_length=255)
    category: str = Field(default="retail", max_length=64)
    risk_score: int | None = Field(default=None, ge=0, le=100)
    flagged: bool = False
    notes: str | None = None


class TransactionUpdateRequest(BaseModel):
    amount: float | None = Field(default=None, gt=0)
    merchant: str | None = Field(default=None, min_length=1, max_length=255)
    item_name: str | None = Field(default=None, max_length=255)
    location: str | None = Field(default=None, max_length=255)
    category: str | None = Field(default=None, max_length=64)
    risk_score: int | None = Field(default=None, ge=0, le=100)
    flagged: bool | None = None
    notes: str | None = None


class SupportTicketCreateRequest(BaseModel):
    description: str = Field(min_length=1)
    category: str = Field(default="general", max_length=64)
    status: str = Field(default="open", pattern="^(open|in_review|resolved)$")
    priority: str = Field(default="medium", pattern="^(low|medium|high)$")
    customer_identifier: str | None = Field(default=None, max_length=255)


class SupportTicketUpdateRequest(BaseModel):
    description: str | None = Field(default=None, min_length=1)
    category: str | None = Field(default=None, max_length=64)
    status: str | None = Field(default=None, pattern="^(open|in_review|resolved)$")
    priority: str | None = Field(default=None, pattern="^(low|medium|high)$")
    customer_identifier: str | None = Field(default=None, max_length=255)


class ComplianceRecordCreateRequest(BaseModel):
    description: str = Field(min_length=1)
    record_type: str = Field(default="general", max_length=64)
    status: str = Field(default="pending", pattern="^(pending|approved|rejected)$")
    policy_flag: bool = False
    severity: str | None = Field(default="low", pattern="^(low|medium|high)$")
    recommendation: str | None = None


class ComplianceRecordUpdateRequest(BaseModel):
    description: str | None = Field(default=None, min_length=1)
    record_type: str | None = Field(default=None, max_length=64)
    status: str | None = Field(default=None, pattern="^(pending|approved|rejected)$")
    policy_flag: bool | None = None
    severity: str | None = Field(default=None, pattern="^(low|medium|high)$")
    recommendation: str | None = None


class TransactionResponse(BaseModel):
    id: str
    amount: float
    merchant: str
    item_name: str | None
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


class AgentActionResponse(BaseModel):
    id: str
    title: str
    description: str
    domain: str
    action_type: str
    entity_type: str
    entity_id: str | None
    status: str
    priority: str
    confidence: float
    rationale: str | None
    payload: dict
    source: str
    created_at: datetime
    resolved_at: datetime | None

    class Config:
        from_attributes = True


class RejectAgentActionRequest(BaseModel):
    reason: str | None = None


class AutomationRuleResponse(BaseModel):
    id: str
    name: str
    description: str
    domain: str
    trigger_type: str
    conditions: dict
    action_type: str
    action_payload: dict
    enabled: bool
    created_at: datetime
    last_run_at: datetime | None

    class Config:
        from_attributes = True


class AutomationRunResponse(BaseModel):
    rules_run: int
    actions_created: int
    message: str


class DailyBriefingResponse(BaseModel):
    generated_at: datetime
    summary: str
    highlights: list[str]
    recommended_actions: list[str]


class InsightsResponse(BaseModel):
    summary: str
    flagged_transactions: int
    open_tickets: int
    pending_compliance: int
    highest_risk_amount: float | None
    highest_risk_merchant: str | None
    top_ticket_category: str | None
