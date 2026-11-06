import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_client_ip
from app.core.audit import audit_service
from app.core.config import settings
from app.core.database import get_db
from app.core.errors import ConflictError, UnauthorizedError
from app.core.rate_limit import login_limiter, register_limiter
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    hash_token,
    validate_password_strength,
    verify_password,
)
from app.models.token import RefreshToken
from app.models.user import User
from app.schemas.auth import (
    MessageResponse,
    RefreshTokenRequest,
    TokenResponse,
    UserLogin,
    UserRegister,
)

auth_router = APIRouter(prefix="/auth", tags=["auth"])

REFRESH_COOKIE_NAME = "refresh_token"
REFRESH_COOKIE_PATH = f"{settings.API_V1_STR}/auth"


def set_refresh_cookie(response: Response, raw_token: str) -> None:
    """Set secure HttpOnly cookie containing refresh token."""
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=raw_token,
        httponly=True,
        samesite="lax",
        secure=settings.is_production,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        path=REFRESH_COOKIE_PATH,
    )


def clear_refresh_cookie(response: Response) -> None:
    """Clear refresh token HttpOnly cookie."""
    response.delete_cookie(
        key=REFRESH_COOKIE_NAME,
        path=REFRESH_COOKIE_PATH,
        httponly=True,
        samesite="lax",
        secure=settings.is_production,
    )


@auth_router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account",
)
def register(
    payload: UserRegister,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> TokenResponse:
    """Register a new user, issue initial access and refresh tokens."""
    client_ip = get_client_ip(request)
    register_limiter.check(client_ip)

    validate_password_strength(payload.password)

    # Check for existing account
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise ConflictError("An account with this email address already exists")

    new_user = User(
        email=payload.email,
        full_name=payload.full_name,
        hashed_password=hash_password(payload.password),
        is_active=True,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    audit_service.record_event(
        action="auth.register",
        resource_type="user",
        actor_type="user",
        actor_id=str(new_user.id),
        resource_id=str(new_user.id),
        metadata={"email": new_user.email, "ip": client_ip},
    )

    # Generate tokens
    access_token = create_access_token(subject=str(new_user.id))
    raw_refresh, expire_dt = create_refresh_token(subject=str(new_user.id))

    refresh_entity = RefreshToken(
        user_id=new_user.id,
        token_hash=hash_token(raw_refresh),
        expires_at=expire_dt,
    )
    db.add(refresh_entity)
    db.commit()

    set_refresh_cookie(response, raw_refresh)

    return TokenResponse(
        access_token=access_token,
        refresh_token=raw_refresh,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@auth_router.post(
    "/login",
    response_model=TokenResponse,
    summary="Authenticate user and issue tokens",
)
def login(
    payload: UserLogin,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> TokenResponse:
    """Validate credentials and return fresh access/refresh tokens."""
    client_ip = get_client_ip(request)
    login_limiter.check(client_ip)

    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        audit_service.record_event(
            action="auth.login_failed",
            resource_type="user",
            actor_type="anonymous",
            actor_id=payload.email,
            metadata={"ip": client_ip, "reason": "invalid_credentials"},
        )
        raise UnauthorizedError("Invalid email or password")

    if not user.is_active:
        audit_service.record_event(
            action="auth.login_failed",
            resource_type="user",
            actor_type="user",
            actor_id=str(user.id),
            metadata={"ip": client_ip, "reason": "inactive_account"},
        )
        raise UnauthorizedError("Invalid email or password")

    user.last_login_at = datetime.now(timezone.utc)
    db.commit()

    access_token = create_access_token(subject=str(user.id))
    raw_refresh, expire_dt = create_refresh_token(subject=str(user.id))

    refresh_entity = RefreshToken(
        user_id=user.id,
        token_hash=hash_token(raw_refresh),
        expires_at=expire_dt,
    )
    db.add(refresh_entity)
    db.commit()

    set_refresh_cookie(response, raw_refresh)

    audit_service.record_event(
        action="auth.login",
        resource_type="user",
        actor_type="user",
        actor_id=str(user.id),
        resource_id=str(user.id),
        metadata={"ip": client_ip},
    )

    return TokenResponse(
        access_token=access_token,
        refresh_token=raw_refresh,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@auth_router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Rotate refresh token and issue new access token",
)
def refresh_token_endpoint(
    request: Request,
    response: Response,
    payload: Optional[RefreshTokenRequest] = None,
    db: Session = Depends(get_db),
) -> TokenResponse:
    """Rotate an active refresh token, revoking the old token."""
    raw_token: Optional[str] = None
    if payload and payload.refresh_token:
        raw_token = payload.refresh_token
    elif request.cookies.get(REFRESH_COOKIE_NAME):
        raw_token = request.cookies.get(REFRESH_COOKIE_NAME)

    if not raw_token:
        raise UnauthorizedError("Refresh token was not provided")

    decoded = decode_token(raw_token, expected_type="refresh")
    user_id_str = decoded.get("sub")
    if not user_id_str:
        raise UnauthorizedError("Invalid refresh token")

    token_hash = hash_token(raw_token)
    token_record = db.query(RefreshToken).filter(RefreshToken.token_hash == token_hash).first()

    if not token_record or not token_record.is_valid:
        # Potential reuse / revoked token usage
        audit_service.record_event(
            action="auth.token_revocation_alert",
            resource_type="refresh_token",
            actor_type="anonymous",
            actor_id=user_id_str,
            metadata={"token_hash": token_hash[:8] + "..."},
        )
        raise UnauthorizedError("Refresh token is invalid or expired")

    # Revoke current token (rotation)
    token_record.revoked_at = datetime.now(timezone.utc)

    user = db.query(User).filter(User.id == uuid.UUID(user_id_str)).first()
    if not user or not user.is_active:
        db.commit()
        raise UnauthorizedError("User account is inactive or not found")

    new_access_token = create_access_token(subject=str(user.id))
    new_raw_refresh, expire_dt = create_refresh_token(subject=str(user.id))

    new_token_record = RefreshToken(
        user_id=user.id,
        token_hash=hash_token(new_raw_refresh),
        expires_at=expire_dt,
    )
    db.add(new_token_record)
    db.commit()

    set_refresh_cookie(response, new_raw_refresh)

    audit_service.record_event(
        action="auth.token_refresh",
        resource_type="user",
        actor_type="user",
        actor_id=str(user.id),
        resource_id=str(user.id),
    )

    return TokenResponse(
        access_token=new_access_token,
        refresh_token=new_raw_refresh,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@auth_router.post(
    "/logout",
    response_model=MessageResponse,
    summary="Revoke active refresh token and clear session",
)
def logout(
    request: Request,
    response: Response,
    payload: Optional[RefreshTokenRequest] = None,
    db: Session = Depends(get_db),
) -> MessageResponse:
    """Revoke refresh token and clear authentication cookie."""
    raw_token: Optional[str] = None
    if payload and payload.refresh_token:
        raw_token = payload.refresh_token
    elif request.cookies.get(REFRESH_COOKIE_NAME):
        raw_token = request.cookies.get(REFRESH_COOKIE_NAME)

    if raw_token:
        token_hash = hash_token(raw_token)
        token_record = db.query(RefreshToken).filter(RefreshToken.token_hash == token_hash).first()
        if token_record and token_record.revoked_at is None:
            token_record.revoked_at = datetime.now(timezone.utc)
            db.commit()
            audit_service.record_event(
                action="auth.logout",
                resource_type="user",
                actor_type="user",
                actor_id=str(token_record.user_id),
                resource_id=str(token_record.id),
            )

    clear_refresh_cookie(response)
    return MessageResponse(message="Successfully logged out")
