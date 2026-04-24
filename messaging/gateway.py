from __future__ import annotations

from uuid import uuid4

from messaging.channels import (
    IMessageAdapter,
    ChannelAdapter,
    SmsAdapter,
    SnapchatAdapter,
    WhatsappAdapter,
)
from messaging.types import InboundMessage, OutboundMessage


class PhotonGateway:
    """Photon-style gateway abstraction with channel adapters."""

    def __init__(self) -> None:
        self.adapters: dict[str, ChannelAdapter] = {
            "sms": SmsAdapter(),
            "whatsapp": WhatsappAdapter(),
            "imessage": IMessageAdapter(),
            "snapchat": SnapchatAdapter(),
        }

    def adapter_for(self, channel: str) -> ChannelAdapter:
        if channel not in self.adapters:
            raise ValueError(f"Unsupported channel '{channel}'.")
        return self.adapters[channel]

    def verify(self, channel: str, body: bytes, signature: str, secret: str) -> bool:
        return self.adapter_for(channel).verify_signature(body, signature, secret)

    def parse_inbound(self, channel: str, payload: dict) -> InboundMessage:
        return self.adapter_for(channel).parse_inbound(payload)

    def send(self, message: OutboundMessage) -> tuple[str, dict]:
        adapter = self.adapter_for(message.channel)
        provider_message_id = f"{message.channel}-{uuid4()}"
        outbound_payload = adapter.build_outbound_payload(message)
        outbound_payload["provider_message_id"] = provider_message_id
        return provider_message_id, outbound_payload
