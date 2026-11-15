"""Private, immutable snapshot exports; originals are never rendered back into originals."""

import hashlib
import html
import io
import json
import time
import zipfile
from backend.app.models.jobs import Export
from backend.app.services.platform.operations import canonical
from backend.app.services.platform.workflow import owned_case, snapshot, sources
from backend.app.services.case_state import fail
from backend.app.services.storage import storage_service
from backend.app.services.platform import artifacts


def pdf_bytes(record, wording, previews=None):
    from backend.app.services.platform.pdf_report import render

    return render(record, wording, previews)


def build(db, job):
    body = json.loads(job.payload)
    resource = db.get(Export, body["export_id"])
    if (
        resource is None
        or resource.owner_id != job.owner_id
        or resource.expires_at < int(time.time())
    ):
        fail(404, "NOT_FOUND", "Export expired.")
    case = owned_case(db, job.owner_id, job.case_id, lock=True)
    if case.version != job.case_version:
        fail(
            409,
            "VERSION_CONFLICT",
            "Export facts changed. Review and request a new snapshot.",
        )
    rows = sources(db, case.id, body["source_ids"])
    record = snapshot(db, case)
    selected = body.get("obligation_ids")
    if selected is not None:
        if set(selected) - {o["id"] for o in record["obligations"]}:
            fail(
                422,
                "INVALID_SELECTION",
                "An obligation is not present in this case snapshot.",
            )
        record["obligations"] = [
            o for o in record["obligations"] if o["id"] in selected
        ]
        record["events"] = []
        totals = {}
        for value in record["obligations"]:
            terms = value["terms"]
            if terms["amount_minor"] is not None and value["state"] == "active":
                bucket = totals.setdefault(
                    terms["currency"],
                    {"promised_minor": 0, "received_minor": 0, "outstanding_minor": 0},
                )
                bucket["promised_minor"] += terms["amount_minor"]
                bucket["received_minor"] += value["received_minor"]
                bucket["outstanding_minor"] += value["outstanding_minor"]
        record["projection"]["money_by_currency"] = totals
        record["projection"]["status"] = "selected_snapshot_not_complete_case_status"
        record["projection"]["health"] = "selected_snapshot"
        record["legacy_commitments"] = []
    if not body.get("include_history", True):
        record["events"] = []
    record["projection"]["as_of"] = job.created_at
    originals = {}
    for row in rows:
        content = storage_service.read_file(row.storage_key)
        if hashlib.sha256(content).hexdigest() != row.sha256:
            fail(409, "INTEGRITY_ERROR", "An original digest does not match.")
        originals["originals/" + row.id + ".bin"] = content
    from backend.app.models.platform import EvidenceCommunication

    record["evidence"] = [
        {
            "id": r.id,
            "filename": r.filename,
            "media_type": r.media_type,
            "sha256": r.sha256,
            "created_at": r.created_at,
            "communication": (
                json.loads(db.get(EvidenceCommunication, r.id).payload)
                if db.get(EvidenceCommunication, r.id)
                else None
            ),
        }
        for r in rows
    ]
    record["export"] = {
        "case_version": case.version,
        "export_id": resource.id,
        "created_at": record["projection"]["as_of"],
        "timestamp_kind": "bindr_receipt_not_external_attestation",
        "warnings": [
            "Sharing the downloaded bundle discloses its contents.",
            "No authenticity or legal admissibility certification.",
        ],
    }
    referenced = {s["evidence_id"] for o in record["obligations"] for s in o["sources"]}
    if referenced - set(body["source_ids"]):
        record["export"]["warnings"].append(
            "Some cited originals were not selected for this export."
        )
    record["export"]["warnings"].append(
        "Selected originals can contain additional text; they are not redacted previews."
    )
    previews = []
    record["export"]["preview_warnings"] = []
    for row in rows[:3]:
        try:
            content = originals["originals/" + row.id + ".bin"]
            preview = None
            if row.media_type.startswith("image/"):
                from PIL import Image

                image = Image.open(io.BytesIO(content))
                if image.width * image.height > 12000000:
                    raise ValueError("Image pixel limit")
                image.thumbnail((900, 600))
                buffer = io.BytesIO()
                image.convert("RGB").save(buffer, format="PNG")
                preview = buffer.getvalue()
            elif row.media_type == "application/pdf":
                import pymupdf

                with pymupdf.open(stream=content, filetype="pdf") as document:
                    page = document[0]
                    scale = min(1.2, 1000 / max(page.rect.width, page.rect.height))
                    preview = page.get_pixmap(
                        matrix=pymupdf.Matrix(scale, scale), alpha=False
                    ).tobytes("png")
            if preview:
                previews.append((row.filename, preview))
        except Exception:
            record["export"]["preview_warnings"].append(
                {
                    "evidence_id": row.id,
                    "warning": "Preview unavailable; original remains in bundle.",
                }
            )
    files = {"record.json": canonical(record).encode("utf-8")}
    if body.get("trusted_timestamp"):
        from backend.app.services.platform.timestamps import issue

        files["record.tsr"] = issue(files["record.json"])
    if "pdf" in body["formats"] or "bundle" in body["formats"]:
        files["case.pdf"] = pdf_bytes(record, body["reviewed_wording"], previews)
    if "bundle" in body["formats"]:
        files.update(originals)
    manifest = {
        "schema_version": 1,
        "export_id": resource.id,
        "case_version": case.version,
        "files": {
            name: hashlib.sha256(data).hexdigest() for name, data in files.items()
        },
        "timestamp_kind": "bindr_receipt_not_external_attestation",
    }
    if body.get("trusted_timestamp"):
        manifest["external_timestamp"] = {
            "format": "RFC3161",
            "target": "record.json",
            "receipt": "record.tsr",
            "trust_anchor_sha256": __import__("os").environ["TSA_CA_SHA256"],
        }
    if body["formats"] == ["data"]:
        content = files["record.json"]
        media = "application/json"
    elif body["formats"] == ["pdf"]:
        content = files["case.pdf"]
        media = "application/pdf"
    else:
        files["manifest.json"] = canonical(manifest).encode()
        output = io.BytesIO()
        with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
            for name, data in files.items():
                archive.writestr(name, data)
        content = output.getvalue()
        media = "application/zip"
    # Deterministic resource key. A retry reuses a verified previously written result.
    key = resource.id + ".bin"
    try:
        existing = artifacts.read(key)
        # Do not overwrite after uncertain commit; compare to persisted snapshot identity.
        if media == "application/zip":
            with zipfile.ZipFile(io.BytesIO(existing)) as archive:
                prior = json.loads(archive.read("manifest.json"))
            if (
                prior["export_id"] != resource.id
                or prior["case_version"] != case.version
            ):
                raise ValueError("Export identity mismatch")
            manifest = prior
        else:
            # Regeneration changes receipt timestamp, so reuse the first immutable bytes.
            if not existing:
                raise ValueError("Empty prior export")
        content = existing
    except Exception as exc:
        from backend.app.services.storage import EvidenceNotFoundError

        if not isinstance(exc, EvidenceNotFoundError):
            raise
        artifacts.save(content, resource.id)
    resource.storage_key = key
    resource.sha256 = hashlib.sha256(content).hexdigest()
    resource.media_type = media
    resource.manifest = canonical(manifest)
    resource.state = "succeeded"
    return {"export_id": resource.id, "case_version": case.version}


def expire_exports(db, now=None):
    now = int(time.time()) if now is None else now
    from backend.app.services.platform.deletion import delete_object
    from backend.app.models.jobs import Job

    for row in (
        db.query(Export)
        .filter(Export.expires_at <= now, Export.state != "expired")
        .all()
    ):
        delete_object(row.storage_key or row.id + ".bin")
        row.state = "expired"
        row.storage_key = None
        row.manifest = None
        # Cancel only the job building this export, not unrelated case work.
        for job in (
            db.query(Job)
            .filter(
                Job.kind.in_(["export", "account_export"]),
                Job.owner_id == row.owner_id,
                Job.state.in_(["queued", "running"]),
            )
            .all()
        ):
            if json.loads(job.payload).get("export_id") == row.id:
                job.state = "cancelled"
                job.stage = "export_expired"
                job.payload = "{}"
    db.commit()
