import hashlib
import json
import uuid
from fastapi import APIRouter, Depends, File, Form, UploadFile, Request
from sqlalchemy.orm import Session
from pydantic import ValidationError
from backend.app.api.v2.platform import Key, communication_warnings
from backend.app.core.auth import get_current_session, SessionData
from backend.app.core.database import get_db
from backend.app.models.evidence import Evidence
from backend.app.models.platform import EvidenceCommunication
from backend.app.models.case import Case
from backend.app.schemas.platform import Communication
from backend.app.schemas.contract import EvidenceSchema
from backend.app.services.case_state import fail
from backend.app.services.platform.workflow import owned_case, claim, event
from backend.app.services.platform.operations import execute, canonical
from backend.app.services.storage import (
    storage_service,
    inspect_content_mime_type,
    sanitize_filename,
    InvalidFileError,
)


async def strict_upload_form(request: Request):
    form = await request.form()
    keys = ["communication", "expected_version", "file"]
    if sorted(form.keys()) != keys or any(len(form.getlist(k)) != 1 for k in keys):
        fail(
            422,
            "VALIDATION_ERROR",
            "Upload exactly one file, one version, and one communication metadata field.",
        )


router = APIRouter(prefix="/api/v2", tags=["Evidence v2"])


@router.post("/cases/{case_id}/evidence", status_code=201)
def upload(
    case_id: str,
    request: Request,
    key: Key,
    file: UploadFile = File(...),
    expected_version: int = Form(..., gt=0),
    communication: str = Form(...),
    validated_form=Depends(strict_upload_form),
    auth: SessionData = Depends(get_current_session),
    db: Session = Depends(get_db),
):
    case = owned_case(db, auth.user_id, case_id)
    try:
        comm = Communication.model_validate_json(communication)
    except ValidationError:
        fail(422, "VALIDATION_ERROR", "Invalid communication date metadata.")
    content = file.file.read(10 * 1024 * 1024 + 1)
    if not content:
        fail(422, "VALIDATION_ERROR", "Empty evidence.")
    if len(content) > 10 * 1024 * 1024:
        fail(413, "FILE_TOO_LARGE", "File exceeds 10 MiB.")
    try:
        from backend.app.services.platform.media import inspect_media

        mime = inspect_media(content, file.filename, file.content_type)
    except InvalidFileError:
        fail(415, "UNSUPPORTED_MEDIA_TYPE", "Unsupported evidence type.")
    digest = hashlib.sha256(content).hexdigest()
    payload = {
        "expected_version": expected_version,
        "sha256": digest,
        "filename": sanitize_filename(file.filename),
        "communication": comm.model_dump(mode="json"),
    }

    def save():
        # Serialize same-case dedupe, even for different operation keys on PostgreSQL.
        if db.bind.dialect.name == "postgresql":
            from sqlalchemy import text

            owner_lock = int.from_bytes(
                hashlib.sha256(("upload-quota:" + auth.user_id).encode()).digest()[:8],
                "big",
                signed=True,
            )
            db.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": owner_lock})
            db.execute(
                text("SELECT id FROM cases WHERE id=:id FOR UPDATE"), {"id": case_id}
            )
            db.refresh(case)
        duplicate = db.query(Evidence).filter_by(case_id=case_id, sha256=digest).first()
        if duplicate:
            return {
                "evidence": EvidenceSchema.model_validate(duplicate).model_dump(
                    mode="json"
                ),
                "duplicate_of": duplicate.id,
                "case_version": case.version,
                "communication": (
                    json.loads(db.get(EvidenceCommunication, duplicate.id).payload)
                    if db.get(EvidenceCommunication, duplicate.id)
                    else None
                ),
            }
        from sqlalchemy import func

        count = db.query(Evidence).filter_by(case_id=case_id).count()
        total = (
            db.query(func.coalesce(func.sum(Evidence.size_bytes), 0))
            .join(Case)
            .filter(Case.owner_id == auth.user_id)
            .scalar()
        )
        if count >= 30 or total + len(content) > 50 * 1024 * 1024:
            fail(413, "STORAGE_LIMIT", "Evidence quota exceeded.")
        claim(db, case, expected_version)
        eid = str(uuid.uuid4())
        storage_key, sha, size = storage_service.save_file(content, eid)
        row = Evidence(
            id=eid,
            case_id=case_id,
            filename=payload["filename"],
            media_type=mime,
            size_bytes=size,
            sha256=sha,
            storage_key=storage_key,
            download_path=f"/api/v1/cases/{case_id}/evidence/{eid}/content",
        )
        try:
            db.add(row)
            db.flush()
            db.add(
                EvidenceCommunication(
                    evidence_id=eid, payload=canonical(comm.model_dump(mode="json"))
                )
            )
            event(
                db,
                case_id,
                "evidence_uploaded",
                {
                    "evidence_id": eid,
                    "sha256": sha,
                    "communication": comm.model_dump(mode="json"),
                },
            )
        except Exception:
            storage_service.delete_file(storage_key)
            raise
        return {
            "evidence": EvidenceSchema.model_validate(row).model_dump(mode="json"),
            "warnings": communication_warnings(comm.model_dump(mode="json")),
            "duplicate_of": None,
            "communication": comm.model_dump(mode="json"),
            "case_version": case.version,
        }

    return execute(db, auth.user_id, "evidence:" + case_id, key, payload, save)


from backend.app.schemas.workflow import CommunicationCorrection


@router.put("/cases/{case_id}/evidence/{evidence_id}/communication")
def correct_communication(
    case_id: str,
    evidence_id: str,
    body: CommunicationCorrection,
    key: Key,
    auth: SessionData = Depends(get_current_session),
    db: Session = Depends(get_db),
):
    case = owned_case(db, auth.user_id, case_id)
    evidence = db.query(Evidence).filter_by(id=evidence_id, case_id=case_id).first()
    if evidence is None:
        fail(404, "NOT_FOUND", "Evidence not found.")

    def save():
        claim(db, case, body.expected_version)
        row = db.get(EvidenceCommunication, evidence_id)
        before = json.loads(row.payload) if row else None
        if row is None:
            row = EvidenceCommunication(evidence_id=evidence_id, version=1)
            db.add(row)
        else:
            row.version += 1
        row.payload = canonical(body.communication.model_dump(mode="json"))
        event(
            db,
            case_id,
            "communication_corrected",
            {
                "evidence_id": evidence_id,
                "before": before,
                "after": body.communication.model_dump(mode="json"),
                "reason": body.reason,
            },
        )
        return {
            "evidence_id": evidence_id,
            "warnings": communication_warnings(json.loads(row.payload)),
            "communication": json.loads(row.payload),
            "case_version": case.version,
        }

    return execute(
        db,
        auth.user_id,
        "communication:" + evidence_id,
        key,
        body.model_dump(mode="json"),
        save,
    )
