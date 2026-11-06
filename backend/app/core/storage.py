import os
import re
import uuid
from pathlib import Path
from typing import Optional, Protocol

from app.core.config import settings
from app.core.errors import AppError
from app.core.logging import logger


class StorageError(AppError):
    """Storage operation exception."""

    def __init__(self, message: str = "Storage operation failed") -> None:
        super().__init__(message=message, code="STORAGE_ERROR", status_code=500)


def sanitize_filename(filename: str) -> str:
    """Sanitize filename to prevent directory traversal and remove unsafe characters."""
    # Strip any directory path components
    basename = os.path.basename(filename)
    # Replace any non-alphanumeric chars (except . - _) with an underscore
    sanitized = re.sub(r"[^\w\.-]", "_", basename)
    # Avoid hidden files or double dots
    sanitized = sanitized.lstrip(".")
    if not sanitized:
        sanitized = "unnamed_file"
    return sanitized[:100]


class StorageService(Protocol):
    """Protocol for file storage backends."""

    def save_file(
        self,
        user_id: uuid.UUID,
        resume_id: uuid.UUID,
        version_id: uuid.UUID,
        filename: str,
        content: bytes,
    ) -> str:
        """Store raw file content securely and return relative storage path."""
        ...

    def get_file(self, storage_path: str) -> bytes:
        """Retrieve file bytes by relative storage path."""
        ...

    def delete_file(self, storage_path: str) -> bool:
        """Delete a single stored file."""
        ...

    def delete_resume_directory(self, user_id: uuid.UUID, resume_id: uuid.UUID) -> bool:
        """Delete all stored versions and directory for a specific resume."""
        ...


class LocalStorageService:
    """Local filesystem storage implementation with path-traversal protection."""

    def __init__(self, base_path: Optional[str] = None) -> None:
        self.base_dir = Path(base_path or settings.STORAGE_LOCAL_PATH).resolve()
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _resolve_safe_path(self, relative_path: str) -> Path:
        """Resolve path and verify it stays inside base storage directory."""
        resolved = (self.base_dir / relative_path).resolve()
        try:
            resolved.relative_to(self.base_dir)
        except ValueError:
            logger.error(f"Potential path traversal attempted: {relative_path}")
            raise StorageError("Invalid storage path") from None
        return resolved

    def save_file(
        self,
        user_id: uuid.UUID,
        resume_id: uuid.UUID,
        version_id: uuid.UUID,
        filename: str,
        content: bytes,
    ) -> str:
        safe_name = sanitize_filename(filename)
        rel_dir = Path(str(user_id)) / str(resume_id)
        file_name = f"{version_id}_{safe_name}"
        rel_path = str(rel_dir / file_name)

        target_file = self._resolve_safe_path(rel_path)
        target_file.parent.mkdir(parents=True, exist_ok=True)

        try:
            target_file.write_bytes(content)
            logger.info(f"File saved to storage: {rel_path} ({len(content)} bytes)")
            return rel_path
        except Exception as exc:
            logger.error(f"Failed to write file {target_file}: {exc}")
            raise StorageError("Failed to persist file") from exc

    def get_file(self, storage_path: str) -> bytes:
        target_file = self._resolve_safe_path(storage_path)
        if not target_file.exists() or not target_file.is_file():
            logger.warning(f"File not found in storage: {storage_path}")
            raise FileNotFoundError(f"Storage file not found: {storage_path}")

        try:
            return target_file.read_bytes()
        except Exception as exc:
            logger.error(f"Failed to read file {target_file}: {exc}")
            raise StorageError("Failed to read file from storage") from exc

    def delete_file(self, storage_path: str) -> bool:
        target_file = self._resolve_safe_path(storage_path)
        if target_file.exists() and target_file.is_file():
            try:
                target_file.unlink()
                logger.info(f"Deleted storage file: {storage_path}")
                return True
            except Exception as exc:
                logger.error(f"Failed to delete file {target_file}: {exc}")
                raise StorageError("Failed to delete file") from exc
        return False

    def delete_resume_directory(self, user_id: uuid.UUID, resume_id: uuid.UUID) -> bool:
        rel_dir = Path(str(user_id)) / str(resume_id)
        target_dir = self._resolve_safe_path(str(rel_dir))
        if target_dir.exists() and target_dir.is_dir():
            try:
                import shutil

                shutil.rmtree(target_dir)
                logger.info(f"Deleted resume storage directory: {rel_dir}")
                return True
            except Exception as exc:
                logger.error(f"Failed to delete directory {target_dir}: {exc}")
                raise StorageError("Failed to delete resume files") from exc
        return False


# Global default storage service instance
storage_service = LocalStorageService()
