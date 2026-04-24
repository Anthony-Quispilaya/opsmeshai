from __future__ import annotations

import hashlib
import hmac
import json
from abc import ABC, abstractmethod

from messaging.types import InboundMessage, OutboundMessage


class ChannelAdapter(ABC):
    channel: str

    @abstractmethod
    def verify_signature(self, body: bytes, signature: str, secret: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    def parse_inbound(self, payload: dict) -> InboundMessage:
        raise NotImplementedError

    @abstractmethod
    def build_outbound_payload(self, message: OutboundMessage) -> dict:
        raise NotImplementedError


class HmacAdapter(ChannelAdapter):
    channel = "base"

    def verify_signature(self, body: bytes, signature: str, secret: str) -> bool:
        expected = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature or "")

    def parse_inbound(self, payload: dict) -> InboundMessage:
        return InboundMessage(
            channel=self.channel,
            event_id=str(payload["event_id"]),
            provider_message_id=str(payload.get("provider_message_id", payload["event_id"])),
            thread_id=str(payload["thread_id"]),
            sender=str(payload.get("sender", "unknown")),
            text=str(payload.get("text", "")),
        )

    def build_outbound_payload(self, message: OutboundMessage) -> dict:
        return {
            "channel": self.channel,
            "thread_id": message.thread_id,
            "recipient": message.recipient,
            "text": message.text,
            "metadata": {"transport": "photon", "version": "sprint4"},
        }


class SmsAdapter(HmacAdapter):
    channel = "sms"


class WhatsappAdapter(HmacAdapter):
    channel = "whatsapp"


class IMessageAdapter(HmacAdapter):
    channel = "imessage"


class SnapchatAdapter(HmacAdapter):
    channel = "snapchat"


def event_preview(payload: dict) -> str:
    compact = json.dumps(payload, separators=(",", ":"), ensure_ascii=True)
    return compact[:200]
