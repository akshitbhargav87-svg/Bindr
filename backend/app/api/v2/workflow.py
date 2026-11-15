import json
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.app.api.v2.platform import Key
from backend.app.core.auth import get_current_session, SessionData
from backend.app.core.database import get_db
from backend.app.models.case import Case
from backend.app.models.workflow import CaseControl
from backend.app.schemas.workflow import (
    ManualPromise,
    Outcome,
    Lifecycle,
    DeadlinePreview,
)
from backend.app.services.platform.operations import execute
from backend.app.services.platform.workflow import (
    owned_case,
    claim,
    add_obligation,
    snapshot,
    record_outcome,
    event,
)
from backend.app.services.platform.deadlines import preview
from backend.app.services.case_state import fail

router = APIRouter(prefix="/api/v2", tags=["Workflow v2"])


@router.get("/cases/{case_id}")
def detail(
    case_id: str,
    auth: SessionData = Depends(get_current_session),
    db: Session = Depends(get_db),
):
    return snapshot(db, owned_case(db, auth.user_id, case_id))


@router.get("/workspace")
def workspace(
    include_archived: bool = False,
    auth: SessionData = Depends(get_current_session),
    db: Session = Depends(get_db),
):
    from sqlalchemy import or_

    query = (
        db.query(Case)
        .outerjoin(CaseControl, CaseControl.case_id == Case.id)
        .filter(Case.owner_id == auth.user_id)
    )
    if not include_archived:
        query = query.filter(
            or_(CaseControl.state.is_(None), CaseControl.state != "archived")
        )
    cases = query.order_by(Case.created_at, Case.id).limit(200).all()
    return {"cases": [snapshot(db, c) for c in cases], "limit": 200}


@router.post("/deadline-preview")
def deadline(body: DeadlinePreview, auth: SessionData = Depends(get_current_session)):
    return {"deadline": preview(body)}


@router.post("/cases/{case_id}/manual-promises", status_code=201)
def manual(
    case_id: str,
    body: ManualPromise,
    key: Key,
    auth: SessionData = Depends(get_current_session),
    db: Session = Depends(get_db),
):
    case = owned_case(db, auth.user_id, case_id)

    def save():
        claim(db, case, body.expected_version)
        row = add_obligation(
            db,
            case,
            body.terms,
            body.sources,
            body.origin,
            body.predecessor_id,
            body.reason,
        )
        from backend.app.services.platform.reminders import schedule

        from backend.app.services.platform.deadlines import attach

        attach(row, body.deadline, body.terms, body.deadline_override_reason)
        schedule(db, case, auth.user_id)
        return {"obligation_id": row.id, "case_version": case.version}

    return execute(
        db, auth.user_id, "manual:" + case_id, key, body.model_dump(mode="json"), save
    )


@router.post("/cases/{case_id}/outcomes", status_code=201)
def outcome(
    case_id: str,
    body: Outcome,
    key: Key,
    auth: SessionData = Depends(get_current_session),
    db: Session = Depends(get_db),
):
    case = owned_case(db, auth.user_id, case_id)

    def save():
        claim(db, case, body.expected_version)
        row = record_outcome(db, case, body)
        from backend.app.services.platform.reminders import schedule

        schedule(db, case, auth.user_id)
        return {"event_id": row.id, "case_version": case.version}

    return execute(
        db, auth.user_id, "outcomes:" + case_id, key, body.model_dump(mode="json"), save
    )


@router.post("/cases/{case_id}/lifecycle")
def lifecycle(
    case_id: str,
    body: Lifecycle,
    key: Key,
    auth: SessionData = Depends(get_current_session),
    db: Session = Depends(get_db),
):
    case = owned_case(db, auth.user_id, case_id)

    def save():
        claim(db, case, body.expected_version, allow_closed=True)
        control = db.get(CaseControl, case_id)
        if control is None:
            control = CaseControl(case_id=case_id, owner_id=auth.user_id)
            db.add(control)
        if body.action in ("archive", "restore"):
            control.state = "archived" if body.action == "archive" else "open"
        if body.action == "reopen":
            control.state = "reopened"
            case.status = "open"
            case.resolved_at = None
        if body.action == "edit_identity":
            if body.title is not None:
                case.title = body.title
            if body.merchant_name is not None:
                case.merchant_name = body.merchant_name
        event(db, case_id, body.action, body.model_dump(mode="json"))
        from backend.app.services.platform.reminders import schedule

        schedule(db, case, auth.user_id)
        return {
            "case_version": case.version,
            "lifecycle": control.state,
            "receipts_preserved": True,
        }

    return execute(
        db,
        auth.user_id,
        "lifecycle:" + case_id,
        key,
        body.model_dump(mode="json"),
        save,
    )


@router.get("/cases/{case_id}/calendar.ics")
def calendar_export(
    case_id: str,
    auth: SessionData = Depends(get_current_session),
    db: Session = Depends(get_db),
):
    from fastapi import Response
    from backend.app.services.platform.calendar_export import calendar

    return Response(
        calendar(db, auth.user_id, case_id),
        media_type="text/calendar; charset=utf-8",
        headers={
            "Content-Disposition": 'attachment; filename="bindr-calendar.ics"',
            "Cache-Control": "private, no-store",
        },
    )


from backend.app.schemas.workflow import Note


@router.post("/cases/{case_id}/notes", status_code=201)
def note(
    case_id: str,
    body: Note,
    key: Key,
    auth: SessionData = Depends(get_current_session),
    db: Session = Depends(get_db),
):
    case = owned_case(db, auth.user_id, case_id)
    from backend.app.services.platform.workflow import sources

    sources(db, case_id, body.source_ids)

    def save():
        claim(db, case, body.expected_version)
        row = event(db, case_id, "user_note", body.model_dump(mode="json"))
        return {
            "event_id": row.id,
            "case_version": case.version,
            "classification": "user_testimony_not_company_confirmation",
        }

    return execute(
        db, auth.user_id, "notes:" + case_id, key, body.model_dump(mode="json"), save
    )
