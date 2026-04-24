from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.deps import get_current_user
from backend.app.db.session import get_db
from backend.app.models.user import User
from backend.app.schemas.user import UserPhoneUpdateRequest, UserResponse
from backend.app.services.onboarding import send_welcome_imessage
from backend.app.utils.phone import normalize_e164

router = APIRouter(tags=["users"])


@router.get("/me", response_model=UserResponse)
async def me(current_user: User = Depends(get_current_user)) -> User:
    return current_user


@router.patch("/me/phone", response_model=UserResponse)
async def update_preferred_phone(
    payload: UserPhoneUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> User:
    previous = current_user.preferred_phone_number
    normalized = normalize_e164(payload.preferred_phone_number)
    if len(normalized) < 8:
        raise HTTPException(status_code=400, detail="Enter a valid phone number with country code.")
    existing = await db.execute(
        select(User).where(User.preferred_phone_number == normalized, User.id != current_user.id)
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=400, detail="Phone number is already assigned to another user.")

    current_user.preferred_phone_number = normalized
    db.add(current_user)
    await db.commit()
    await db.refresh(current_user)

    previous_norm = normalize_e164(previous) if previous else ""
    if normalized != previous_norm:
        sent, _ = await send_welcome_imessage(db, current_user, force=True)
        if sent:
            await db.commit()
        else:
            await db.rollback()
        await db.refresh(current_user)
    return current_user
