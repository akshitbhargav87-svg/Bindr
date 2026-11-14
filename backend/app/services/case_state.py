"""Authoritative status projection and compare-and-swap case mutations.

Security & Concurrency Invariants:
----------------------------------
1. Optimistic Concurrency Control (CAS):
   Case mutations (evidence upload, extraction review, resolution) require the client's
   current known version (`expected_version`). Modifications execute an atomic SQL
   compare-and-swap:
       UPDATE cases SET version = version + 1
       WHERE id = :case_id AND version = :expected_version AND status != 'resolved'
   If another transaction incremented the version concurrently, the update affects 0 rows,
   triggering an immediate transaction rollback and HTTP 409 VERSION_CONFLICT.

2. Terminal State Immutability:
   A resolved case (`status == 'resolved'`) is closed to further mutations. All mutating
   operations are rejected with HTTP 409 CASE_RESOLVED to prevent retroactive tampering
   with confirmed case outcomes.

3. Dynamic Status Projection:
   Case status is projected authoritatively at read time: active commitments with past-due
   deadlines project the case status as 'overdue' without modifying persistent storage.
"""
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
    """
    Claim a case version inside the same database transaction as all associated writes.

    Invariant:
    - Verifies that `expected` equals `case.version`.
    - Atomically increments `version` via SQL compare-and-swap (CAS).
    - If a concurrent request modified the case (rowcount != 1), rolls back the transaction
      and raises HTTP 409 VERSION_CONFLICT to prevent lost updates.
    - Rejects modifications if the case status is 'resolved' (HTTP 409 VERSION_CONFLICT).
    """
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
    """
    Compute authoritative case projection for client presentation.

    Invariant:
    - If case is resolved, terminal status 'resolved' is strictly preserved.
    - If case is open and has an active commitment past its due date, status is
      projected as 'overdue' dynamically.
    - Leaves underlying database rows intact while ensuring clients see accurate timeline state.
    """
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
