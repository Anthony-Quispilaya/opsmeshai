from pydantic import BaseModel, Field


class PhotonInboundEvent(BaseModel):
    event_id: str
    provider_message_id: str
    thread_id: str = Field(min_length=1)
    sender: str
    text: str = ""
    platform: str = "photon"
