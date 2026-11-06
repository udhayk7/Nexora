import uuid
from typing import Optional

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.errors import ForbiddenError, UnauthorizedError
from app.core.security import decode_token
from app.models.user import User

bearer_scheme = HTTPBearer(auto_error=False)


def get_token_from_header(
    auth: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> str:
    """Extract raw bearer token from Authorization header."""
    if not auth or not auth.credentials:
        raise UnauthorizedError("Authentication credentials were not provided")
    return auth.credentials


def get_current_user(
    token: str = Depends(get_token_from_header),
    db: Session = Depends(get_db),
) -> User:
    """Validate bearer token and resolve corresponding User entity."""
    payload = decode_token(token, expected_type="access")
    user_id_str = payload.get("sub")

    try:
        user_id = uuid.UUID(user_id_str)
    except (ValueError, TypeError):
        raise UnauthorizedError("Malformed credentials identifier") from None

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise UnauthorizedError("User does not exist")

    return user


def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Ensure authenticated user is active and in good standing."""
    if not current_user.is_active:
        raise ForbiddenError("User account has been disabled")
    return current_user


def get_client_ip(request: Request) -> str:
    """Extract reliable client IP from headers or connection."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"
