import re
import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")


class UserRegister(BaseModel):
    """User registration payload."""

    email: str = Field(..., examples=["user@example.com"])
    password: str = Field(..., min_length=8, examples=["SecurePass123!"])
    full_name: str = Field(..., min_length=1, max_length=100, examples=["Jane Doe"])

    @field_validator("email")
    @classmethod
    def validate_and_normalize_email(cls, v: str) -> str:
        normalized = v.strip().lower()
        if not EMAIL_REGEX.match(normalized):
            raise ValueError("Invalid email address format")
        return normalized

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, v: str) -> str:
        trimmed = v.strip()
        if not trimmed:
            raise ValueError("Full name cannot be blank")
        return trimmed


class UserLogin(BaseModel):
    """User login credential payload."""

    email: str = Field(..., examples=["user@example.com"])
    password: str = Field(..., examples=["SecurePass123!"])

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        return v.strip().lower()


class UserResponse(BaseModel):
    """Safe public user representation."""

    id: uuid.UUID
    email: str
    full_name: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    last_login_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    """Token response payload containing both access and refresh tokens."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshTokenRequest(BaseModel):
    """Payload for token refresh when cookies are not utilized."""

    refresh_token: Optional[str] = None


class MessageResponse(BaseModel):
    """Generic status message response."""

    message: str
