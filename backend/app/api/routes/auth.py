import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.security import create_access_token, hash_password, verify_password
from backend.app.db.session import SessionLocal, get_db
from backend.app.models.user import User
from backend.app.schemas.auth import LoginRequest, RegisterRequest, RegisterResponse, TokenResponse
from backend.app.schemas.user import UserResponse
from backend.app.services.onboarding import send_welcome_imessage
from backend.app.utils.phone import normalize_e164

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


async def _deliver_welcome_intro_task(user_id: str) -> None:
    async with SessionLocal() as db:
        try:
            result = await db.execute(select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()
            if not user:
                return
            sent, error_detail = await send_welcome_imessage(db, user, force=False)
            if sent:
                await db.commit()
            else:
                logger.warning("Welcome iMessage not sent for user %s: %s", user_id, error_detail)
                await db.rollback()
        except Exception:
            logger.exception("Welcome intro task failed for user %s", user_id)
            await db.rollback()


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
async def register(
    payload: RegisterRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> RegisterResponse:
    existing = await db.execute(select(User).where(User.email == payload.email.lower()))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=400, detail="Email already registered")

    normalized_phone = normalize_e164(payload.preferred_phone_number)
    if len(normalized_phone) < 8:
        raise HTTPException(status_code=400, detail="Enter a valid phone number with country code.")

    existing_phone = await db.execute(
        select(User).where(User.preferred_phone_number == normalized_phone)
    )
    if existing_phone.scalar_one_or_none() is not None:
        raise HTTPException(status_code=400, detail="Phone number already registered")

    user = User(
        email=payload.email.lower(),
        full_name=payload.full_name.strip(),
        preferred_phone_number=normalized_phone,
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    background_tasks.add_task(_deliver_welcome_intro_task, user.id)

    token = create_access_token(user.id)
    return RegisterResponse(
        access_token=token,
        user=UserResponse.model_validate(user),
    )


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    result = await db.execute(select(User).where(User.email == payload.email.lower()))
    user = result.scalar_one_or_none()
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return TokenResponse(access_token=create_access_token(user.id))
