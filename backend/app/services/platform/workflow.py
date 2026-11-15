"""Owned snapshots and append-only outcomes. All callers mutate inside one operation transaction."""

import json
from datetime import datetime, timezone
from sqlalchemy import update
from backend.app.models.case import Case
from backend.app.models.evidence import Evidence
from backend.app.models.workflow import Obligation, CaseEvent, CaseControl
from backend.app.services.case_state import fail
from backend.app.services.platform.operations import canonical


def owned_case(db, owner, case_id, lock=False):
    query = db.query(Case).filter_by(id=case_id, owner_id=owner)
    if lock:
        query = query.with_for_update()
    row = query.first()
    if row is None:
        fail(404, "NOT_FOUND", "Case not found.")
    return row


def claim(db, case, expected, allow_closed=False):
    if case.status == "resolved" and not allow_closed:
        fail(
            409,
            "CASE_RESOLVED",
            "Reopen this case explicitly before editing its obligations.",
        )
    count = db.execute(
        update(Case)
        .where(
            Case.id == case.id,
            Case.owner_id == case.owner_id,
            Case.version == expected,
            True if allow_closed else Case.status != "resolved",
        )
        .values(version=expected + 1),
        execution_options={"synchronize_session": False},
    ).rowcount
    if count != 1:
        fail(409, "VERSION_CONFLICT", "Refresh and review the current case.")
    db.expire(case)
    from backend.app.services.platform.jobs import cancel_case_jobs

    cancel_case_jobs(db, case.id)
    from backend.app.services.platform.reminders import schedule

    schedule(db, case, case.owner_id)


def sources(db, case_id, refs):
    ids = [r.evidence_id if hasattr(r, "evidence_id") else r for r in refs]
    if len(ids) != len(set(ids)):
        fail(422, "VALIDATION_ERROR", "Duplicate evidence IDs.")
    rows = (
        db.query(Evidence)
        .filter(Evidence.case_id == case_id, Evidence.id.in_(ids))
        .all()
        if ids
        else []
    )
    if {e.id for e in rows} != set(ids):
        fail(404, "NOT_FOUND", "Source not found in this case.")
    # Verbatim checking for text originals. Document/audio page/segment verification is B's
    # pure processor boundary; HTTP extraction rechecks its evidence identity below.
    from backend.app.services.storage import storage_service

    for ref in refs:
        if hasattr(ref, "quote"):
            row = next(e for e in rows if e.id == ref.evidence_id)
            cache = db.info.setdefault("citation_documents", {})
            identity = (row.id, row.sha256)
            if identity not in cache:
                from backend.app.ai.document_processor import DocumentProcessor

                suffix = {
                    "text/plain": ".txt",
                    "image/png": ".png",
                    "image/jpeg": ".jpg",
                    "application/pdf": ".pdf",
                }.get(row.media_type)
                if not suffix:
                    fail(
                        422,
                        "INVALID_CITATION",
                        "This source type has no supported citation processor.",
                    )
                from backend.app.services.platform.media import original

                cache[identity] = DocumentProcessor().process_bytes(
                    original(row), "source" + suffix
                )
            document = cache[identity]
            haystack = (
                next((p.text for p in document.pages if p.page_number == ref.page), "")
                if ref.page
                else document.raw_text
            )
            if ref.quote not in haystack:
                fail(
                    422,
                    "INVALID_CITATION",
                    "Quotation is not present in its attributed original/page.",
                )
    by_id = {row.id: row for row in rows}
    return [by_id[eid] for eid in ids]


def event(db, case_id, kind, payload):
    from sqlalchemy import func

    sequence = (
        db.query(func.coalesce(func.max(CaseEvent.sequence), 0))
        .filter(CaseEvent.case_id == case_id)
        .scalar()
        + 1
    )
    row = CaseEvent(
        case_id=case_id,
        kind=kind,
        payload=canonical(payload),
        case_version=db.get(Case, case_id).version,
        sequence=sequence,
    )
    db.add(row)
    db.flush()
    return row


def ledger(db, case_id):
    events = (
        db.query(CaseEvent)
        .filter_by(case_id=case_id)
        .order_by(
            CaseEvent.sequence.asc().nulls_first(), CaseEvent.created_at, CaseEvent.id
        )
        .all()
    )
    voided = {
        json.loads(e.payload)["corrects_event_id"]
        for e in events
        if e.kind == "correction"
    }
    receipts, fulfilled = {}, set()
    for e in events:
        if e.id in voided or e.kind not in ("partial", "full"):
            continue
        for a in json.loads(e.payload)["allocations"]:
            oid = a["root_id"]
            receipts[oid] = receipts.get(oid, 0) + (a["amount_minor"] or 0)
            if e.kind == "full":
                fulfilled.add(oid)
    return events, receipts, fulfilled


def snapshot(db, case):
    events, receipts, fulfilled = ledger(db, case.id)
    values, totals = [], {}
    now = datetime.now(timezone.utc)
    for row in (
        db.query(Obligation)
        .filter_by(case_id=case.id)
        .order_by(Obligation.created_at, Obligation.id)
        .all()
    ):
        terms = json.loads(row.terms)
        received = receipts.get(row.root_id, 0)
        amount = terms["amount_minor"]
        balance = max(0, amount - received) if amount is not None else None
        status = row.state
        if status == "active":
            if (amount is not None and balance == 0) or (
                amount is None and row.root_id in fulfilled
            ):
                status = "fulfilled"
            elif (
                terms["due_at"]
                and datetime.fromisoformat(terms["due_at"].replace("Z", "+00:00")) < now
            ):
                status = "overdue"
            else:
                status = "on_track" if terms["due_at"] else "undated"
        if row.state == "active" and amount is not None:
            bucket = totals.setdefault(
                terms["currency"],
                {"promised_minor": 0, "received_minor": 0, "outstanding_minor": 0},
            )
            bucket["promised_minor"] += amount
            bucket["received_minor"] += received
            bucket["outstanding_minor"] += balance
        values.append(
            {
                "id": row.id,
                "root_id": row.root_id,
                "predecessor_id": row.predecessor_id,
                "semantic_status": status,
                "state": row.state,
                "origin": row.origin,
                "terms": terms,
                "sources": json.loads(row.sources),
                "deadline": json.loads(row.deadline),
                "received_minor": received,
                "outstanding_minor": balance,
            }
        )
    active = [v for v in values if v["state"] == "active"]
    status = (
        "resolved"
        if active and all(v["semantic_status"] == "fulfilled" for v in active)
        else (
            "overdue"
            if any(v["semantic_status"] == "overdue" for v in active)
            else "open"
        )
    )
    control = db.get(CaseControl, case.id)
    if control and control.state == "reopened":
        status = "open"
    from backend.app.schemas.contract import EvidenceSchema, CommitmentSchema

    return {
        "case": {
            "id": case.id,
            "title": case.title,
            "merchant_name": case.merchant_name,
            "version": case.version,
        },
        "version": case.version,
        "obligations": values,
        "evidence": [
            EvidenceSchema.model_validate(e).model_dump(mode="json")
            for e in case.evidence
        ],
        "legacy_commitments": [
            CommitmentSchema.model_validate(c).model_dump(mode="json")
            for c in case.commitments
        ],
        "legacy_facts_in_v2_totals": False,
        "events": [
            {
                "id": e.id,
                "sequence": e.sequence,
                "case_version": e.case_version,
                "kind": e.kind,
                "payload": json.loads(e.payload),
                "created_at": e.created_at,
            }
            for e in events
        ],
        "projection": {
            "status": status,
            "lifecycle": control.state if control else "open",
            "money_by_currency": totals,
            "health": (
                "resolved"
                if status == "resolved"
                else (
                    "overdue"
                    if status == "overdue"
                    else (
                        "missing_information"
                        if not active
                        or any(v["semantic_status"] == "undated" for v in active)
                        else (
                            "nearing_deadline"
                            if any(
                                v["terms"]["due_at"]
                                and 0
                                <= (
                                    datetime.fromisoformat(
                                        v["terms"]["due_at"].replace("Z", "+00:00")
                                    )
                                    - now
                                ).total_seconds()
                                <= 3 * 86400
                                for v in active
                            )
                            else "on_track"
                        )
                    )
                )
            ),
            "as_of": now.isoformat(),
            "timezone": "Asia/Kolkata",
        },
        "capabilities": {
            "manual": True,
            "outcomes": True,
            "export": True,
            "automatic_send": False,
        },
    }


def add_obligation(
    db, case, terms, source_refs, origin, predecessor_id=None, reason=None
):
    sources(db, case.id, source_refs)
    root = None
    if predecessor_id:
        old = (
            db.query(Obligation)
            .filter_by(id=predecessor_id, case_id=case.id, state="active")
            .first()
        )
        if old is None:
            fail(
                409,
                "INVALID_PREDECESSOR",
                "Predecessor is unavailable or already revised.",
            )
        _, received, _ = ledger(db, case.id)
        old_terms = json.loads(old.terms)
        if received.get(old.root_id, 0) and (
            terms.currency != old_terms["currency"]
            or terms.amount_minor is None
            or terms.amount_minor < received[old.root_id]
        ):
            fail(
                422,
                "INVALID_REVISION",
                "A revision cannot discard received money or change its currency.",
            )
        old.state = "superseded"
        root = old.root_id
    from backend.app.models.workflow import identity

    oid = identity()
    row = Obligation(
        id=oid,
        case_id=case.id,
        root_id=root or oid,
        predecessor_id=predecessor_id,
        origin=origin,
        terms=canonical(terms.model_dump(mode="json")),
        sources=canonical([r.model_dump(mode="json") for r in source_refs]),
    )
    db.add(row)
    db.flush()
    event(
        db,
        case.id,
        "promise_revised" if predecessor_id else "promise_confirmed",
        {
            "obligation_id": oid,
            "predecessor_id": predecessor_id,
            "reason": reason,
            "origin": origin,
        },
    )
    return row


def record_outcome(db, case, body):
    sources(db, case.id, body.source_ids)
    events, receipts, fulfilled = ledger(db, case.id)
    payload = body.model_dump(mode="json")
    if body.kind == "correction":
        target = next((e for e in events if e.id == body.corrects_event_id), None)
        if target is None or target.kind not in (
            "partial",
            "full",
            "pending",
            "company_claim",
        ):
            fail(
                422,
                "INVALID_CORRECTION",
                "Correction must reference an outcome in this case.",
            )
        if any(
            e.kind == "correction"
            and json.loads(e.payload)["corrects_event_id"] == target.id
            for e in events
        ):
            fail(409, "ALREADY_CORRECTED", "Outcome was already corrected.")
    else:
        allocations = []
        for a in body.allocations:
            row = (
                db.query(Obligation)
                .filter_by(id=a.obligation_id, case_id=case.id, state="active")
                .first()
            )
            if row is None:
                fail(404, "NOT_FOUND", "Active obligation not found.")
            terms = json.loads(row.terms)
            promised = terms["amount_minor"]
            got = receipts.get(row.root_id, 0)
            if body.kind in ("partial", "full"):
                if promised is None:
                    if (
                        a.amount_minor is not None
                        or body.kind == "partial"
                        and not body.note.strip()
                    ):
                        fail(
                            422,
                            "INVALID_ALLOCATION",
                            "Nonfinancial progress requires a note and no amount.",
                        )
                    if row.root_id in fulfilled:
                        fail(409, "ALREADY_FULFILLED", "Already fulfilled.")
                elif (
                    a.amount_minor is None
                    or a.amount_minor > promised - got
                    or (body.kind == "partial" and a.amount_minor == promised - got)
                    or (body.kind == "full" and a.amount_minor != promised - got)
                ):
                    fail(
                        422,
                        "INVALID_ALLOCATION",
                        "Receipt must fit the remaining balance; full receipt must equal it.",
                    )
            elif a.amount_minor is not None:
                fail(
                    422,
                    "INVALID_ALLOCATION",
                    "Pending and company claims do not record received money.",
                )
            allocations.append(
                {
                    **a.model_dump(),
                    "root_id": row.root_id,
                    "currency": terms["currency"],
                }
            )
        if body.received_at and body.received_at > datetime.now(timezone.utc):
            fail(422, "INVALID_RECEIPT_TIME", "A receipt cannot occur in the future.")
        payload["allocations"] = allocations
    return event(db, case.id, body.kind, payload)
