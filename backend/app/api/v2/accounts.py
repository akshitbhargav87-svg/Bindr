import time
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.app.api.v2.platform import Key
from backend.app.api.v2.jobs import recent
from backend.app.core.auth import get_current_session, SessionData
from backend.app.core.database import get_db
from backend.app.models.account import AccountSession
from backend.app.models.case import Case
from backend.app.models.workflow import CaseControl
from backend.app.models.jobs import Job, Export
from backend.app.models.integrations import (
    AccountControl,
    AggregateConsent,
    IntakeAlias,
)
from backend.app.schemas.jobs import DeleteAccount
from backend.app.services.platform.operations import execute
from backend.app.services.platform.jobs import enqueue, view
from backend.app.services.platform.accounts import ensure_active
from backend.app.services.case_state import fail

router = APIRouter(prefix="/api/v2/account", tags=["Account privacy v2"])


@router.post("/export", status_code=202)
def export(
    key: Key,
    auth: SessionData = Depends(get_current_session),
    db: Session = Depends(get_db),
):
    recent(auth)
    ensure_active(db, auth.user_id)

    def save():
        row = Export(owner_id=auth.user_id, expires_at=int(time.time()) + 86400)
        db.add(row)
        db.flush()
        job = enqueue(db, auth.user_id, "account_export", {"export_id": row.id})
        return {"export_id": row.id, **view(job)}

    return execute(db, auth.user_id, "account.export", key, {}, save)


@router.delete("", status_code=202)
def delete(
    body: DeleteAccount,
    key: Key,
    auth: SessionData = Depends(get_current_session),
    db: Session = Depends(get_db),
):
    recent(auth)
    ensure_active(db, auth.user_id)

    def save():
        control = AccountControl(
            owner_id=auth.user_id, state="deleting", deleted_at=int(time.time())
        )
        db.add(control)
        db.query(AccountSession).filter_by(account_id=auth.user_id).update(
            {"revoked_at": int(time.time())}
        )
        db.query(Job).filter_by(owner_id=auth.user_id).update(
            {"state": "cancelled", "payload": "{}", "result": None}
        )
        db.query(IntakeAlias).filter_by(owner_id=auth.user_id).update(
            {"revoked_at": int(time.time())}
        )
        consent = db.get(AggregateConsent, auth.user_id)
        if consent:
            consent.enabled = 0
            consent.version += 1
        for case in (
            db.query(Case).filter_by(owner_id=auth.user_id).with_for_update().all()
        ):
            cc = db.get(CaseControl, case.id) or CaseControl(
                case_id=case.id, owner_id=auth.user_id
            )
            cc.state = "deleting"
            db.add(cc)
            case.owner_id = "deleted:" + case.id
            case.version += 1
        job = enqueue(db, auth.user_id, "delete_account", {})
        return {
            **view(job),
            "normal_access": "revoked",
            "retention": "Identity, SQL and private object deletion retries in the worker. Backup aging and third-party copies have separate limits.",
        }

    return execute(db, auth.user_id, "account.delete", key, body.model_dump(), save)
