from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agents.orchestrator import AgentOrchestrator, OrchestratorError
from backend.app.api.deps import get_current_user
from backend.app.db.session import get_db
from backend.app.models.agent_run import AgentRun
from backend.app.models.message import Message, MessageRole
from backend.app.models.thread import Thread
from backend.app.models.user import User
from backend.app.schemas.conversations import (
    ConversationMessageRequest,
    ConversationMessageResponse,
    ConversationResponse,
    CreateConversationRequest,
)

router = APIRouter(prefix="/conversations", tags=["conversations"])
orchestrator = AgentOrchestrator()


@router.post("", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    payload: CreateConversationRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Thread:
    thread = Thread(title=payload.title.strip(), owner_id=current_user.id)
    db.add(thread)
    await db.commit()
    await db.refresh(thread)
    return thread


@router.post("/{conversation_id}/messages", response_model=ConversationMessageResponse)
async def post_message(
    conversation_id: str,
    payload: ConversationMessageRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ConversationMessageResponse:
    thread_result = await db.execute(
        select(Thread).where(Thread.id == conversation_id, Thread.owner_id == current_user.id)
    )
    thread = thread_result.scalar_one_or_none()
    if thread is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    user_message = Message(
        thread_id=thread.id,
        role=MessageRole.user,
        content=payload.content.strip(),
    )
    db.add(user_message)
    await db.flush()

    run = AgentRun(
        thread_id=thread.id,
        user_message_id=user_message.id,
        status="running",
        trace={},
    )
    db.add(run)
    await db.flush()

    try:
        result = orchestrator.run_turn(payload.content.strip())
        assistant_message = Message(
            thread_id=thread.id,
            role=MessageRole.assistant,
            content=result.assistant_message,
        )
        db.add(assistant_message)
        await db.flush()

        run.status = "completed"
        run.assistant_message_id = assistant_message.id
        run.trace = result.trace.model_dump()
        await db.commit()

        return ConversationMessageResponse(
            thread_id=thread.id,
            user_message_id=user_message.id,
            assistant_message_id=assistant_message.id,
            assistant_message=result.assistant_message,
            run_status=run.status,
            trace=run.trace,
        )
    except OrchestratorError as exc:
        run.status = "failed"
        run.error_code = exc.code
        run.error_message = str(exc)
        run.trace = {"error": str(exc), "code": exc.code}
        await db.commit()
        raise HTTPException(
            status_code=400,
            detail={
                "code": exc.code,
                "message": str(exc),
                "thread_id": thread.id,
                "run_id": run.id,
            },
        ) from exc
