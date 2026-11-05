import hashlib
import re
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import bcrypt
import jwt

from app.core.config import settings
from app.core.errors import AppError

# Password policy regexes
PASSWORD_MIN_LENGTH = 8
LOWERCASE_REGEX = re.compile(r"[a-z]")
UPPERCASE_REGEX = re.compile(r"[A-Z]")
DIGIT_REGEX = re.compile(r"\d")
SPECIAL_CHAR_REGEX = re.compile(r"""[!@#$%^&*(),.?":{}|<>\-_]""")


def validate_password_strength(password: str) -> None:
    """Validate server-side password complexity requirements."""
    if len(password) < PASSWORD_MIN_LENGTH:
        raise AppError(
            message=f"Password must be at least {PASSWORD_MIN_LENGTH} characters long",
            code="WEAK_PASSWORD",
            status_code=400,
        )
    if not LOWERCASE_REGEX.search(password):
        raise AppError(
            message="Password must contain at least one lowercase letter",
            code="WEAK_PASSWORD",
            status_code=400,
        )
    if not UPPERCASE_REGEX.search(password):
        raise AppError(
            message="Password must contain at least one uppercase letter",
            code="WEAK_PASSWORD",
            status_code=400,
        )
    if not DIGIT_REGEX.search(password):
        raise AppError(
            message="Password must contain at least one digit",
            code="WEAK_PASSWORD",
            status_code=400,
        )
    if not SPECIAL_CHAR_REGEX.search(password):
        raise AppError(
            message="Password must contain at least one special character",
            code="WEAK_PASSWORD",
            status_code=400,
        )


def hash_password(password: str) -> str:
    """Hash plaintext password using bcrypt with random salt."""
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify plaintext password against bcrypt hash in constant time."""
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"), hashed_password.encode("utf-8")
        )
    except Exception:
        return False


def hash_token(token: str) -> str:
    """Produce SHA-256 hash of a token for secure database storage."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_access_token(
    subject: str,
    expires_delta: Optional[timedelta] = None,
    extra_claims: Optional[dict[str, Any]] = None,
) -> str:
    """Generate a short-lived signed JWT access token."""
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    claims: dict[str, Any] = {
        "sub": subject,
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
        "type": "access",
        "jti": str(uuid.uuid4()),
    }
    if extra_claims:
        claims.update(extra_claims)

    return jwt.encode(
        claims,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


def create_refresh_token(
    subject: str,
    expires_delta: Optional[timedelta] = None,
) -> tuple[str, datetime]:
    """Generate a signed JWT refresh token with random entropy."""
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    claims: dict[str, Any] = {
        "sub": subject,
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
        "type": "refresh",
        "jti": str(uuid.uuid4()),
        "nonce": secrets.token_hex(16),
    }

    token = jwt.encode(
        claims,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )
    return token, expire


def decode_token(token: str, expected_type: str = "access") -> dict[str, Any]:
    """Validate token signature, expiration, and token type claim."""
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
    except jwt.ExpiredSignatureError:
        raise AppError(
            message="Token has expired",
            code="TOKEN_EXPIRED",
            status_code=401,
        ) from None
    except jwt.InvalidTokenError:
        raise AppError(
            message="Invalid authentication token",
            code="INVALID_TOKEN",
            status_code=401,
        ) from None

    token_type = payload.get("type")
    if token_type != expected_type:
        raise AppError(
            message=f"Invalid token type: expected '{expected_type}', got '{token_type}'",
            code="INVALID_TOKEN_TYPE",
            status_code=401,
        )

    if not payload.get("sub"):
        raise AppError(
            message="Malformed token payload: missing subject",
            code="INVALID_TOKEN_PAYLOAD",
            status_code=401,
        )

    return payload

