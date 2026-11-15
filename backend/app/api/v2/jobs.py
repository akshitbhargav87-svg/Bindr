import json
import time
from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session
from backend.app.api.v2.platform import Key
from backend.app.core.auth import get_current_session, SessionData
from backend.app.core.database import get_db
from backend.app.models.case import utc_now_iso
from backend.app.models.jobs import Job, NotificationPreferences, Export
from backend.app.models.workflow import CaseControl
from backend.app.schemas.jobs import Notifications, ExportRequest, DeleteCase
from backend.app.services.case_state import fail
from backend.app.services.platform.workflow import owned_case, claim, event, sources
from backend.app.services.platform.operations import execute, canonical
from backend.app.services.platform.jobs import enqueue, view, cancel_case_jobs
from backend.app.services.storage import storage_service

router = APIRouter(prefix="/api/v2", tags=["Jobs and privacy v2"])


def recent(auth):
    if auth.auth_time is None or not 0 <= int(time.time()) - auth.auth_time <= 300:
        fail(
            401,
            "RECENT_AUTH_REQUIRED",
            "Reauthenticate before exporting or deleting account data.",
        )


@router.get("/jobs/{job_id}")
def get_job(
    job_id: str,
    auth: SessionData = Depends(get_current_session),
    db: Session = Depends(get_db),
):
    row = db.query(Job).filter_by(id=job_id, owner_id=auth.user_id).first()
    if row is None:
        fail(404, "NOT_FOUND", "Job not found.")
    return view(row)


@router.put("/notification-preferences")
def preferences(
    body: Notifications,
    key: Key,
    auth: SessionData = Depends(get_current_session),
    db: Session = Depends(get_db),
):
    def save():
        row = db.get(NotificationPreferences, auth.user_id)
        if row is None:
            if body.expected_version != 0:
                fail(409, "VERSION_CONFLICT", "Refresh notification preferences.")
            row = NotificationPreferences(owner_id=auth.user_id, version=1)
            db.add(row)
        else:
            from sqlalchemy import update

            count = db.execute(
                update(NotificationPreferences)
                .where(
                    NotificationPreferences.owner_id == auth.user_id,
                    NotificationPreferences.version == body.expected_version,
                )
                .values(version=body.expected_version + 1),
                execution_options={"synchronize_session": False},
            ).rowcount
            if count != 1:
                fail(409, "VERSION_CONFLICT", "Refresh notification preferences.")
            db.expire(row)
        row.payload = canonical(body.model_dump(exclude={"expected_version"}))
        db.query(Job).filter(
            Job.owner_id == auth.user_id,
            Job.kind.in_(["notification", "follow_up"]),
            Job.state.in_(["queued", "running"]),
        ).update(
            {"state": "cancelled", "stage": "preferences_changed"},
            synchronize_session=False,
        )
        from backend.app.models.case import Case
        from backend.app.services.platform.reminders import schedule

        for case in db.query(Case).filter_by(owner_id=auth.user_id).all():
            schedule(db, case, auth.user_id)
        from backend.app.services.platform.notifications import capabilities

        return {
            "version": row.version,
            "preferences": json.loads(row.payload),
            "capabilities": capabilities(),
            "delivery_enabled": False,
        }

    return execute(
        db, auth.user_id, "notification-preferences", key, body.model_dump(), save
    )


@router.post("/cases/{case_id}/exports", status_code=202)
def export_case(
    case_id: str,
    body: ExportRequest,
    key: Key,
    auth: SessionData = Depends(get_current_session),
    db: Session = Depends(get_db),
):
    case = owned_case(db, auth.user_id, case_id)
    sources(db, case_id, body.source_ids)
    if body.obligation_ids is not None:
        from backend.app.models.workflow import Obligation

        valid = {
            r.id
            for r in db.query(Obligation)
            .filter(
                Obligation.case_id == case_id, Obligation.id.in_(body.obligation_ids)
            )
            .all()
        }
        if valid != set(body.obligation_ids):
            fail(
                422,
                "INVALID_SELECTION",
                "An obligation is not present in this case snapshot.",
            )
    if body.trusted_timestamp:
        from backend.app.services.platform.timestamps import configuration

        configuration()

    def save():
        if case.version != body.expected_version:
            fail(409, "VERSION_CONFLICT", "Review current facts before exporting.")
        row = Export(
            owner_id=auth.user_id,
            case_id=case.id,
            case_version=case.version,
            expires_at=int(time.time()) + 86400,
        )
        db.add(row)
        db.flush()
        job = enqueue(
            db,
            auth.user_id,
            "export",
            {**body.model_dump(), "export_id": row.id},
            case.id,
            case.version,
        )
        return {"export_id": row.id, **view(job)}

    return execute(db, auth.user_id, "exports:" + case_id, key, body.model_dump(), save)


@router.get("/exports/{export_id}")
def get_export(
    export_id: str,
    download: bool = False,
    auth: SessionData = Depends(get_current_session),
    db: Session = Depends(get_db),
):
    row = db.query(Export).filter_by(id=export_id, owner_id=auth.user_id).first()
    if row is None or row.expires_at < int(time.time()):
        fail(404, "NOT_FOUND", "Export not found or expired.")
    current_case = owned_case(db, auth.user_id, row.case_id) if row.case_id else None
    if download:
        if row.state != "succeeded":
            fail(409, "EXPORT_NOT_READY", "Export is not ready.")
        from backend.app.services.platform import artifacts

        content = artifacts.read(row.storage_key)
        import hashlib

        if hashlib.sha256(content).hexdigest() != row.sha256:
            fail(409, "INTEGRITY_ERROR", "Export digest does not match.")
        return Response(
            content,
            media_type=row.media_type,
            headers={
                "Content-Disposition": 'attachment; filename="bindr-export"',
                "Cache-Control": "private, no-store",
                "X-Content-Type-Options": "nosniff",
            },
        )
    return {
        "export": {
            "id": row.id,
            "state": row.state,
            "case_version": row.case_version,
            "stale_snapshot": bool(
                current_case and current_case.version != row.case_version
            ),
            "expires_at": row.expires_at,
            "sha256": row.sha256,
            "manifest": json.loads(row.manifest) if row.manifest else None,
            "download_path": (
                f"/api/v2/exports/{row.id}?download=true"
                if row.state == "succeeded"
                else None
            ),
        }
    }


@router.delete("/cases/{case_id}", status_code=202)
def delete_case(
    case_id: str,
    body: DeleteCase,
    key: Key,
    auth: SessionData = Depends(get_current_session),
    db: Session = Depends(get_db),
):
    recent(auth)
    # Allows reconciliation only by the owner of the tombstone.
    control = db.get(CaseControl, case_id)
    prior_deletion = (
        db.query(Job)
        .filter_by(case_id=case_id, owner_id=auth.user_id, kind="delete_case")
        .first()
    )
    case = (
        owned_case(db, auth.user_id, case_id)
        if (not control or control.state != "deleting") and prior_deletion is None
        else None
    )
    if control and control.owner_id != auth.user_id:
        fail(404, "NOT_FOUND", "Case not found.")

    def save():
        if case is None:
            fail(409, "DELETION_IN_PROGRESS", "Deletion already requested.")
        claim(db, case, body.expected_version)
        row = control or CaseControl(case_id=case_id, owner_id=auth.user_id)
        row.state = "deleting"
        row.deleted_at = utc_now_iso()
        db.add(row)
        # Legacy endpoints also deny access immediately, without broad v1 router edits.
        case.owner_id = "deleted:" + case.id
        cancel_case_jobs(db, case_id)
        job = enqueue(db, auth.user_id, "delete_case", {}, case_id, case.version)
        return {
            **view(job),
            "deletion_token": job.id,
            "retention": "Normal access is revoked now. Private object cleanup is retryable; backups and third-party copies have separate retention.",
        }

    return execute(db, auth.user_id, "delete:" + case_id, key, body.model_dump(), save)
