import os
import re
import hashlib
import uuid
from typing import Tuple, Optional
from backend.app.core.config import settings


class StorageError(Exception):
    """Base exception for storage errors."""
    pass


class InvalidFileError(StorageError):
    """File format is unsupported, malformed, or invalid."""
    pass


class FileTooLargeError(StorageError):
    """File exceeds allowed upload size."""
    pass


def sanitize_filename(filename: Optional[str]) -> str:
    """
    Sanitize an uploaded filename to prevent directory traversal and injection.
    Strips path separators, control characters, and limits length.
    """
    if not filename or not filename.strip():
        return "unnamed_evidence"
    
    # Strip directory paths
    base = os.path.basename(filename)
    # Remove null bytes and control chars
    base = re.sub(r'[\x00-\x1f\x7f]', '', base)
    # Remove Windows/Unix path separators that might remain
    base = base.replace("/", "").replace("\\", "").strip()
    
    # Truncate if excessively long
    if len(base) > 200:
        name, ext = os.path.splitext(base)
        base = name[: 200 - len(ext)] + ext
        
    return base or "unnamed_evidence"


def inspect_content_mime_type(data: bytes, declared_type: Optional[str] = None) -> str:
    """
    Inspect the binary content header (magic bytes) to determine and verify MIME type.
    Rejects disguised files and unsupported formats.
    """
    if not data or len(data) == 0:
        raise InvalidFileError("File is empty (0 bytes).")

    # PNG: 89 50 4E 47 0D 0A 1A 0A
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"

    # JPEG: FF D8 FF
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"

    # PDF: %PDF-
    if data.startswith(b"%PDF-"):
        return "application/pdf"

    # Text / UTF-8 check
    try:
        data.decode("utf-8")
        # Ensure it doesn't contain null bytes (which indicate binary data)
        if b"\x00" not in data:
            return "text/plain"
    except UnicodeDecodeError:
        pass

    raise InvalidFileError(
        f"Unsupported or invalid file format. Supported types: PNG, JPEG, PDF, and UTF-8 plain text."
    )


class LocalEvidenceStorage:
    """
    Storage abstraction managing private evidence files on disk.
    Files are stored under random UUID keys outside publicly accessible web roots.
    """

    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = base_dir or settings.STORAGE_DIR
        os.makedirs(self.base_dir, exist_ok=True)

    def save_file(self, data: bytes, evidence_id: str) -> Tuple[str, str, int]:
        """
        Save file content to private storage.
        
        Args:
            data: Raw file bytes
            evidence_id: Unique UUID string for evidence
            
        Returns:
            Tuple of (storage_key, sha256_hex, size_bytes)
        """
        size_bytes = len(data)
        if size_bytes > settings.MAX_UPLOAD_SIZE_BYTES:
            raise FileTooLargeError(
                f"File size ({size_bytes} bytes) exceeds limit of {settings.MAX_UPLOAD_SIZE_BYTES} bytes."
            )

        sha256_hash = hashlib.sha256(data).hexdigest()
        storage_key = f"{evidence_id}.bin"
        file_path = os.path.join(self.base_dir, storage_key)

        try:
            with open(file_path, "wb") as f:
                f.write(data)
        except Exception as e:
            raise StorageError(f"Failed to write evidence to disk: {e}") from e

        return storage_key, sha256_hash, size_bytes

    def get_file_path(self, storage_key: str) -> str:
        """Get absolute path for a private storage key, ensuring no directory escape."""
        safe_key = os.path.basename(storage_key)
        full_path = os.path.abspath(os.path.join(self.base_dir, safe_key))
        if not full_path.startswith(os.path.abspath(self.base_dir)):
            raise StorageError("Path traversal attempt detected.")
        if not os.path.exists(full_path):
            raise StorageError(f"Evidence file {storage_key} not found on disk.")
        return full_path

    def read_file(self, storage_key: str) -> bytes:
        """Read evidence bytes from storage."""
        path = self.get_file_path(storage_key)
        with open(path, "rb") as f:
            return f.read()

    def delete_file(self, storage_key: str) -> bool:
        """Safely delete file on rollback."""
        try:
            path = self.get_file_path(storage_key)
            if os.path.exists(path):
                os.remove(path)
                return True
        except Exception:
            pass
        return False


storage_service = LocalEvidenceStorage()
