import hashlib
import json
import secrets
import time
from typing import Literal
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from pydantic import Field
from backend.app.api.v2.platform import Key
from backend.app.core.auth import get_current_session, SessionData
from backend.app.core.database import get_db
from backend.app.models.integrations import Connection, IntakeAlias, Intake
from backend.app.schemas.platform import Strict
from backend.app.services.platform.operations import execute
from backend.app.services.platform.workflow import owned_case
from backend.app.services.platform.connectors import (
    begin_gmail,
    finish_gmail,
    revoke_gmail,
)
from backend.app.services.case_state import fail

router = APIRouter(prefix="/api/v2/connectors", tags=["Connectors proposal v1"])


class Connect(Strict):
    capability: Literal["send", "read", "send_and_read"]


class Alias(Strict):
    case_id: str | None = None


@router.post("/gmail/connect")
def connect(
    body: Connect,
    key: Key,
    auth: SessionData = Depends(get_current_session),
    db: Session = Depends(get_db),
):
    return execute(
        db,
        auth.user_id,
        "gmail.connect",
        key,
        body.model_dump(),
        lambda: begin_gmail(db, auth, body.capability),
    )


@router.get("/gmail/callback")
def callback(
    state: str = Query(min_length=20, max_length=200),
    code: str = Query(min_length=1, max_length=4000),
    auth: SessionData = Depends(get_current_session),
    db: Session = Depends(get_db),
):
    return finish_gmail(db, auth, state, code)


@router.post("/gmail/disconnect")
def disconnect(
    key: Key,
    auth: SessionData = Depends(get_current_session),
    db: Session = Depends(get_db),
):
    return execute(
        db,
        auth.user_id,
        "gmail.disconnect",
        key,
        {},
        lambda: revoke_gmail(db, auth.user_id),
    )


@router.get("/{provider}/status")
def status(
    provider: Literal["gmail", "inbound_email", "whatsapp"],
    auth: SessionData = Depends(get_current_session),
    db: Session = Depends(get_db),
):
    row = (
        db.query(Connection).filter_by(owner_id=auth.user_id, provider=provider).first()
    )
    return {
        "provider": provider,
        "state": row.state if row else "not_connected",
        "scopes": json.loads(row.scopes) if row else [],
        "public_activation": False,
        "automatic_send": False,
        "configuration_required": True,
    }


@router.post("/inbound_email/aliases", status_code=201)
def alias(
    body: Alias,
    key: Key,
    auth: SessionData = Depends(get_current_session),
    db: Session = Depends(get_db),
):
    if body.case_id:
        owned_case(db, auth.user_id, body.case_id)

    def save():
        token = secrets.token_urlsafe(32)
        digest = hashlib.sha256(token.encode()).hexdigest()
        db.add(IntakeAlias(digest=digest, owner_id=auth.user_id, case_id=body.case_id))
        return {
            "case_id": body.case_id,
            "alias_id": digest,
            "alias_token": token,
            "state": "provider_configuration_required",
            "read_access": False,
        }

    # Result necessarily retains a recoverable capability until explicitly revoked;
    # API stays owner-only and does not place this in public logs.
    return execute(db, auth.user_id, "intake.alias", key, body.model_dump(), save)


@router.delete("/inbound_email/aliases/{alias_id}")
def revoke_alias(
    alias_id: str,
    key: Key,
    auth: SessionData = Depends(get_current_session),
    db: Session = Depends(get_db),
):
    row = db.get(IntakeAlias, alias_id)
    if row is None or row.owner_id != auth.user_id:
        fail(404, "NOT_FOUND", "Alias not found.")

    def save():
        row.revoked_at = int(time.time())
        return {"state": "revoked"}

    return execute(db, auth.user_id, "alias.revoke:" + alias_id, key, {}, save)


@router.get("/inbound_email/intake")
def inbox(
    auth: SessionData = Depends(get_current_session), db: Session = Depends(get_db)
):
    rows = (
        db.query(Intake)
        .filter_by(owner_id=auth.user_id)
        .order_by(Intake.created_at.desc())
        .limit(100)
        .all()
    )
    return {
        "items": [
            {
                "id": r.id,
                "case_id": r.case_id,
                "provider": r.provider,
                "state": r.state,
                "created_at": r.created_at,
            }
            for r in rows
        ],
        "limit": 100,
    }


from backend.app.schemas.connectors import ReviewedSend, GmailImport


@router.post("/gmail/cases/{case_id}/send", status_code=202)
def reviewed_send(
    case_id: str,
    body: ReviewedSend,
    key: Key,
    auth: SessionData = Depends(get_current_session),
    db: Session = Depends(get_db),
):
    case = owned_case(db, auth.user_id, case_id)
    from backend.app.services.platform.gmail import connection
    from backend.app.services.platform.jobs import enqueue, view
    from backend.app.services.platform.workflow import sources

    connection_row = connection(db, auth.user_id, "send")
    if body.receive_replies:
        connection(db, auth.user_id, "read")
    sources(db, case_id, body.source_ids)

    def save():
        if case.version != body.expected_version:
            fail(409, "VERSION_CONFLICT", "Review current facts before sending.")
        # Network dispatch is an explicit worker handler, disabled by default.
        job = enqueue(
            db,
            auth.user_id,
            "send",
            {**body.model_dump(), "connection_generation": connection_row.generation},
            case_id,
            case.version,
        )
        return {**view(job), "automatic_send": False, "activation_required": True}

    return execute(
        db, auth.user_id, "gmail.send:" + case_id, key, body.model_dump(), save
    )


@router.post("/gmail/import", status_code=201)
def import_review(
    body: GmailImport,
    key: Key,
    auth: SessionData = Depends(get_current_session),
    db: Session = Depends(get_db),
):
    alias = db.get(IntakeAlias, hashlib.sha256(body.alias_token.encode()).hexdigest())
    if alias is None or alias.owner_id != auth.user_id or alias.revoked_at is not None:
        fail(404, "NOT_FOUND", "Intake destination not found.")
    from backend.app.services.platform.gmail import import_message

    return execute(
        db,
        auth.user_id,
        "gmail.import",
        key,
        body.model_dump(),
        lambda: import_message(db, auth.user_id, body.message_id, body.alias_token),
    )


@router.get("/inbound_email/intake/{intake_id}/content")
def intake_content(
    intake_id: str,
    auth: SessionData = Depends(get_current_session),
    db: Session = Depends(get_db),
):
    row = db.query(Intake).filter_by(id=intake_id, owner_id=auth.user_id).first()
    if row is None:
        fail(404, "NOT_FOUND", "Intake item not found.")
    if row.case_id:
        owned_case(db, auth.user_id, row.case_id)
    from backend.app.services.storage import storage_service
    from fastapi import Response

    return Response(
        storage_service.read_file(row.storage_key),
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": 'attachment; filename="bindr-original-intake.bin"',
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.post("/whatsapp/disconnect")
def disconnect_whatsapp(
    key: Key,
    auth: SessionData = Depends(get_current_session),
    db: Session = Depends(get_db),
):
    def save():
        from backend.app.models.integrations import ProviderLink
        from backend.app.models.jobs import Job

        db.query(ProviderLink).filter_by(
            owner_id=auth.user_id, provider="whatsapp"
        ).delete(synchronize_session=False)
        row = (
            db.query(Connection)
            .filter_by(owner_id=auth.user_id, provider="whatsapp")
            .first()
        )
        if row:
            row.state = "disconnected"
            row.credential = None
            row.generation += 1
        for job in (
            db.query(Job)
            .filter_by(owner_id=auth.user_id, kind="notification")
            .filter(Job.state.in_(["queued", "running"]))
            .all()
        ):
            if json.loads(job.payload).get("channel") == "whatsapp":
                job.state = "cancelled"
                job.stage = "disconnected"
        return {"state": "disconnected", "personal_inbox_access": False}

    return execute(db, auth.user_id, "whatsapp.disconnect", key, {}, save)
