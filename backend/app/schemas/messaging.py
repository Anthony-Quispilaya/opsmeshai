from pydantic import BaseModel, Field


class OutboundSendRequest(BaseModel):
    channel: str = Field(pattern="^(sms|whatsapp|imessage|snapchat)$")
    thread_id: str
    recipient: str
    text: str = Field(min_length=1, max_length=2000)


class OutboundSendResponse(BaseModel):
    status: str
    provider_message_id: str
    channel: str
    thread_id: str


class WebhookInboundRequest(BaseModel):
    event_id: str
    provider_message_id: str | None = None
    thread_id: str
    sender: str
    text: str = Field(default="", max_length=2000)


class WebhookInboundResponse(BaseModel):
    accepted: bool
    duplicate: bool = False
    event_id: str
    thread_id: str
    message_id: str | None = None
