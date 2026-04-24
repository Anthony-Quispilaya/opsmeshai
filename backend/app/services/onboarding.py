import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import get_settings
from backend.app.models.message import Message, MessageRole
from backend.app.models.messaging_event import MessagingEvent
from backend.app.models.thread import Thread
from backend.app.models.user import User
from backend.app.services.photon_outbound import send_photon_bridge_message

logger = logging.getLogger(__name__)

WELCOME_IMESSAGE_TEXT = (
    "Hi — this is your OpsMesh AI agent on iMessage. "
    "I'm here to help your team get work done: ask questions, request updates, "
    "or delegate tasks, and I'll respond here. "
    "Reply anytime to pick up where you left off."
)


async def ensure_phone_thread(db: AsyncSession, user: User) -> Thread:
    phone = user.preferred_phone_number
    if not phone:
        raise ValueError("User has no preferred phone number")

    expected_title = f"Phone Thread ({phone})"
    thread_result = await db.execute(
        select(Thread).where(Thread.owner_id == user.id, Thread.title == expected_title)
    )
    thread = thread_result.scalar_one_or_none()
    if thread is None:
        thread = Thread(owner_id=user.id, title=expected_title)
        db.add(thread)
        await db.flush()
    return thread


async def send_welcome_imessage(
    db: AsyncSession,
    user: User,
    *,
    force: bool = False,
) -> tuple[bool, str | None]:
    """
    Ensure the phone thread exists, send the product intro via Photon (iMessage), and record it.
    Returns (sent, error_detail).
    - sent=True means Photon accepted the outbound and records were stored.
    - sent=False includes a reason in error_detail.
    """
    if not user.preferred_phone_number:
        return False, "No preferred phone number set for this user."
    if user.welcome_message_sent_at is not None and not force:
        return False, "Welcome introduction already sent for this user."

    settings = get_settings()
    if not settings.feature_messaging_imessage:
        logger.warning("Welcome iMessage skipped: FEATURE_MESSAGING_IMESSAGE is disabled")
        return False, "FEATURE_MESSAGING_IMESSAGE is disabled."

    thread = await ensure_phone_thread(db, user)
    recipient = user.preferred_phone_number

    try:
        bridge_response = await asyncio.to_thread(
            send_photon_bridge_message,
            "imessage",
            thread.id,
            recipient,
            WELCOME_IMESSAGE_TEXT,
        )
    except Exception as exc:
        logger.exception("Welcome iMessage failed for user %s", user.id)
        return False, str(exc)

    provider_message_id = str(bridge_response.get("provider_message_id", "unknown"))

    intro = Message(
        thread_id=thread.id,
        role=MessageRole.assistant,
        content=WELCOME_IMESSAGE_TEXT,
    )
    db.add(intro)
    await db.flush()

    event = MessagingEvent(
        channel="imessage",
        provider_event_id=provider_message_id,
        thread_id=thread.id,
        direction="outbound",
        status="sent",
        provider_message_id=provider_message_id,
        recipient=recipient,
        payload=bridge_response,
    )
    db.add(event)

    user.welcome_message_sent_at = datetime.now(timezone.utc)
    db.add(user)
    await db.flush()
    return True, None
