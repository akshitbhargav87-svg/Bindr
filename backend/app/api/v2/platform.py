"""A1 HTTP primitives. Auth/CSRF/expected-account defenses are the existing real dependency."""

import json
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Annotated
from fastapi import APIRouter, Depends, Header
from sqlalchemy import update
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.core.auth import get_current_session, SessionData
from backend.app.models.case import Case, utc_now_iso
from backend.app.models.evidence import Evidence
from backend.app.models.platform import CaptureDraft
from backend.app.models.timeline import TimelineEvent
from backend.app.schemas.platform import CaseCreate, DraftCreate, DraftUpdate
from backend.app.schemas.contract import CaseSchema
from backend.app.services.case_state import fail
from backend.app.services.platform.operations import execute, canonical

router = APIRouter(prefix="/api/v2", tags=["Platform v2"])
Key = Annotated[str, Header(alias="Idempotency-Key", min_length=1, max_length=200)]


def validate_sources(db, owner, capture):
    ids = capture.evidence_ids
    if len(set(ids)) != len(ids):
        fail(422, "VALIDATION_ERROR", "Duplicate evidence IDs.")
    for eid in ids:
        row = (
            db.query(Evidence)
            .join(Case)
            .filter(Evidence.id == eid, Case.owner_id == owner)
            .first()
        )
        if row is None:
            fail(404, "NOT_FOUND", "Evidence not found.")


def communication_warnings(comm):
    if (
        comm
        and comm["date"]
        and comm["date"] > datetime.now(ZoneInfo(comm["timezone"])).date().isoformat()
    ):
        return ["future_communication_date_requires_confirmation"]
    return []


def draft_view(row):
    capture = json.loads(row.payload)
    comm = capture["communication"]
    warnings = communication_warnings(comm)
    return {
        "draft": {
            "id": row.id,
            "version": row.version,
            "capture": capture,
            "warnings": warnings,
            "updated_at": row.updated_at,
        }
    }


@router.post("/cases", status_code=201)
def create_case(
    body: CaseCreate,
    key: Key,
    auth: SessionData = Depends(get_current_session),
    db: Session = Depends(get_db),
):
    def save():
        row = Case(owner_id=auth.user_id, **body.model_dump())
        db.add(row)
        db.flush()
        db.add(
            TimelineEvent(
                case_id=row.id,
                event_type="case_created",
                description="Case created from reviewed user input.",
            )
        )
        return {"case": CaseSchema.model_validate(row).model_dump(mode="json")}

    return execute(
        db, auth.user_id, "cases.create", key, body.model_dump(mode="json"), save
    )


@router.post("/capture-drafts", status_code=201)
def create_draft(
    body: DraftCreate,
    key: Key,
    auth: SessionData = Depends(get_current_session),
    db: Session = Depends(get_db),
):
    validate_sources(db, auth.user_id, body.capture)

    def save():
        if db.query(CaptureDraft).filter_by(owner_id=auth.user_id).count() >= 50:
            fail(429, "DRAFT_LIMIT", "Remove old drafts before creating more.")
        row = CaptureDraft(
            owner_id=auth.user_id,
            payload=canonical(body.capture.model_dump(mode="json")),
        )
        db.add(row)
        db.flush()
        return draft_view(row)

    return execute(
        db,
        auth.user_id,
        "capture-drafts.create",
        key,
        body.model_dump(mode="json"),
        save,
    )


@router.get("/capture-drafts/{draft_id}")
def get_draft(
    draft_id: str,
    auth: SessionData = Depends(get_current_session),
    db: Session = Depends(get_db),
):
    row = db.query(CaptureDraft).filter_by(id=draft_id, owner_id=auth.user_id).first()
    if row is None:
        fail(404, "NOT_FOUND", "Draft not found.")
    return draft_view(row)


@router.put("/capture-drafts/{draft_id}")
def update_draft(
    draft_id: str,
    body: DraftUpdate,
    key: Key,
    auth: SessionData = Depends(get_current_session),
    db: Session = Depends(get_db),
):
    row = db.query(CaptureDraft).filter_by(id=draft_id, owner_id=auth.user_id).first()
    if row is None:
        fail(404, "NOT_FOUND", "Draft not found.")
    validate_sources(db, auth.user_id, body.capture)

    def save():
        count = db.execute(
            update(CaptureDraft)
            .where(
                CaptureDraft.id == draft_id,
                CaptureDraft.owner_id == auth.user_id,
                CaptureDraft.version == body.expected_version,
            )
            .values(
                payload=canonical(body.capture.model_dump(mode="json")),
                version=body.expected_version + 1,
                updated_at=utc_now_iso(),
            ),
            execution_options={"synchronize_session": False},
        ).rowcount
        if count != 1:
            fail(409, "VERSION_CONFLICT", "Refresh the saved draft before editing.")
        db.expire(row)
        return draft_view(row)

    return execute(
        db,
        auth.user_id,
        f"capture-drafts.update:{draft_id}",
        key,
        body.model_dump(mode="json"),
        save,
    )
