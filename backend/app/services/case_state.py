"""Authoritative status projection and compare-and-swap case mutations."""
import uuid
from datetime import datetime, timezone
from fastapi import HTTPException
from sqlalchemy import update
from sqlalchemy.orm.attributes import set_committed_value
from backend.app.models.case import Case


def fail(status, code, message):
    raise HTTPException(status, detail={"error": {"code": code, "message": message,
                         "details": [], "request_id": str(uuid.uuid4())}})


def claim_version(db, case, expected):
    """Claim a case version inside the same transaction as all associated writes."""
    old = case.version
    if expected is not None and expected != old:
        fail(409, "VERSION_CONFLICT", "This case changed. Refresh and review the latest record.")
    count = db.execute(update(Case).where(Case.id == case.id, Case.version == old,
                       Case.status != "resolved").values(version=old + 1),
                       execution_options={"synchronize_session": False}).rowcount
    if count != 1:
        db.rollback()
        fail(409, "VERSION_CONFLICT", "This case changed. Refresh and review the latest record.")
    set_committed_value(case, "version", old + 1)


def displayed_case(case):
    from backend.app.schemas.contract import CaseSchema
    value = CaseSchema.model_validate(case)
    if case.status != "resolved":
        now = datetime.now(timezone.utc)
        overdue = False
        for commitment in case.commitments:
            if commitment.status == "active" and commitment.due_at:
                try:
                    overdue |= datetime.fromisoformat(commitment.due_at.replace("Z", "+00:00")) < now
                except ValueError:
                    pass
        value.status = "overdue" if overdue else "open"
    return value
