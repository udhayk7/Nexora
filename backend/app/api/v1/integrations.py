import uuid
from typing import Any

from fastapi import APIRouter, Depends, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.oauth_state import generate_oauth_state, verify_oauth_state
from app.models.assistant import GmailConnection
from app.models.user import User
from app.schemas.ai_usage import AIUsageSummaryResponse
from app.schemas.assistant import (
    GmailConnectionStatusResponse,
    GoogleAuthUrlResponse,
    GoogleOAuthCallbackRequest,
)
from app.services.ai.cost_manager import AICostManager
from app.services.gmail_service import GmailService
from app.services.integration_health_service import IntegrationHealthService

router = APIRouter(prefix="/integrations", tags=["Integrations & Health"])
google_router = APIRouter(prefix="/google", tags=["Google & Gmail Integration"])


# ---------------------------------------------------------------------------
# Google & Gmail OAuth Endpoints (under /api/v1/integrations/google/*)
# ---------------------------------------------------------------------------


@google_router.get(
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


@google_router.get(
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


@google_router.post(
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


@google_router.get(
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


@google_router.post(
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


# Mount Google subrouter onto main integrations router
router.include_router(google_router)


# ---------------------------------------------------------------------------
# Centralized Integration Health & Diagnostic Endpoints (/api/v1/integrations/*)
# ---------------------------------------------------------------------------


@router.get(
    "/health",
    summary="Get comprehensive status across all external integrations",
)
def get_integrations_health(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Inspects status of OpenAI, Gemini, PostgreSQL, Redis, Celery, Gmail, and Job feeds."""
    return IntegrationHealthService.check_all(db=db, user=current_user)


@router.post(
    "/test/{service}",
    summary="Safely test connection to a specific integration service",
)
def test_integration_service(
    service: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Performs an isolated diagnostic check for a service without exposing secrets."""
    return IntegrationHealthService.test_service(service_name=service, db=db, user=current_user)


@router.get(
    "/ai-usage",
    response_model=AIUsageSummaryResponse,
    summary="Get AI usage monitoring, token consumption, and estimated spending",
)
def get_ai_usage_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AIUsageSummaryResponse:
    """Aggregates AI consumption metrics, model breakdowns, and budget limits."""
    return AICostManager.get_usage_summary(db=db)


@router.get(
    "/job-sources",
    summary="Get operational and rate-limit status for all job discovery adapters",
)
def get_job_sources_status(
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Returns technical capability, rate limiting, and verification metadata for job sources."""
    return IntegrationHealthService._check_job_sources()
