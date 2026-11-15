"""One-use extension upload capabilities: intake only, never private case-read access."""

import hashlib
import secrets
import time
from fastapi import APIRouter, Depends, Header, File, UploadFile
from sqlalchemy.orm import Session
from sqlalchemy import update
from backend.app.api.v2.platform import Key
from backend.app.core.auth import get_current_session, SessionData
from backend.app.core.database import get_db
from backend.app.models.pairing import CaptureCapability
from backend.app.models.integrations import Intake
from backend.app.models.workflow import identity
from backend.app.schemas.platform import Strict
from backend.app.services.platform.operations import execute
from backend.app.services.platform.workflow import owned_case
from backend.app.services.platform.accounts import ensure_active
from backend.app.services.storage import (
    storage_service,
    inspect_content_mime_type,
    InvalidFileError,
)
from backend.app.services.case_state import fail

router = APIRouter(
    prefix="/api/v2/connectors/extension",
    tags=["Explicit capture capability proposal v1"],
)


class Pair(Strict):
    case_id: str


@router.post("/pair", status_code=201)
def pair(
    body: Pair,
    key: Key,
    auth: SessionData = Depends(get_current_session),
    db: Session = Depends(get_db),
):
    owned_case(db, auth.user_id, body.case_id)

    def save():
        token = secrets.token_urlsafe(32)
        expires = int(time.time()) + 600
        db.add(
            CaptureCapability(
                digest=hashlib.sha256(token.encode()).hexdigest(),
                owner_id=auth.user_id,
                session_id=auth.session_id,
                case_id=body.case_id,
                expires_at=expires,
            )
        )
        return {
            "case_id": body.case_id,
            "capture_token": token,
            "expires_at": expires,
            "scope": "one_upload_to_review_intake_only",
            "read_access": False,
        }

    return execute(db, auth.user_id, "extension.pair", key, body.model_dump(), save)


@router.post("/capture", status_code=201)
def capture(
    file: UploadFile = File(...),
    authorization: str = Header(max_length=300),
    db: Session = Depends(get_db),
):
    # No cookie/session is accepted here. The capability cannot be used at normal APIs.
    if not authorization.startswith("Capture "):
        fail(401, "UNAUTHENTICATED", "Capture capability required.")
    token = authorization[8:]
    row = db.get(CaptureCapability, hashlib.sha256(token.encode()).hexdigest())
    if row is None or row.expires_at < int(time.time()):
        fail(401, "UNAUTHENTICATED", "Capture capability expired or invalid.")
    from backend.app.core.config import settings

    if settings.AUTH_PROVIDER == "firebase":
        from backend.app.models.account import AccountSession, Account
        from backend.app.services.account_auth import provider_call, check_user

        session = db.get(AccountSession, row.session_id)
        account = db.get(Account, row.owner_id)
        if (
            session is None
            or account is None
            or session.account_id != row.owner_id
            or session.revoked_at is not None
            or session.expires_at <= int(time.time())
        ):
            fail(401, "UNAUTHENTICATED", "Pair a new capture after signing in again.")
        check_user(
            provider_call("user", account.provider_uid),
            session.auth_time,
            session.factor_version,
        )
    ensure_active(db, row.owner_id)
    owned_case(db, row.owner_id, row.case_id)
    content = file.file.read(10 * 1024 * 1024 + 1)
    if not content or len(content) > 10 * 1024 * 1024:
        fail(413, "FILE_TOO_LARGE", "Capture must contain 1 byte to 10 MiB.")
    try:
        inspect_content_mime_type(content, file.content_type)
    except InvalidFileError:
        fail(415, "UNSUPPORTED_MEDIA_TYPE", "Unsupported captured file.")
    digest = hashlib.sha256(content).hexdigest()
    if row.used_at is not None:
        if row.payload_hash != digest:
            fail(
                409, "CAPTURE_USED", "Capability already used for a different capture."
            )
        return {"intake_id": row.result, "state": "review_required", "duplicate": True}
    count = db.execute(
        update(CaptureCapability)
        .where(
            CaptureCapability.digest == row.digest, CaptureCapability.used_at.is_(None)
        )
        .values(used_at=int(time.time()), payload_hash=digest),
        execution_options={"synchronize_session": False},
    ).rowcount
    if count != 1:
        fail(
            409,
            "CAPTURE_USED",
            "Capture already submitted; reconcile the original request.",
        )
    iid = identity()
    storage_key, _, _ = storage_service.save_file(content, iid)
    item = Intake(
        id=iid,
        owner_id=row.owner_id,
        case_id=row.case_id,
        provider="extension",
        event_id=row.digest,
        message_hash=digest,
        storage_key=storage_key,
    )
    # Same original may already be in this owner's intake. Keep its stable original reference.
    duplicate = (
        db.query(Intake)
        .filter_by(owner_id=row.owner_id, case_id=row.case_id, message_hash=digest)
        .first()
    )
    if duplicate:
        storage_service.delete_file(storage_key)
        iid = duplicate.id
    else:
        db.add(item)
    db.execute(
        update(CaptureCapability)
        .where(CaptureCapability.digest == row.digest)
        .values(result=iid),
        execution_options={"synchronize_session": False},
    )
    db.commit()
    return {
        "intake_id": iid,
        "state": "review_required",
        "duplicate": duplicate is not None,
    }
