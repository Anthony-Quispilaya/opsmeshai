from datetime import datetime

from pydantic import BaseModel, Field


class CreateConversationRequest(BaseModel):
    title: str = Field(default="New Thread", min_length=1, max_length=255)


class ConversationResponse(BaseModel):
    id: str
    title: str
    created_at: datetime

    class Config:
        from_attributes = True


class ConversationMessageRequest(BaseModel):
    content: str = Field(min_length=1, max_length=4000)


class ConversationMessageResponse(BaseModel):
    thread_id: str
    user_message_id: str
    assistant_message_id: str | None = None
    assistant_message: str
    run_status: str
    error_code: str | None = None
    error_message: str | None = None
    trace: dict
