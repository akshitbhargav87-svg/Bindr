"""Private ingestion types. Accepted bytes do not imply a connected transcription/AI processor."""

from pathlib import Path
import hashlib
from backend.app.services.storage import inspect_content_mime_type, storage_service
from backend.app.services.case_state import fail


def inspect_media(content, filename, declared_type=None):
    if content.startswith(b"RIFF") and content[8:12] == b"WAVE":
        return "audio/wav"
    if content.startswith(b"ID3") or content[:2] in (
        b"\xff\xfb",
        b"\xff\xf3",
        b"\xff\xf2",
    ):
        return "audio/mpeg"
    if content.startswith(b"fLaC"):
        return "audio/flac"
    if content.startswith(b"OggS"):
        return "audio/ogg"
    if (
        content.startswith(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1")
        and Path(filename or "").suffix.lower() == ".msg"
    ):
        return "application/vnd.ms-outlook"
    mime = inspect_content_mime_type(content, declared_type)
    if mime == "text/plain" and Path(filename or "").suffix.lower() == ".eml":
        return "message/rfc822"
    return mime


def original(row):
    content = storage_service.read_file(row.storage_key)
    if (
        len(content) != row.size_bytes
        or hashlib.sha256(content).hexdigest() != row.sha256
    ):
        fail(
            409,
            "INTEGRITY_ERROR",
            "Original evidence no longer matches its recorded digest.",
        )
    return content


def processing_suffix(row):
    suffix = {
        "text/plain": ".txt",
        "image/png": ".png",
        "image/jpeg": ".jpg",
        "application/pdf": ".pdf",
    }.get(row.media_type)
    if suffix is None:
        fail(
            503,
            "DOCUMENT_PROCESSOR_UNAVAILABLE",
            "Original is saved privately. This source needs the versioned email/audio processor; manual entry remains available.",
        )
    return suffix
