"""Leased jobs with bounded retries. Side-effecting sends require provider reconciliation."""

import json
import time
import uuid
from sqlalchemy import update, or_, and_
from backend.app.models.jobs import Job
from backend.app.services.platform.operations import canonical


def enqueue(
    db, owner, kind, payload, case_id=None, version=None, run_at=None, job_id=None
):
    if job_id:
        old = db.get(Job, job_id)
        if old:
            if old.state == "succeeded" or old.error_code == "DELIVERY_UNCERTAIN":
                return old
            old.state = "queued"
            old.case_version = version
            old.payload = canonical(payload)
            old.run_at = run_at or int(time.time())
            old.lease_token = None
            return old
    if (
        db.query(Job)
        .filter(Job.owner_id == owner, Job.state.in_(["queued", "running"]))
        .count()
        >= 250
    ):
        from backend.app.services.case_state import fail

        fail(429, "JOB_LIMIT", "Too many pending jobs for this account.")
    row = Job(
        owner_id=owner,
        kind=kind,
        payload=canonical(payload),
        case_id=case_id,
        case_version=version,
        run_at=run_at or int(time.time()),
    )
    if job_id:
        row.id = job_id
    db.add(row)
    db.flush()
    return row


def cancel_case_jobs(db, case_id):
    from backend.app.models.jobs import Export

    db.query(Export).filter(Export.case_id == case_id, Export.state == "queued").update(
        {"state": "cancelled"}, synchronize_session=False
    )
    db.execute(
        update(Job)
        .where(
            Job.case_id == case_id,
            Job.state.in_(["queued", "running", "review_required"]),
        )
        .values(state="cancelled", stage="obsolete", lease_token=None)
    )


def view(row):
    return {
        "job": {
            "id": row.id,
            "state": row.state,
            "stage": row.stage,
            "retryable": row.state == "queued",
            "error": {"code": row.error_code} if row.error_code else None,
            "request_id": row.id,
            "resource": json.loads(row.result) if row.result else None,
            "case_version": row.case_version,
        }
    }


def run_one(factory, handlers, now=None):
    """Claim in a short transaction; handlers must use fresh authorization/version checks.

    A crashed send is never automatically resent. Other handlers must be idempotent.
    Lease fencing prevents a stale worker from recording success after cancellation.
    """
    now = int(time.time()) if now is None else now
    token = str(uuid.uuid4())
    with factory() as db:
        expired = (
            db.query(Job).filter(Job.state == "running", Job.lease_until < now).all()
        )
        for row in expired:
            if row.kind in ("send", "notification") or json.loads(row.payload).get(
                "trusted_timestamp", False
            ):
                row.state = "failed"
                row.stage = "reconcile_delivery"
                row.error_code = "DELIVERY_UNCERTAIN"
            else:
                row.state = "queued"
                row.stage = "retry_after_worker_restart"
        db.commit()
        row = (
            db.query(Job)
            .filter(Job.state == "queued", Job.run_at <= now)
            .order_by(Job.run_at, Job.id)
            .first()
        )
        if row is None:
            return None
        jid = row.id
        count = db.execute(
            update(Job)
            .where(Job.id == jid, Job.state == "queued")
            .values(
                state="running",
                stage="processing",
                lease_until=now + 300,
                lease_token=token,
                attempts=Job.attempts + 1,
            ),
            execution_options={"synchronize_session": False},
        ).rowcount
        db.commit()
        if count != 1:
            return None
    try:
        with factory() as db:
            row = db.get(Job, jid)
            if row.state != "running" or row.lease_token != token:
                return jid
            handler = handlers.get(row.kind)
            if handler is None:
                row.state = "failed"
                row.stage = "configuration_required"
                row.error_code = "PROVIDER_NOT_CONFIGURED"
                db.commit()
                return jid
            result = handler(db, row)
            # Handler SQL changes and job success share a transaction; durable external work
            # must be deterministic/reconciled. A concurrent cancel wins via this predicate.
            changed = db.execute(
                update(Job)
                .where(Job.id == jid, Job.state == "running", Job.lease_token == token)
                .values(
                    state="succeeded",
                    stage="complete",
                    result=canonical(result),
                    payload="{}",
                    lease_token=None,
                ),
                execution_options={"synchronize_session": False},
            ).rowcount
            if changed != 1:
                db.rollback()
            else:
                db.commit()
    except Exception as exc:
        with factory() as db:
            row = db.get(Job, jid)
            if row and row.state == "running" and row.lease_token == token:
                status = getattr(exc, "status_code", None)
                row.error_code = (
                    "OBSOLETE_JOB"
                    if status in (404, 409)
                    else (
                        "PROVIDER_NOT_CONFIGURED"
                        if status == 503
                        else (
                            "DELIVERY_UNCERTAIN"
                            if row.kind in ("send", "notification")
                            else "JOB_FAILED"
                        )
                    )
                )  # no exception/provider/source payload in public diagnostics
                row.lease_token = None
                paid_timestamp = json.loads(row.payload).get("trusted_timestamp", False)
                row.state = (
                    "cancelled"
                    if row.error_code == "OBSOLETE_JOB"
                    else (
                        "queued"
                        if row.kind not in ("send", "notification")
                        and not paid_timestamp
                        and row.attempts < 3
                        else "failed"
                    )
                )
                row.stage = (
                    "reconcile_delivery"
                    if row.error_code == "DELIVERY_UNCERTAIN"
                    else (
                        "retry_scheduled"
                        if row.state == "queued"
                        else (
                            "configuration_required"
                            if row.error_code == "PROVIDER_NOT_CONFIGURED"
                            else "needs_review"
                        )
                    )
                )
                row.run_at = now + min(300, 2**row.attempts * 10)
                db.commit()
    return jid
