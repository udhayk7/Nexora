import uuid

from fastapi import APIRouter, Depends, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.oauth_state import generate_oauth_state, verify_oauth_state
from app.models.assistant import GmailConnection
from app.models.user import User
from app.schemas.assistant import (
    GmailConnectionStatusResponse,
    GoogleAuthUrlResponse,
    GoogleOAuthCallbackRequest,
)
from app.services.gmail_service import GmailService

router = APIRouter(prefix="/integrations/google", tags=["Google & Gmail Integration"])


@router.get(
    "/auth-url",
    response_model=GoogleAuthUrlResponse,
    summary="Generate official Google OAuth 2.0 authorization URL",
)
def get_google_auth_url(
    current_user: User = Depends(get_current_user),
) -> GoogleAuthUrlResponse:
    """Generate a tamper-proof state token and return Google's OAuth consent URL."""
    state = generate_oauth_state(user_id=current_user.id, action="gmail_connect")
    auth_url = GmailService.get_authorization_url(state=state)
    return GoogleAuthUrlResponse(authorization_url=auth_url, state=state)


@router.get(
    "/callback",
    summary="Handle Google OAuth 2.0 redirect callback",
)
def google_oauth_redirect_callback(
    code: str = Query(...),
    state: str = Query(...),
    db: Session = Depends(get_db),
) -> RedirectResponse:
    """Browser redirect callback from Google OAuth.

    Validates state token to identify user, completes exchange, and redirects to dashboard.
    """
    # Verify state without current_user dependency since this is a top-level browser redirect
    # Verify signature first to extract user id
    parts = state.split(".", 1)
    if len(parts) != 2:
        return RedirectResponse(url="/dashboard/application-assistant?error=invalid_oauth_state")

    try:
        import base64
        import json

        rem = len(parts[0]) % 4
        padded = parts[0] + ("=" * (4 - rem) if rem else "")
        data = json.loads(base64.urlsafe_b64decode(padded.encode()).decode("utf-8"))
        user_id = uuid.UUID(data["uid"])
        verify_oauth_state(state=state, expected_user_id=user_id, expected_action="gmail_connect")
    except Exception:
        return RedirectResponse(
            url="/dashboard/application-assistant?error=state_verification_failed"
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return RedirectResponse(url="/dashboard/application-assistant?error=user_not_found")

    try:
        GmailService.exchange_code_for_tokens(db=db, user=user, code=code)
        return RedirectResponse(url="/dashboard/application-assistant?connected=true")
    except Exception as exc:
        return RedirectResponse(
            url=f"/dashboard/application-assistant?error=exchange_failed&details={str(exc)[:100]}"
        )


@router.post(
    "/callback",
    response_model=GmailConnectionStatusResponse,
    summary="Exchange Google OAuth code for tokens (SPA callback)",
)
def google_oauth_spa_callback(
    data: GoogleOAuthCallbackRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> GmailConnectionStatusResponse:
    """Exchange authorization code for tokens, verifying that state matches current user."""
    verify_oauth_state(
        state=data.state, expected_user_id=current_user.id, expected_action="gmail_connect"
    )
    conn = GmailService.exchange_code_for_tokens(db=db, user=current_user, code=data.code)
    return GmailConnectionStatusResponse(
        is_connected=conn.is_active,
        email=conn.email,
        scopes=conn.scopes,
        connected_at=conn.connected_at,
        is_token_valid=True,
    )


@router.get(
    "/status",
    response_model=GmailConnectionStatusResponse,
    summary="Get connected Gmail account status",
)
def get_gmail_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> GmailConnectionStatusResponse:
    """Retrieve public connection status for current user. Never reveals tokens."""
    conn = db.query(GmailConnection).filter(GmailConnection.user_id == current_user.id).first()
    if not conn or not conn.is_active:
        return GmailConnectionStatusResponse(
            is_connected=False,
            email=None,
            scopes=[],
            connected_at=None,
            is_token_valid=False,
        )

    return GmailConnectionStatusResponse(
        is_connected=True,
        email=conn.email,
        scopes=conn.scopes,
        connected_at=conn.connected_at,
        is_token_valid=bool(conn.encrypted_access_token or conn.encrypted_refresh_token),
    )


@router.post(
    "/disconnect",
    summary="Disconnect Gmail account and revoke access",
)
def disconnect_gmail_account(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    """Revoke tokens and disconnect user's Gmail account."""
    GmailService.disconnect_account(db=db, user=current_user)
    return {"message": "Gmail account disconnected successfully"}
