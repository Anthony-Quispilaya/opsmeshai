from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from backend.app.models.user import UserRole


class UserResponse(BaseModel):
    id: str
    email: EmailStr
    full_name: str
    preferred_phone_number: str | None = None
    welcome_message_sent_at: datetime | None = None
    role: UserRole
    created_at: datetime

    class Config:
        from_attributes = True


class UserPhoneUpdateRequest(BaseModel):
    preferred_phone_number: str = Field(min_length=8, max_length=32)
