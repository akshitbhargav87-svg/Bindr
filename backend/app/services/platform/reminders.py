"""Durable reminder scheduling. External channels need explicit opt-in and activation."""

import json
import uuid
import hashlib
import time
from datetime import datetime, timedelta
from backend.app.models.jobs import NotificationPreferences, Job
from backend.app.models.workflow import Obligation, CaseControl
from backend.app.models.devices import PushDevice
from backend.app.services.platform.workflow import owned_case, ledger
from backend.app.services.platform.jobs import enqueue
from backend.app.services.case_state import fail


def schedule(db, case, owner):
    db.query(Job).filter(
        Job.case_id == case.id,
        Job.kind.in_(["reminder", "notification", "follow_up"]),
        Job.state.in_(["queued", "running"]),
    ).update(
        {"state": "cancelled", "stage": "rescheduled", "lease_token": None},
        synchronize_session=False,
    )
    db.flush()
    control = db.get(CaseControl, case.id)
    if (
        case.status == "resolved"
        or control
        and control.state in ("archived", "deleting")
    ):
        return
    prefs = db.get(NotificationPreferences, owner)
    if prefs is None:
        return
    preference = json.loads(prefs.payload)
    if not any(
        preference.get(c, False) for c in ["in_app", "email", "push", "whatsapp"]
    ):
        return
    _, receipts, full = ledger(db, case.id)
    for obligation in (
        db.query(Obligation).filter_by(case_id=case.id, state="active").all()
    ):
        terms = json.loads(obligation.terms)
        if (
            not terms["due_at"]
            or (terms["amount_minor"] is None and obligation.root_id in full)
            or terms["amount_minor"] is not None
            and receipts.get(obligation.root_id, 0) >= terms["amount_minor"]
        ):
            continue
        due = datetime.fromisoformat(terms["due_at"].replace("Z", "+00:00"))
        seed = (
            owner
            + ":"
            + obligation.id
            + ":"
            + hashlib.sha256(obligation.terms.encode()).hexdigest()
            + ":"
            + str(prefs.version)
        )
        channels = []
        if preference.get("in_app", True):
            channels.append(("in_app", None))
        if preference.get("email"):
            channels.append(("email", None))
        if preference.get("whatsapp"):
            channels.append(("whatsapp", None))
        if preference.get("push"):
            channels.extend(
                ("push", d.id)
                for d in db.query(PushDevice).filter_by(owner_id=owner, active=1).all()
            )
        for offset in preference["days_before"]:
            when = int((due - timedelta(days=offset)).timestamp())
            if when < int(time.time()) and offset != 0:
                continue
            for channel, device in channels:
                jid = str(
                    uuid.uuid5(
                        uuid.NAMESPACE_URL,
                        seed + ":" + channel + ":" + str(device) + ":" + str(offset),
                    )
                )
                enqueue(
                    db,
                    owner,
                    "reminder" if channel == "in_app" else "notification",
                    {
                        "obligation_id": obligation.id,
                        "preferences_version": prefs.version,
                        "channel": channel,
                        "device_id": device,
                    },
                    case.id,
                    case.version,
                    when,
                    job_id=jid,
                )
        if preference.get("follow_up_days"):
            enqueue(
                db,
                owner,
                "follow_up",
                {"obligation_id": obligation.id, "preferences_version": prefs.version},
                case.id,
                case.version,
                int((due + timedelta(days=preference["follow_up_days"])).timestamp()),
                job_id=str(uuid.uuid5(uuid.NAMESPACE_URL, seed + ":follow_up")),
            )


def deliver_prompt(db, job):
    case = owned_case(db, job.owner_id, job.case_id)
    control = db.get(CaseControl, case.id)
    if (
        case.status == "resolved"
        or control
        and control.state in ("archived", "deleting")
    ):
        fail(409, "OBSOLETE_JOB", "Case is closed or archived.")
    if case.version != job.case_version:
        fail(409, "OBSOLETE_JOB", "Case changed; reminder requires rescheduling.")
    data = json.loads(job.payload)
    prefs = db.get(NotificationPreferences, job.owner_id)
    if prefs is None or prefs.version != data["preferences_version"]:
        fail(409, "OBSOLETE_JOB", "Preferences changed.")
    obligation = (
        db.query(Obligation)
        .filter_by(id=data["obligation_id"], case_id=case.id, state="active")
        .first()
    )
    if obligation is None:
        fail(409, "OBSOLETE_JOB", "Promise revised/revoked.")
    terms = json.loads(obligation.terms)
    _, receipts, fulfilled = ledger(db, case.id)
    if (terms["amount_minor"] is None and obligation.root_id in fulfilled) or (
        terms["amount_minor"] is not None
        and receipts.get(obligation.root_id, 0) >= terms["amount_minor"]
    ):
        fail(409, "OBSOLETE_JOB", "Already fulfilled.")
    return {
        "obligation_id": obligation.id,
        "action": "review_follow_up" if job.kind == "follow_up" else "review_deadline",
        "channel": "in_app",
        "external_delivery": False,
        "case_version": case.version,
    }
