from dataclasses import dataclass


@dataclass
class InboundMessage:
    channel: str
    event_id: str
    provider_message_id: str
    thread_id: str
    sender: str
    text: str


@dataclass
class OutboundMessage:
    channel: str
    thread_id: str
    recipient: str
    text: str
