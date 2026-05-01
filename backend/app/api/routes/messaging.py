import json

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from agents.orchestrator import AgentOrchestrator, OrchestratorError
from backend.app.api.deps import get_current_user
from backend.app.core.config import get_settings
from backend.app.db.session import get_db
from backend.app.models.agent_run import AgentRun
from backend.app.models.message import Message, MessageRole
from backend.app.models.messaging_event import MessagingEvent
from backend.app.models.thread import Thread
from backend.app.models.user import User
from backend.app.schemas.messaging import (
    OutboundSendRequest,
    OutboundSendResponse,
    WebhookInboundResponse,
)
from backend.app.schemas.photon_bridge import PhotonInboundEvent
from backend.app.services.ops_processor import OpsProcessor
from backend.app.services.photon_outbound import send_photon_bridge_message
from backend.app.utils.phone import normalize_e164
from messaging.channels import event_preview
from messaging.gateway import PhotonGateway

router = APIRouter(prefix="/messaging", tags=["messaging"])
gateway = PhotonGateway()
orchestrator = AgentOrchestrator()
ops_processor = OpsProcessor()
settings = get_settings()


def _channel_enabled(channel: str) -> bool:
    mapping = {
        "sms": settings.feature_messaging_sms,
        "whatsapp": settings.feature_messaging_whatsapp,
        "imessage": settings.feature_messaging_imessage,
        "snapchat": settings.feature_messaging_snapchat,
    }
    return mapping.get(channel, False)


def _require_photon_mode() -> None:
    if settings.messaging_transport_mode != "photon_sdk":
        raise HTTPException(
            status_code=400,
            detail="Messaging is configured for Photon-only mode. Set MESSAGING_TRANSPORT_MODE=photon_sdk.",
        )


def _channel_from_platform(platform: str) -> str:
    value = platform.strip().lower()
    if "whatsapp" in value:
        return "whatsapp"
    if "imessage" in value:
        return "imessage"
    if "snapchat" in value:
        return "snapchat"
    return "sms"


def _bridge_send_or_http_error(channel: str, thread_id: str, recipient: str, text: str) -> dict:
    try:
        return send_photon_bridge_message(channel, thread_id, recipient, text)
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


async def _store_inbound_message(
    db: AsyncSession,
    channel: str,
    provider_event_id: str,
    provider_message_id: str,
    thread_id: str,
    sender: str,
    text: str,
    payload_preview: dict,
) -> WebhookInboundResponse:
    thread_result = await db.execute(select(Thread).where(Thread.id == thread_id))
    thread = thread_result.scalar_one_or_none()
    if thread is None:
        raise HTTPException(status_code=404, detail="Thread not found for inbound message")

    event = MessagingEvent(
        channel=channel,
        provider_event_id=provider_event_id,
        thread_id=thread_id,
        direction="inbound",
        status="accepted",
        provider_message_id=provider_message_id,
        recipient=sender,
        payload=payload_preview,
    )
    db.add(event)
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        return WebhookInboundResponse(
            accepted=True,
            duplicate=True,
            event_id=provider_event_id,
            thread_id=thread_id,
            message_id=None,
        )

    inbound_message = Message(
        thread_id=thread_id,
        role=MessageRole.user,
        content=text,
    )
    db.add(inbound_message)
    await db.flush()

    event.status = "stored"
    await db.flush()

    if settings.enable_inbound_auto_reply and text.strip() and settings.messaging_transport_mode == "photon_sdk":
        # Load recent conversation history for this thread (last 10 turns)
        history_result = await db.execute(
            select(Message)
            .where(Message.thread_id == thread_id)
            .order_by(Message.created_at.desc())
            .limit(10)
        )
        history: list[dict] = [
            {"role": msg.role.value, "content": msg.content}
            for msg in reversed(history_result.scalars().all())
        ]

        run = AgentRun(
            thread_id=thread_id,
            user_message_id=inbound_message.id,
            status="running",
            trace={},
        )
        db.add(run)
        await db.flush()
        try:
            # Try ops-aware processing first (transactions, tickets, compliance, queries)
            ops_reply = await ops_processor.process(text.strip(), db, history=history)
            if ops_reply is not None:
                reply_text = ops_reply
                trace_data: dict = {"intent": "ops_processed", "steps": ["ops_processor"]}
            else:
                result = orchestrator.run_turn(text.strip(), history=history)
                reply_text = result.assistant_message
                trace_data = result.trace.model_dump()

            assistant_message = Message(
                thread_id=thread_id,
                role=MessageRole.assistant,
                content=reply_text,
            )
            db.add(assistant_message)
            await db.flush()

            outbound_payload = _bridge_send_or_http_error(
                channel=channel,
                thread_id=thread_id,
                recipient=sender,
                text=reply_text,
            )
            provider_mid = str(outbound_payload.get("provider_message_id", f"auto-{thread_id}"))
            outbound_event = MessagingEvent(
                channel=channel,
                provider_event_id=provider_mid,
                thread_id=thread_id,
                direction="outbound",
                status="sent",
                provider_message_id=provider_mid,
                recipient=sender,
                payload=outbound_payload,
            )
            db.add(outbound_event)

            run.status = "completed"
            run.assistant_message_id = assistant_message.id
            run.trace = trace_data
        except OrchestratorError as exc:
            run.status = "failed"
            run.error_code = exc.code
            run.error_message = str(exc)
            run.trace = {"error": str(exc), "code": exc.code}
            await db.flush()

    await db.commit()
    return WebhookInboundResponse(
        accepted=True,
        duplicate=False,
        event_id=provider_event_id,
        thread_id=thread_id,
        message_id=inbound_message.id,
    )


async def _resolve_thread_for_sender(
    db: AsyncSession, sender: str, fallback_thread_id: str | None
) -> str | None:
    normalized_sender = normalize_e164(sender)
    user_result = await db.execute(
        select(User).where(User.preferred_phone_number == normalized_sender)
    )
    user = user_result.scalar_one_or_none()
    if user is None:
        if fallback_thread_id:
            fallback_thread_result = await db.execute(select(Thread).where(Thread.id == fallback_thread_id))
            fallback_thread = fallback_thread_result.scalar_one_or_none()
            if fallback_thread is not None:
                return fallback_thread.id
        return None

    expected_title = f"Phone Thread ({normalized_sender})"
    thread_result = await db.execute(
        select(Thread).where(Thread.owner_id == user.id, Thread.title == expected_title)
    )
    thread = thread_result.scalar_one_or_none()
    if thread is None:
        thread = Thread(owner_id=user.id, title=expected_title)
        db.add(thread)
        await db.flush()
    return thread.id


@router.post("/send", response_model=OutboundSendResponse)
async def send_message(
    payload: OutboundSendRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> OutboundSendResponse:
    _require_photon_mode()
    if not _channel_enabled(payload.channel):
        raise HTTPException(status_code=400, detail=f"Channel '{payload.channel}' is disabled.")

    recipient = payload.recipient.strip()
    if recipient.lower() in {"me", "self"}:
        if not current_user.preferred_phone_number:
            raise HTTPException(
                status_code=400,
                detail="No preferred phone number configured. Set it via PATCH /me/phone first.",
            )
        recipient = current_user.preferred_phone_number

    thread_result = await db.execute(
        select(Thread).where(Thread.id == payload.thread_id, Thread.owner_id == current_user.id)
    )
    thread = thread_result.scalar_one_or_none()
    if thread is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    bridge_response = _bridge_send_or_http_error(
        channel=payload.channel,
        thread_id=payload.thread_id,
        recipient=recipient,
        text=payload.text,
    )
    provider_message_id = str(bridge_response.get("provider_message_id", "unknown"))

    event = MessagingEvent(
        channel=payload.channel,
        provider_event_id=provider_message_id,
        thread_id=payload.thread_id,
        direction="outbound",
        status="sent",
        provider_message_id=provider_message_id,
        recipient=recipient,
        payload=bridge_response,
    )
    db.add(event)
    await db.commit()

    return OutboundSendResponse(
        status="sent",
        provider_message_id=provider_message_id,
        channel=payload.channel,
        thread_id=payload.thread_id,
    )


@router.post("/webhooks/{channel}", response_model=WebhookInboundResponse)
async def inbound_webhook(
    channel: str,
    request: Request,
    x_photon_signature: str = Header(default=""),
    db: AsyncSession = Depends(get_db),
) -> WebhookInboundResponse:
    _require_photon_mode()
    if channel not in {"sms", "whatsapp", "imessage", "snapchat"}:
        raise HTTPException(status_code=404, detail="Unsupported channel")
    if not _channel_enabled(channel):
        raise HTTPException(status_code=400, detail=f"Channel '{channel}' is disabled.")

    webhook_secret = settings.photon_webhook_secret or "dev-photon-secret"
    raw = await request.body()
    if not gateway.verify(channel, raw, x_photon_signature, webhook_secret):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    try:
        payload = json.loads(raw.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="Invalid JSON payload") from exc

    inbound = gateway.parse_inbound(channel, payload)
    return await _store_inbound_message(
        db=db,
        channel=channel,
        provider_event_id=inbound.event_id,
        provider_message_id=inbound.provider_message_id,
        thread_id=inbound.thread_id,
        sender=inbound.sender,
        text=inbound.text,
        payload_preview={"preview": event_preview(payload)},
    )


@router.post("/photon/events", response_model=WebhookInboundResponse)
async def ingest_photon_event(
    payload: PhotonInboundEvent,
    x_photon_bridge_token: str = Header(default=""),
    db: AsyncSession = Depends(get_db),
) -> WebhookInboundResponse:
    _require_photon_mode()
    if x_photon_bridge_token != settings.photon_bridge_token:
        raise HTTPException(status_code=401, detail="Invalid bridge token")

    channel = _channel_from_platform(payload.platform)
    if not _channel_enabled(channel):
        raise HTTPException(status_code=400, detail=f"Channel '{channel}' is disabled.")

    resolved_thread_id = await _resolve_thread_for_sender(db, payload.sender, payload.thread_id)
    if not resolved_thread_id:
        raise HTTPException(
            status_code=400,
            detail="No thread mapping for sender. Configure user preferred phone number first.",
        )

    return await _store_inbound_message(
        db=db,
        channel=channel,
        provider_event_id=payload.event_id,
        provider_message_id=payload.provider_message_id,
        thread_id=resolved_thread_id,
        sender=payload.sender,
        text=payload.text,
        payload_preview={
            "platform": payload.platform,
            "source": "photon_sdk",
            "preview": payload.text[:200],
        },
    )
