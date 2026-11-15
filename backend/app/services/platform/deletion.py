"""Retryable private storage + SQL cleanup. A case is hidden before this runs."""

import json
from backend.app.models.case import Case
from backend.app.models.evidence import Evidence
from backend.app.models.account import AccountDraft
from backend.app.models.platform import EvidenceCommunication, Operation, CaptureDraft
from backend.app.models.workflow import CaseControl, CaseEvent, Obligation, Proposal
from backend.app.models.jobs import Job, Export
from backend.app.services.storage import (
    storage_service,
    EvidenceNotFoundError,
    StorageError,
)
from backend.app.services.case_state import fail


def delete_object(key):
    from backend.app.services.platform.artifacts import read

    try:
        read(key)
    except EvidenceNotFoundError:
        return
    if not storage_service.delete_file(key):
        raise StorageError("Private cleanup must be retried.")


def cleanup_case(db, job):
    control = db.get(CaseControl, job.case_id)
    if control is None:
        return {"deleted": True}
    if control.state != "deleting" or control.owner_id != job.owner_id:
        fail(409, "INVALID_DELETION", "Deletion authorization changed.")
    case = db.get(Case, job.case_id)
    if case is None:
        return {"deleted": True}
    evidence = db.query(Evidence).filter_by(case_id=case.id).all()
    exports = db.query(Export).filter_by(case_id=case.id).all()
    from backend.app.models.integrations import Intake, IntakeAlias, ProviderLink
    from backend.app.models.pairing import CaptureCapability

    intake = db.query(Intake).filter_by(case_id=case.id, owner_id=job.owner_id).all()
    aliases = (
        db.query(IntakeAlias).filter_by(case_id=case.id, owner_id=job.owner_id).all()
    )
    for row in evidence + exports + intake:
        if row.storage_key:
            delete_object(row.storage_key)
    for draft in db.query(CaptureDraft).filter_by(owner_id=job.owner_id).all():
        if any(
            e.id in json.loads(draft.payload).get("evidence_ids", []) for e in evidence
        ):
            db.delete(draft)
    # Remove PII in completed operation results referencing this case, while leaving
    # unrelated case operations intact. Hashes alone do not contain source content.
    for op in db.query(Operation).filter_by(owner_id=job.owner_id).all():
        if op.scope == "delete:" + case.id:
            continue  # Retain only the deletion receipt, never deleted case contents.
        if case.id in op.scope or (
            op.result
            and (case.id in op.result or any(a.digest in op.result for a in aliases))
        ):
            db.delete(op)
    db.query(ProviderLink).filter(
        ProviderLink.alias_digest.in_([a.digest for a in aliases])
    ).delete(synchronize_session=False)
    from backend.app.models.integrations import MessageIdentity

    db.query(MessageIdentity).filter_by(
        owner_id=job.owner_id, case_scope=case.id
    ).delete(synchronize_session=False)
    for row in aliases + intake:
        db.delete(row)
    db.query(CaptureCapability).filter_by(
        case_id=case.id, owner_id=job.owner_id
    ).delete(synchronize_session=False)
    for model, field in [(EvidenceCommunication, EvidenceCommunication.evidence_id)]:
        db.query(model).filter(field.in_([e.id for e in evidence])).delete(
            synchronize_session=False
        )
    from backend.app.models.aggregates import CompanyAssignment

    for model in (
        CompanyAssignment,
        AccountDraft,
        CaseEvent,
        Proposal,
        Obligation,
        Export,
    ):
        db.query(model).filter(model.case_id == case.id).delete(
            synchronize_session=False
        )
    # Cancelled jobs no longer retain selected evidence / reviewed wording.
    db.query(Job).filter(Job.case_id == case.id, Job.id != job.id).update(
        {"payload": "{}", "result": None}, synchronize_session=False
    )
    db.delete(control)
    db.flush()
    db.delete(case)
    db.flush()
    return {
        "deleted": True,
        "backup_retention": "Production backup retention requires owner confirmation; existing copies may age out separately.",
    }
