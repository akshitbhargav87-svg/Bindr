"""
Evidence Storage Service and Invariants for Bindr.

Storage & Evidence Preservation Invariants:
-------------------------------------------
1. Original Evidence Immutability:
   Original evidence bytes uploaded by the user are immutable. They are never modified,
   re-encoded, compressed, or overwritten after ingestion.

2. Tamper Detection & SHA-256 Verification:
   A SHA-256 cryptographic digest is computed immediately upon ingestion and persisted
   in the Evidence database model. This ensures verifiable integrity across the lifetime
   of the case and allows independent verification of stored bytes.

3. Private Storage Isolation:
   Evidence files are saved under server-generated UUID keys (`<evidence_id>.bin`),
   never user-provided filenames. Files are stored strictly outside public web roots
   with restrictive file descriptors (`0o600`) locally, or in private Google Cloud Storage
   buckets with uniform bucket-level access and public access prevention enabled.

4. Backend-Mediated Access Only:
   Neither public object URLs nor signed URLs are ever generated or returned. All access
   must pass through authenticated backend endpoints that verify case ownership and emit
   security headers (`Cache-Control: private, no-store`, `X-Content-Type-Options: nosniff`).

5. Best-Effort Rollback Compensation:
   The upload endpoint requests deletion after a known pre-commit flush failure. It
   preserves the object after an uncertain commit acknowledgement, because metadata
   may already be committed. SQL and file storage do not share an atomic transaction;
   uncertain failures or failed compensation can leave unreferenced private objects.
"""

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


class EvidenceNotFoundError(StorageError):
    """The requested original is absent from private storage."""


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
    base = os.path.basename(filename.replace("\\", "/"))
    # Remove null bytes and control chars
    base = re.sub(r'[\x00-\x1f\x7f]', '', base)
    # Remove Windows/Unix path separators that might remain
    base = base.replace("/", "").replace("\\", "").replace('"', "").strip()
    
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
            descriptor = os.open(file_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(descriptor, "wb") as f:
                f.write(data)
        except Exception as e:
            raise StorageError(f"Failed to write evidence to disk: {e}") from e

        return storage_key, sha256_hash, size_bytes

    def get_file_path(self, storage_key: str) -> str:
        """Get absolute path for a private storage key, ensuring no directory escape."""
        safe_key = os.path.basename(storage_key)
        full_path = os.path.abspath(os.path.join(self.base_dir, safe_key))
        if os.path.commonpath([full_path, os.path.abspath(self.base_dir)]) != os.path.abspath(self.base_dir):
            raise StorageError("Path traversal attempt detected.")
        if not os.path.exists(full_path):
            raise EvidenceNotFoundError("Stored evidence file not found.")
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


class GCSEvidenceStorage:
    """Private, immutable originals accessed with the Cloud Run service identity.

    No public URLs, signed URLs, service-account key files or local cache are used.
    The bucket is configured with uniform access and public access prevention.
    """

    def __init__(self, bucket_name: str, client=None):
        if not bucket_name or not bucket_name.strip():
            raise ValueError("EVIDENCE_GCS_BUCKET is required for GCS storage.")
        self.bucket_name = bucket_name
        self._client = client

    def _blob(self, storage_key: str):
        # Keys come from our evidence UUID, never an uploaded filename.
        if not re.fullmatch(r"[0-9a-fA-F-]{36}\.bin", storage_key):
            raise StorageError("Invalid evidence storage key.")
        if self._client is None:
            from google.cloud import storage
            self._client = storage.Client()
        return self._client.bucket(self.bucket_name).blob(storage_key)

    def save_file(self, data: bytes, evidence_id: str) -> Tuple[str, str, int]:
        if len(data) > settings.MAX_UPLOAD_SIZE_BYTES:
            raise FileTooLargeError("File exceeds the evidence size limit.")
        storage_key = f"{uuid.UUID(evidence_id)}.bin"
        try:
            blob = self._blob(storage_key)
            blob.upload_from_string(
                data, content_type="application/octet-stream",
                if_generation_match=0, timeout=30,
            )
        except Exception as exc:
            # Provider errors may contain bucket names, paths and request details.
            raise StorageError("Could not save evidence to private storage.") from exc
        return storage_key, hashlib.sha256(data).hexdigest(), len(data)

    def read_file(self, storage_key: str) -> bytes:
        from google.api_core.exceptions import NotFound
        try:
            blob = self._blob(storage_key)
            blob.reload(timeout=30)
            if blob.size is None or blob.size > settings.MAX_UPLOAD_SIZE_BYTES:
                raise StorageError("Stored evidence exceeds the size limit.")
            return blob.download_as_bytes(if_generation_match=blob.generation, timeout=30)
        except NotFound as exc:
            raise EvidenceNotFoundError("Stored evidence file not found.") from exc
        except Exception as exc:
            raise StorageError("Could not read evidence from private storage.") from exc

    def delete_file(self, storage_key: str) -> bool:
        """Best-effort compensation if recording a newly uploaded file fails."""
        try:
            blob = self._blob(storage_key)
            blob.reload(timeout=30)
            blob.delete(if_generation_match=blob.generation, timeout=30)
            return True
        except Exception:
            return False


def create_storage_service():
    backend = settings.EVIDENCE_STORAGE_BACKEND
    if backend == "local":
        return LocalEvidenceStorage()
    if backend == "gcs":
        return GCSEvidenceStorage(settings.EVIDENCE_GCS_BUCKET)
    raise ValueError("EVIDENCE_STORAGE_BACKEND must be local or gcs.")


def validate_cloud_run_settings():
    """Fail closed instead of losing records on an ephemeral Cloud Run instance."""
    if os.getenv("K_SERVICE"):
        if settings.ENVIRONMENT not in ("production", "prod"):
            raise RuntimeError("Cloud Run requires ENVIRONMENT=production.")
        if settings.EVIDENCE_STORAGE_BACKEND != "gcs" or not settings.EVIDENCE_GCS_BUCKET:
            raise RuntimeError("Cloud Run requires private GCS evidence storage.")
        if not settings.DATABASE_URL.startswith(("postgres://", "postgresql://", "postgresql+psycopg://")):
            raise RuntimeError("Cloud Run requires persistent PostgreSQL records.")


storage_service = create_storage_service()
