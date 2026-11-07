import base64
import contextlib
import email.utils
import urllib.parse
from datetime import datetime, timedelta, timezone
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Optional

import httpx
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import AppError, BadRequestError, ForbiddenError
from app.core.logging import logger
from app.core.token_encryption import decrypt_token, encrypt_token
from app.models.assistant import GmailConnection
from app.models.user import User

GOOGLE_AUTH_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_ENDPOINT = "https://www.googleapis.com/oauth2/v2/userinfo"
GOOGLE_REVOKE_ENDPOINT = "https://oauth2.googleapis.com/revoke"
GMAIL_API_BASE = "https://gmail.googleapis.com/gmail/v1/users/me"


class GmailServiceError(AppError):
    """Exception raised during Gmail API or OAuth operations."""

    def __init__(self, message: str = "Gmail service error", status_code: int = 502) -> None:
        super().__init__(message=message, code="GMAIL_SERVICE_ERROR", status_code=status_code)


class GmailService:
    """Manages Google OAuth 2.0 authorization, token refresh, draft creation, and message send."""

    @classmethod
    def get_authorization_url(cls, state: str) -> str:
        """Construct the official Google OAuth 2.0 consent URL with minimal requested scopes."""
        if not settings.GOOGLE_CLIENT_ID:
            raise BadRequestError(
                "Google OAuth client ID is not configured. "
                "Please configure GOOGLE_CLIENT_ID in the application environment."
            )

        params = {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "redirect_uri": settings.GOOGLE_REDIRECT_URI,
            "response_type": "code",
            "scope": " ".join(settings.GMAIL_SCOPES),
            "access_type": "offline",
            "prompt": "consent",  # Ensures refresh_token is provided
            "state": state,
        }
        return f"{GOOGLE_AUTH_ENDPOINT}?{urllib.parse.urlencode(params)}"

    @classmethod
    def exchange_code_for_tokens(
        cls,
        db: Session,
        user: User,
        code: str,
    ) -> GmailConnection:
        """Exchange authorization code for tokens, verify identity, and store encrypted tokens."""
        if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
            raise BadRequestError("Google OAuth credentials are not configured in environment.")

        token_payload = {
            "code": code,
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "redirect_uri": settings.GOOGLE_REDIRECT_URI,
            "grant_type": "authorization_code",
        }

        with httpx.Client(timeout=15.0) as client:
            resp = client.post(GOOGLE_TOKEN_ENDPOINT, data=token_payload)
            if resp.status_code != 200:
                logger.error("Google token exchange failed: %s %s", resp.status_code, resp.text)
                raise GmailServiceError("Failed to exchange authorization code with Google OAuth")

            tokens = resp.json()
            access_token = tokens.get("access_token")
            refresh_token = tokens.get("refresh_token")
            expires_in = tokens.get("expires_in", 3600)

            # Retrieve user's Google email
            userinfo_resp = client.get(
                GOOGLE_USERINFO_ENDPOINT,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            if userinfo_resp.status_code != 200:
                raise GmailServiceError("Failed to retrieve connected Google account profile")

            userinfo = userinfo_resp.json()
            google_email = userinfo.get("email")
            if not google_email:
                raise GmailServiceError("Google account has no verified email address")

        now = datetime.now(timezone.utc)
        token_expiry = now + timedelta(seconds=expires_in)

        # Encrypt tokens for storage at rest
        enc_refresh = encrypt_token(refresh_token) if refresh_token else None
        enc_access = encrypt_token(access_token)

        conn = db.query(GmailConnection).filter(GmailConnection.user_id == user.id).first()

        if conn:
            conn.email = google_email
            conn.encrypted_access_token = enc_access
            if enc_refresh:
                conn.encrypted_refresh_token = enc_refresh
            conn.token_expiry = token_expiry
            conn.scopes = settings.GMAIL_SCOPES
            conn.is_active = True
            conn.connected_at = now
            conn.last_used_at = now
        else:
            conn = GmailConnection(
                user_id=user.id,
                email=google_email,
                encrypted_refresh_token=enc_refresh,
                encrypted_access_token=enc_access,
                token_expiry=token_expiry,
                scopes=settings.GMAIL_SCOPES,
                is_active=True,
                connected_at=now,
                last_used_at=now,
            )
            db.add(conn)

        db.commit()
        db.refresh(conn)
        return conn

    @classmethod
    def get_valid_access_token(cls, db: Session, user: User) -> tuple[str, GmailConnection]:
        """Retrieve a valid access token for the user, refreshing it if expired."""
        conn = (
            db.query(GmailConnection)
            .filter(GmailConnection.user_id == user.id, GmailConnection.is_active.is_(True))
            .first()
        )
        if not conn or not conn.encrypted_access_token:
            raise BadRequestError(
                "No connected Gmail account found. Please connect your Gmail account first."
            )

        now = datetime.now(timezone.utc)
        # Check if expired or within 2 minutes of expiry
        is_expired = conn.token_expiry and (conn.token_expiry - now).total_seconds() < 120

        if not is_expired:
            access_token = decrypt_token(conn.encrypted_access_token)
            if access_token:
                return access_token, conn

        # Needs refresh
        refresh_token = decrypt_token(conn.encrypted_refresh_token)
        if not refresh_token:
            conn.is_active = False
            db.commit()
            raise BadRequestError(
                "Gmail connection expired and cannot be refreshed. Please reconnect your account."
            )

        new_access_token, new_expiry = cls._refresh_token(refresh_token)
        conn.encrypted_access_token = encrypt_token(new_access_token)
        conn.token_expiry = new_expiry
        conn.last_used_at = now
        db.commit()
        db.refresh(conn)

        return new_access_token, conn

    @classmethod
    def _refresh_token(cls, refresh_token: str) -> tuple[str, datetime]:
        """Perform token refresh against Google OAuth token endpoint."""
        if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
            raise BadRequestError("Google OAuth credentials are not configured in environment.")

        refresh_payload = {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        }

        with httpx.Client(timeout=15.0) as client:
            resp = client.post(GOOGLE_TOKEN_ENDPOINT, data=refresh_payload)
            if resp.status_code != 200:
                logger.error("Token refresh failed: %s %s", resp.status_code, resp.text)
                raise GmailServiceError(
                    "Failed to refresh Gmail access token. Account re-authorization required."
                )

            data = resp.json()
            new_token = data.get("access_token")
            expires_in = data.get("expires_in", 3600)
            expiry = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
            return new_token, expiry

    @classmethod
    def disconnect_account(cls, db: Session, user: User) -> None:
        """Disconnect connected Gmail account and attempt upstream revocation."""
        conn = db.query(GmailConnection).filter(GmailConnection.user_id == user.id).first()
        if not conn:
            return

        # Attempt revocation with Google
        token_to_revoke = None
        with contextlib.suppress(Exception):
            token_to_revoke = decrypt_token(conn.encrypted_refresh_token) or decrypt_token(
                conn.encrypted_access_token
            )

        if token_to_revoke:
            try:
                with httpx.Client(timeout=10.0) as client:
                    client.post(GOOGLE_REVOKE_ENDPOINT, params={"token": token_to_revoke})
            except Exception as exc:
                logger.warning("Upstream Google token revocation returned error: %s", exc)

        conn.is_active = False
        conn.encrypted_access_token = None
        conn.encrypted_refresh_token = None
        db.commit()

    @classmethod
    def create_draft(
        cls,
        db: Session,
        user: User,
        recipient_email: str,
        subject: str,
        body: str,
        attachments: Optional[
            list[tuple[str, bytes, str]]
        ] = None,  # [(filename, bytes, mime_type)]
    ) -> dict[str, Any]:
        """Create a draft in the user's connected Gmail account via the official Gmail API."""
        if not recipient_email or "@" not in recipient_email:
            raise BadRequestError("A valid explicit recipient email address is required.")

        access_token, conn = cls.get_valid_access_token(db, user)

        raw_b64 = cls._build_rfc2822_message(
            sender=conn.email,
            recipient=recipient_email,
            subject=subject,
            body=body,
            attachments=attachments or [],
        )

        with httpx.Client(timeout=20.0) as client:
            resp = client.post(
                f"{GMAIL_API_BASE}/drafts",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                },
                json={"message": {"raw": raw_b64}},
            )
            if resp.status_code not in (200, 201):
                logger.error("Gmail create draft failed: %s %s", resp.status_code, resp.text)
                raise GmailServiceError(
                    f"Gmail draft creation failed with status {resp.status_code}"
                )

            data = resp.json()
            draft_id = data.get("id")
            message = data.get("message", {})
            message_id = message.get("id")
            thread_id = message.get("threadId")

            conn.last_used_at = datetime.now(timezone.utc)
            db.commit()

            return {
                "draft_id": draft_id,
                "message_id": message_id,
                "thread_id": thread_id,
                "connected_email": conn.email,
            }

    @classmethod
    def send_email(
        cls,
        db: Session,
        user: User,
        recipient_email: str,
        subject: str,
        body: str,
        confirm_send: bool,
        attachments: Optional[list[tuple[str, bytes, str]]] = None,
    ) -> dict[str, Any]:
        """Send an approved email through the connected Gmail account after confirmation."""
        if not confirm_send:
            raise ForbiddenError(
                "Explicit user confirmation is strictly required immediately before sending email."
            )
        if not recipient_email or "@" not in recipient_email:
            raise BadRequestError(
                "A valid explicit recipient email address is required. "
                "Nexora never sends to guessed emails."
            )

        access_token, conn = cls.get_valid_access_token(db, user)

        raw_b64 = cls._build_rfc2822_message(
            sender=conn.email,
            recipient=recipient_email,
            subject=subject,
            body=body,
            attachments=attachments or [],
        )

        with httpx.Client(timeout=25.0) as client:
            resp = client.post(
                f"{GMAIL_API_BASE}/messages/send",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                },
                json={"raw": raw_b64},
            )
            if resp.status_code not in (200, 201):
                logger.error("Gmail send failed: %s %s", resp.status_code, resp.text)
                err_text = resp.text[:150]
                raise GmailServiceError(
                    f"Gmail send request rejected by Google ({resp.status_code}): {err_text}"
                )

            data = resp.json()
            message_id = data.get("id")
            thread_id = data.get("threadId")

            conn.last_used_at = datetime.now(timezone.utc)
            db.commit()

            return {
                "message_id": message_id,
                "thread_id": thread_id,
                "sent_at": datetime.now(timezone.utc).isoformat(),
                "connected_email": conn.email,
            }

    @classmethod
    def _build_rfc2822_message(
        cls,
        sender: str,
        recipient: str,
        subject: str,
        body: str,
        attachments: list[tuple[str, bytes, str]],
    ) -> str:
        """Build RFC 2822 MIME multipart message and return base64url-encoded string."""
        message = MIMEMultipart("mixed")
        message["From"] = sender
        message["To"] = recipient
        message["Subject"] = subject
        message["Date"] = email.utils.formatdate(localtime=True)

        # Plain text & HTML alternative
        alt_part = MIMEMultipart("alternative")
        text_part = MIMEText(body, "plain", "utf-8")
        alt_part.attach(text_part)

        # Basic HTML format
        html_body = body.replace("\n", "<br/>")
        html_part = MIMEText(f"<html><body><p>{html_body}</p></body></html>", "html", "utf-8")
        alt_part.attach(html_part)
        message.attach(alt_part)

        # Attachments
        total_size = 0
        limit_mb = settings.MAX_UPLOAD_SIZE_BYTES // (1024 * 1024)
        for filename, content, _mime_type in attachments:
            total_size += len(content)
            if total_size > settings.MAX_UPLOAD_SIZE_BYTES:
                raise BadRequestError(
                    f"Combined attachment size exceeds maximum limit of {limit_mb}MB."
                )

            part = MIMEApplication(content, Name=filename)
            part["Content-Disposition"] = f'attachment; filename="{filename}"'
            message.attach(part)

        raw_bytes = message.as_bytes()
        return base64.urlsafe_b64encode(raw_bytes).decode("utf-8")
