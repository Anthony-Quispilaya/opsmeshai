from pydantic import BaseModel, EmailStr, Field

from backend.app.schemas.user import UserResponse


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=2, max_length=255)
    preferred_phone_number: str = Field(min_length=8, max_length=32)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class RegisterResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
