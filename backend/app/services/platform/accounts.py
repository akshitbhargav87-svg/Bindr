"""Account export/deletion services; provider identity deletion is an explicit owner-requested job."""

import hashlib
import io
import json
import time
import zipfile
from types import SimpleNamespace
from backend.app.models.account import (
    Account,
    AccountSession,
    AccountPreferences,
    AccountDraft,
    WorkspaceClaim,
)
from backend.app.models.case import Case
from backend.app.models.evidence import Evidence
from backend.app.models.platform import CaptureDraft, Operation
from backend.app.models.jobs import Job, Export, NotificationPreferences
from backend.app.models.integrations import (
    AccountControl,
    Connection,
    OAuthState,
    IntakeAlias,
    Intake,
    AggregateConsent,
    ProviderLink,
)
from backend.app.models.workflow import CaseControl
from backend.app.services.platform.workflow import snapshot
from backend.app.services.platform.operations import canonical
from backend.app.services.platform.deletion import cleanup_case, delete_object
from backend.app.services.platform import artifacts
from backend.app.services.storage import storage_service
from backend.app.services.case_state import fail


def ensure_active(db, owner):
    row = db.get(AccountControl, owner)
    if row and row.state != "active":
        fail(401, "ACCOUNT_DELETING", "This account is being deleted.")


def export_account(db, job):
    ensure_active(db, job.owner_id)
    resource = db.get(Export, json.loads(job.payload)["export_id"])
    if resource is None or resource.owner_id != job.owner_id:
        fail(404, "NOT_FOUND", "Export not found.")
    account = db.get(Account, job.owner_id)
    if account is None:
        fail(404, "NOT_FOUND", "Account not found.")
    cases = (
        db.query(Case)
        .filter_by(owner_id=job.owner_id)
        .order_by(Case.id)
        .with_for_update()
        .all()
    )
    files = {}
    record = {
        "account": {
            "id": account.id,
            "email": account.email,
            "display_name": account.display_name,
        },
        "cases": [snapshot(db, c) for c in cases],
        "capture_drafts": [
            {"id": d.id, "version": d.version, "capture": json.loads(d.payload)}
            for d in db.query(CaptureDraft).filter_by(owner_id=job.owner_id).all()
        ],
        "complaint_drafts": [
            {
                "case_id": d.case_id,
                "version": d.version,
                "payload": json.loads(d.payload),
            }
            for d in db.query(AccountDraft).filter_by(account_id=job.owner_id).all()
        ],
        "preferences": (
            json.loads(db.get(AccountPreferences, job.owner_id).payload)
            if db.get(AccountPreferences, job.owner_id)
            else {}
        ),
        "credentials_included": False,
        "receipt_time": job.created_at,
    }
    for evidence in (
        db.query(Evidence).join(Case).filter(Case.owner_id == job.owner_id).all()
    ):
        content = storage_service.read_file(evidence.storage_key)
        if hashlib.sha256(content).hexdigest() != evidence.sha256:
            fail(409, "INTEGRITY_ERROR", "Original digest mismatch.")
        files["originals/" + evidence.id + ".bin"] = content
    for item in db.query(Intake).filter_by(owner_id=job.owner_id).all():
        files["intake/" + item.id + ".bin"] = storage_service.read_file(
            item.storage_key
        )
    files["record.json"] = canonical(record).encode()
    manifest = {
        "schema_version": 1,
        "files": {n: hashlib.sha256(v).hexdigest() for n, v in files.items()},
        "timestamp_kind": "bindr_receipt_not_external_attestation",
    }
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as bundle:
        for name, value in files.items():
            bundle.writestr(name, value)
        bundle.writestr("manifest.json", canonical(manifest))
    content = output.getvalue()
    key = resource.id + ".bin"
    from backend.app.services.storage import EvidenceNotFoundError

    try:
        content = artifacts.read(key)
    except EvidenceNotFoundError:
        artifacts.save(content, resource.id)
    resource.state = "succeeded"
    resource.storage_key = key
    resource.sha256 = hashlib.sha256(content).hexdigest()
    resource.media_type = "application/zip"
    resource.manifest = canonical(manifest)
    return {"export_id": resource.id}


def cleanup_account(db, job):
    owner = job.owner_id
    control = db.get(AccountControl, owner)
    if control and control.state == "deleted":
        return {"deleted": True}
    if control is None or control.state != "deleting":
        fail(409, "INVALID_DELETION", "Account deletion is not authorized.")
    account = db.get(Account, owner)
    if account is None:
        return {"deleted": True}
    # This does not run during test/setup. Only an explicit authenticated DELETE creates
    # this job. The identity adapter is stubbed in tests; real deletion needs live acceptance.
    from backend.app.services.identity import get_identity_provider

    get_identity_provider().delete(account.provider_uid)
    from backend.app.services.platform.connectors import revoke_gmail

    revoke_gmail(db, owner)
    controls = db.query(CaseControl).filter_by(owner_id=owner, state="deleting").all()
    for case_control in controls:
        cleanup_case(
            db, SimpleNamespace(case_id=case_control.case_id, owner_id=owner, id=job.id)
        )
    for row in db.query(Export).filter_by(owner_id=owner).all():
        if row.storage_key:
            delete_object(row.storage_key)
        db.delete(row)
    for row in db.query(Intake).filter_by(owner_id=owner).all():
        delete_object(row.storage_key)
        db.delete(row)
    from backend.app.models.devices import PushDevice
    from backend.app.models.pairing import CaptureCapability

    from backend.app.models.integrations import MessageIdentity

    for model, field in [
        (MessageIdentity, MessageIdentity.owner_id),
        (PushDevice, PushDevice.owner_id),
        (CaptureCapability, CaptureCapability.owner_id),
        (AccountSession, AccountSession.account_id),
        (AccountPreferences, AccountPreferences.account_id),
        (AccountDraft, AccountDraft.account_id),
        (WorkspaceClaim, WorkspaceClaim.account_id),
        (CaptureDraft, CaptureDraft.owner_id),
        (Operation, Operation.owner_id),
        (Connection, Connection.owner_id),
        (OAuthState, OAuthState.owner_id),
        (IntakeAlias, IntakeAlias.owner_id),
        (NotificationPreferences, NotificationPreferences.owner_id),
        (AggregateConsent, AggregateConsent.owner_id),
        (ProviderLink, ProviderLink.owner_id),
    ]:
        db.query(model).filter(field == owner).delete(synchronize_session=False)
    db.query(Job).filter(Job.owner_id == owner, Job.id != job.id).delete(
        synchronize_session=False
    )
    db.delete(account)
    db.flush()
    # Tombstone contains only a random internal ID; no email/provider ID or evidence.
    control.state = "deleted"
    return {
        "deleted": True,
        "backup_retention": "Owner-confirmed production backup aging still applies; third-party copies cannot be recalled.",
    }
