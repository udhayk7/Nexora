import base64
import hashlib
import hmac
import json
import time
import uuid
from typing import Any

from app.core.config import settings
from app.core.errors import BadRequestError


def generate_oauth_state(user_id: uuid.UUID, action: str = "gmail_connect") -> str:
    """Generate a tamper-proof, timestamped OAuth state string for CSRF mitigation."""
    payload = {
        "uid": str(user_id),
        "act": action,
        "ts": int(time.time()),
        "nonce": uuid.uuid4().hex[:12],
    }
    raw_payload = json.dumps(payload, separators=(",", ":"))
    payload_b64 = base64.urlsafe_b64encode(raw_payload.encode()).decode().rstrip("=")

    sig = hmac.new(
        settings.SECRET_KEY.encode("utf-8"),
        payload_b64.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    return f"{payload_b64}.{sig}"


def verify_oauth_state(
    state: str,
    expected_user_id: uuid.UUID,
    expected_action: str = "gmail_connect",
    max_age_seconds: int = 900,  # 15 minutes
) -> dict[str, Any]:
    """Validate OAuth state parameter signature, action, expiration, and user identity."""
    if not state or "." not in state:
        raise BadRequestError("Invalid OAuth state format")

    parts = state.split(".", 1)
    if len(parts) != 2:
        raise BadRequestError("Malformed OAuth state token")

    payload_b64, signature = parts

    # Recompute HMAC signature
    expected_sig = hmac.new(
        settings.SECRET_KEY.encode("utf-8"),
        payload_b64.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(signature, expected_sig):
        raise BadRequestError("OAuth state verification failed: invalid signature")

    # Add padding back if necessary
    rem = len(payload_b64) % 4
    padded_b64 = payload_b64 + ("=" * (4 - rem) if rem else "")

    try:
        raw_json = base64.urlsafe_b64decode(padded_b64.encode()).decode("utf-8")
        data = json.loads(raw_json)
    except Exception as exc:
        raise BadRequestError("Corrupt OAuth state payload") from exc

    # Validate user identity
    if data.get("uid") != str(expected_user_id):
        raise BadRequestError("OAuth state user mismatch")

    # Validate action
    if data.get("act") != expected_action:
        raise BadRequestError("OAuth state action mismatch")

    # Validate timestamp expiration
    ts = data.get("ts", 0)
    now = int(time.time())
    if now - ts > max_age_seconds:
        raise BadRequestError("OAuth state has expired. Please initiate connection again.")
    if ts > now + 60:
        raise BadRequestError("OAuth state timestamp in future")

    return dict(data)
