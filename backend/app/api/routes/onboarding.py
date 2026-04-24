from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.deps import get_current_user
from backend.app.db.session import get_db
from backend.app.models.user import User
from backend.app.schemas.user import UserResponse
from backend.app.services.onboarding import send_welcome_imessage

router = APIRouter(prefix="/onboarding", tags=["onboarding"])


class WelcomeStatusResponse(BaseModel):
    sent: bool
    error_detail: str | None = None
    user: UserResponse


@router.post("/welcome-imessage", response_model=WelcomeStatusResponse)
async def send_welcome_imessage_endpoint(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> WelcomeStatusResponse:
    if not current_user.preferred_phone_number:
        raise HTTPException(
            status_code=400,
            detail="Set your phone number before requesting a welcome message.",
        )

    sent, error_detail = await send_welcome_imessage(db, current_user, force=True)
    if sent:
        await db.commit()
    else:
        await db.rollback()

    await db.refresh(current_user)
    return WelcomeStatusResponse(
        sent=sent,
        error_detail=error_detail,
        user=UserResponse.model_validate(current_user),
    )
