import uuid
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status, Response, Request
from urllib.parse import quote
from starlette.concurrency import run_in_threadpool
from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.app.core.database import get_db
from backend.app.core.auth import get_current_session, SessionData
from backend.app.models.case import Case, utc_now_iso
from backend.app.models.evidence import Evidence
from backend.app.models.timeline import TimelineEvent
from backend.app.services.case_state import claim_version
from backend.app.schemas.contract import (
    EvidenceSchema, EvidenceUploadResponse, EvidenceListResponse
)
from backend.app.services.storage import (
    storage_service, sanitize_filename, inspect_content_mime_type,
    InvalidFileError, FileTooLargeError, StorageError, EvidenceNotFoundError
)

router = APIRouter(prefix="/cases/{case_id}/evidence", tags=["Evidence"])


def _api_error(status_code: int, code: str, message: str, details: Optional[list] = None):
    req_id = str(uuid.uuid4())
    raise HTTPException(
        status_code=status_code,
        detail={
            "error": {
                "code": code,
                "message": message,
                "details": details or [],
                "request_id": req_id
            }
        }
    )


@router.post("", response_model=EvidenceUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_evidence(
    case_id: str,
    request: Request,
    file: UploadFile = File(...),
    expected_version: int = Form(..., gt=0),
    session: SessionData = Depends(get_current_session),
    db: Session = Depends(get_db)
):
    """
    Upload evidence file (PNG, JPEG, PDF, text/plain) to an owned case.
    Requires an authenticated session.
    Validates file format by content inspection, enforces max 10MB limit,
    hashes with SHA-256, increments case version, and records a timeline event.
    """
    form = await request.form()
    if sorted(form.keys()) != ["expected_version", "file"] or len(form.getlist("file")) != 1 or len(form.getlist("expected_version")) != 1:
        _api_error(422, "VALIDATION_ERROR", "Upload exactly one file and one expected_version field.")
    case = db.query(Case).filter(Case.id == case_id, Case.owner_id == session.user_id).first()
    if not case:
        _api_error(status.HTTP_404_NOT_FOUND, "NOT_FOUND", f"Case {case_id} not found.")

    if case.status == "resolved":
        _api_error(status.HTTP_409_CONFLICT, "CASE_RESOLVED", "Resolved cases permit reads only.")

    if expected_version is not None and case.version != expected_version:
        _api_error(
            status.HTTP_409_CONFLICT,
            "VERSION_CONFLICT",
            f"Case version conflict: current is {case.version}, expected {expected_version}."
        )

    from backend.app.services.rate_limit import enforce_limit
    enforce_limit(("upload", session.user_id), 30, 3600)
    file_count = db.query(Evidence).filter(Evidence.case_id == case_id).count()
    total_bytes = db.query(func.coalesce(func.sum(Evidence.size_bytes), 0)).join(Case).filter(Case.owner_id == session.user_id).scalar()
    if file_count >= 30 or total_bytes >= 50 * 1024 * 1024:
        _api_error(413, "STORAGE_LIMIT", "This workspace has reached its evidence limit (30 files per case, 50 MiB total).")
    # Read uploaded file content
    try:
        content = await file.read(10 * 1024 * 1024 + 1)
    except Exception as e:
        _api_error(status.HTTP_422_UNPROCESSABLE_ENTITY, "UNREADABLE_EVIDENCE", "Could not read upload payload.")

    if len(content) > 10 * 1024 * 1024:
        _api_error(413, "FILE_TOO_LARGE", "File exceeds 10 MiB.")
    if total_bytes + len(content) > 50 * 1024 * 1024:
        _api_error(413, "STORAGE_LIMIT", "This workspace has reached its 50 MiB evidence limit.")
    # Check 0 bytes
    if not content or len(content) == 0:
        _api_error(status.HTTP_422_UNPROCESSABLE_ENTITY, "VALIDATION_ERROR", "Uploaded file is empty (0 bytes).")

    # Content type inspection via magic bytes
    try:
        detected_mime = inspect_content_mime_type(content, file.content_type)
    except InvalidFileError as e:
        _api_error(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, "UNSUPPORTED_MEDIA_TYPE", str(e))

    claim_version(db, case, expected_version)
    evidence_id = str(uuid.uuid4())
    safe_name = sanitize_filename(file.filename)

    # Save to storage abstraction
    try:
        storage_key, sha256_hash, size_bytes = await run_in_threadpool(storage_service.save_file, content, evidence_id)
    except FileTooLargeError as e:
        _api_error(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "FILE_TOO_LARGE", str(e))
    except StorageError as e:
        _api_error(status.HTTP_500_INTERNAL_SERVER_ERROR, "STORAGE_ERROR", str(e))

    download_path = f"/api/v1/cases/{case_id}/evidence/{evidence_id}/content"
    now_iso = utc_now_iso()

    try:
        evidence = Evidence(
            id=evidence_id,
            case_id=case_id,
            filename=safe_name,
            media_type=detected_mime,
            size_bytes=size_bytes,
            sha256=sha256_hash,
            storage_key=storage_key,
            download_path=download_path,
            created_at=now_iso
        )
        db.add(evidence)

        # Increment case version

        # Prevent duplicate timeline entries
        timeline_entry = TimelineEvent(
            case_id=case_id,
            event_type="evidence_uploaded",
            description=f"Evidence uploaded: '{safe_name}' ({detected_mime}, {size_bytes} bytes).",
            event_date=now_iso,
            created_at=now_iso
        )
        db.add(timeline_entry)

        # A rejected flush has not committed metadata, so compensation is safe.
        db.flush()
    except Exception:
        db.rollback()
        await run_in_threadpool(storage_service.delete_file, storage_key)
        _api_error(status.HTTP_500_INTERNAL_SERVER_ERROR, "DATABASE_ERROR", "Failed to record evidence.")

    try:
        db.commit()
    except Exception:
        db.rollback()
        # A lost commit acknowledgement may mean SQL did commit. Preserve the
        # original so a retry/reconciliation cannot encounter a dangling record.
        _api_error(status.HTTP_500_INTERNAL_SERVER_ERROR, "DATABASE_ERROR", "Could not confirm the evidence save. Reload the case before retrying.")
    db.refresh(evidence)
    db.refresh(case)

    return {
        "evidence": EvidenceSchema.model_validate(evidence),
        "case_version": case.version
    }


@router.get("", response_model=EvidenceListResponse)
def list_case_evidence(
    case_id: str,
    session: SessionData = Depends(get_current_session),
    db: Session = Depends(get_db)
):
    """List all evidence metadata associated with an owned case. Requires authenticated session."""
    case = db.query(Case).filter(Case.id == case_id, Case.owner_id == session.user_id).first()
    if not case:
        _api_error(status.HTTP_404_NOT_FOUND, "NOT_FOUND", f"Case {case_id} not found.")

    evidence_items = (
        db.query(Evidence)
        .filter(Evidence.case_id == case_id)
        .order_by(Evidence.created_at.asc(), Evidence.id.asc())
        .all()
    )
    return {"evidence": [EvidenceSchema.model_validate(e) for e in evidence_items]}


@router.get("/{evidence_id}", response_model=EvidenceSchema)
def get_evidence_metadata(
    case_id: str,
    evidence_id: str,
    session: SessionData = Depends(get_current_session),
    db: Session = Depends(get_db)
):
    """Retrieve metadata for a specific evidence item in an owned case."""
    evidence = (
        db.query(Evidence)
        .join(Case)
        .filter(Evidence.id == evidence_id, Evidence.case_id == case_id, Case.owner_id == session.user_id)
        .first()
    )
    if not evidence:
        _api_error(status.HTTP_404_NOT_FOUND, "NOT_FOUND", f"Evidence {evidence_id} not found under case {case_id}.")
    return EvidenceSchema.model_validate(evidence)


@router.get("/{evidence_id}/content")
def get_evidence_content(
    case_id: str,
    evidence_id: str,
    session: SessionData = Depends(get_current_session),
    db: Session = Depends(get_db)
):
    """
    Stream evidence raw bytes with secure headers.
    Protected by session authorization and case ownership.
    Headers: Cache-Control: private, no-store, X-Content-Type-Options: nosniff.
    """
    evidence = (
        db.query(Evidence)
        .join(Case)
        .filter(Evidence.id == evidence_id, Evidence.case_id == case_id, Case.owner_id == session.user_id)
        .first()
    )
    if not evidence:
        _api_error(status.HTTP_404_NOT_FOUND, "NOT_FOUND", f"Evidence {evidence_id} not found under case {case_id}.")

    try:
        file_bytes = storage_service.read_file(evidence.storage_key)
    except EvidenceNotFoundError:
        _api_error(status.HTTP_404_NOT_FOUND, "FILE_NOT_FOUND", "Stored evidence file not found.")
    except StorageError:
        _api_error(status.HTTP_503_SERVICE_UNAVAILABLE, "STORAGE_ERROR", "Private evidence storage is temporarily unavailable.")

    safe_name = sanitize_filename(evidence.filename)
    headers = {
        "Cache-Control": "private, no-store",
        "X-Content-Type-Options": "nosniff",
        "Content-Disposition": f"attachment; filename*=UTF-8''{quote(safe_name, safe='')}",
    }

    return Response(
        content=file_bytes,
        media_type=evidence.media_type,
        headers=headers
    )
