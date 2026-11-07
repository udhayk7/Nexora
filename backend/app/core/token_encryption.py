import base64
import hashlib
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings
from app.core.errors import AppError


class TokenEncryptionError(AppError):
    """Exception raised when OAuth token encryption or decryption fails."""

    def __init__(self, message: str = "Token encryption error") -> None:
        super().__init__(message=message, code="TOKEN_ENCRYPTION_ERROR", status_code=500)


def _get_fernet_key() -> bytes:
    """Derive a safe 32-byte urlsafe base64-encoded key for Fernet.

    Uses GMAIL_TOKEN_ENCRYPTION_KEY if provided; otherwise derives from SECRET_KEY.
    """
    raw_key = settings.GMAIL_TOKEN_ENCRYPTION_KEY or settings.SECRET_KEY
    if not raw_key:
        raise TokenEncryptionError("Missing encryption key configuration")

    # If it is already a valid 32-byte base64 Fernet key, use it
    if len(raw_key) == 44:
        try:
            base64.urlsafe_b64decode(raw_key.encode())
            return raw_key.encode()
        except Exception:
            pass

    # Deterministically derive 32 bytes using SHA-256 and urlsafe base64-encode
    hashed = hashlib.sha256(raw_key.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(hashed)


def encrypt_token(plain_token: Optional[str]) -> Optional[str]:
    """Encrypt an OAuth access or refresh token string for storage at rest."""
    if not plain_token:
        return None
    try:
        f = Fernet(_get_fernet_key())
        encrypted_bytes = f.encrypt(plain_token.encode("utf-8"))
        return encrypted_bytes.decode("utf-8")
    except Exception as exc:
        raise TokenEncryptionError("Failed to encrypt OAuth token") from exc


def decrypt_token(encrypted_token: Optional[str]) -> Optional[str]:
    """Decrypt an encrypted OAuth token from storage.

    Never logs or exposes the decrypted token.
    """
    if not encrypted_token:
        return None
    try:
        f = Fernet(_get_fernet_key())
        decrypted_bytes = f.decrypt(encrypted_token.encode("utf-8"))
        return decrypted_bytes.decode("utf-8")
    except InvalidToken as exc:
        raise TokenEncryptionError("Decryption failed: invalid or corrupt token") from exc
    except Exception as exc:
        raise TokenEncryptionError("Failed to decrypt OAuth token") from exc
