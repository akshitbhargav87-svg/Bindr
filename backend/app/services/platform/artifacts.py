"""Bounded private generated artifacts in the existing storage backend, never web roots."""

import hashlib
import os
import uuid
from backend.app.services.storage import (
    storage_service,
    GCSEvidenceStorage,
    EvidenceNotFoundError,
    StorageError,
)

MAX_ARTIFACT_BYTES = 64 * 1024 * 1024


def save(data, resource_id):
    if len(data) > MAX_ARTIFACT_BYTES:
        raise StorageError("Export exceeds 64 MiB; select fewer originals.")
    key = str(uuid.UUID(resource_id)) + ".bin"
    if isinstance(storage_service, GCSEvidenceStorage):
        try:
            storage_service._blob(key).upload_from_string(
                data,
                content_type="application/octet-stream",
                if_generation_match=0,
                timeout=60,
            )
        except Exception as exc:
            raise StorageError("Could not save private export.") from exc
    else:
        path = os.path.join(storage_service.base_dir, key)
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
    return key


def read(key):
    if isinstance(storage_service, GCSEvidenceStorage):
        from google.api_core.exceptions import NotFound

        try:
            blob = storage_service._blob(key)
            blob.reload(timeout=30)
            if blob.size is None or blob.size > MAX_ARTIFACT_BYTES:
                raise StorageError("Invalid private artifact size.")
            return blob.download_as_bytes(
                if_generation_match=blob.generation, timeout=60
            )
        except NotFound as exc:
            raise EvidenceNotFoundError("Private export absent.") from exc
        except Exception as exc:
            raise StorageError("Could not read private export.") from exc
    path = storage_service.get_file_path(key)
    if os.path.getsize(path) > MAX_ARTIFACT_BYTES:
        raise StorageError("Invalid private artifact size.")
    with open(path, "rb") as handle:
        return handle.read(MAX_ARTIFACT_BYTES + 1)
