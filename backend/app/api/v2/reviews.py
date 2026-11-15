"""V2 intelligence is a pure replaceable seam. Missing engine support fails closed."""

import json
import time
import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import ValidationError
from backend.app.api.v2.platform import Key
from backend.app.core.auth import get_current_session, SessionData
from backend.app.core.database import get_db
from backend.app.models.platform import EvidenceCommunication
from backend.app.models.workflow import Proposal, Obligation
from backend.app.schemas.workflow import ExtractionRequest, ProposalResult, Review
from backend.app.services.platform.workflow import (
    owned_case,
    claim,
    sources,
    add_obligation,
    event,
)
from backend.app.services.platform.operations import execute, canonical
from backend.app.services.case_state import fail

router = APIRouter(prefix="/api/v2", tags=["Human review v2"])


def get_intelligence():
    from backend.app.services.ai_adapter import ai_adapter

    return ai_adapter


@router.post("/cases/{case_id}/extractions", status_code=201)
def extract(
    case_id: str,
    body: ExtractionRequest,
    key: Key,
    auth: SessionData = Depends(get_current_session),
    db: Session = Depends(get_db),
    engine=Depends(get_intelligence),
):
    case = owned_case(db, auth.user_id, case_id)
    rows = sources(db, case_id, body.evidence_ids)
    context = {"stage": "validation", "started": time.monotonic()}
    attempt_id = str(uuid.uuid4())
    from backend.app.models.jobs import Job
    from backend.app.services.platform.jobs import view

    def save():
        claim(db, case, body.expected_version)
        context["stage"] = "configuration"
        method = getattr(engine, "extract_proposals_v2", None)
        if method is None:
            fail(
                503,
                "INTELLIGENCE_V2_UNAVAILABLE",
                "V2 intelligence is not configured. Manual entry remains available.",
            )
        from backend.app.services.storage import storage_service
        from backend.app.ai.document_processor import DocumentProcessor
        from backend.app.services.rate_limit import enforce_limit

        enforce_limit(("extraction-v2", auth.user_id), 10, 3600)
        documents = []
        texts = {}
        pages = {}
        context["stage"] = "document_processing"
        for row in rows:
            from backend.app.services.platform.media import original, processing_suffix

            content = original(row)
            # A invokes B's existing pure document processor without changing it.
            suffix = processing_suffix(row)
            doc = DocumentProcessor().process_bytes(
                content, filename="evidence" + suffix
            )
            texts[row.id] = doc.raw_text
            pages[row.id] = {p.page_number: p.text for p in doc.pages}
            comm = db.get(EvidenceCommunication, row.id)
            metadata = body.metadata_references.get(row.id)
            documents.append(
                {
                    "evidence_id": row.id,
                    "text": doc.raw_text,
                    "pages": [p.model_dump() for p in doc.pages],
                    "communication": (
                        metadata.model_dump(mode="json")
                        if metadata
                        else json.loads(comm.payload) if comm else None
                    ),
                }
            )
        request = {
            "schema_version": 2,
            "case_id": case_id,
            "evidence": documents,
            "existing_obligations": [
                {"id": o.id, "terms": json.loads(o.terms)}
                for o in db.query(Obligation)
                .filter_by(case_id=case_id, state="active")
                .all()
            ],
            "context": {
                "operation_id": key,
                "timeout_seconds": 60,
                "timezone": "Asia/Kolkata",
            },
        }
        from backend.app.services.platform.intelligence_boundary import invoke
        from fastapi import HTTPException

        context["stage"] = "inference_and_schema_validation"
        try:
            result = ProposalResult.model_validate(invoke(method, request))
        except HTTPException:
            raise
        except ValidationError:
            fail(
                502,
                "AI_INVALID_OUTPUT",
                "The intelligence response failed schema validation. Nothing was confirmed.",
            )
        except Exception:
            fail(
                503,
                "AI_UNAVAILABLE",
                "Intelligence did not complete. Nothing was confirmed.",
            )
        context["stage"] = "citation_validation"
        for candidate in result.candidates:
            for source in candidate.sources:
                haystack = (
                    pages.get(source.evidence_id, {}).get(source.page, "")
                    if source.page
                    else texts.get(source.evidence_id, "")
                )
                if not haystack or source.quote not in haystack:
                    fail(
                        502,
                        "AI_INVALID_OUTPUT",
                        "An intelligence citation does not match its attributed evidence.",
                    )
            if (
                candidate.relation.predecessor_id
                and not db.query(Obligation)
                .filter_by(
                    id=candidate.relation.predecessor_id,
                    case_id=case_id,
                    state="active",
                )
                .first()
            ):
                fail(
                    502, "AI_INVALID_OUTPUT", "An intelligence predecessor is invalid."
                )
        if db.get(Proposal, result.proposal_id):
            fail(502, "AI_INVALID_OUTPUT", "Proposal identity was reused.")
        db.add(
            Proposal(
                id=result.proposal_id,
                case_id=case_id,
                case_version=case.version,
                payload=canonical(result.model_dump(mode="json")),
            )
        )
        event(
            db,
            case_id,
            "proposal_created",
            {
                "proposal_id": result.proposal_id,
                "candidate_count": len(result.candidates),
            },
        )
        attempt = Job(
            id=attempt_id,
            owner_id=auth.user_id,
            case_id=case_id,
            case_version=case.version,
            kind="extraction_attempt",
            state="review_required",
            stage="review",
            run_at=int(time.time()),
            payload="{}",
            result=canonical(
                {
                    "proposal_id": result.proposal_id,
                    "elapsed_ms": round((time.monotonic() - context["started"]) * 1000),
                }
            ),
        )
        db.add(attempt)
        db.flush()
        return {
            "job": view(attempt)["job"],
            "proposal": result.model_dump(mode="json"),
            "state": "review_required",
            "case_version": case.version,
        }

    try:
        return execute(
            db,
            auth.user_id,
            "extract:" + case_id,
            key,
            body.model_dump(mode="json"),
            save,
        )
    except HTTPException as exc:
        db.rollback()
        code = (
            exc.detail.get("error", {}).get("code", "EXTRACTION_FAILED")
            if isinstance(exc.detail, dict)
            else "EXTRACTION_FAILED"
        )
        if exc.status_code in (502, 503, 504):
            attempt = Job(
                id=attempt_id,
                owner_id=auth.user_id,
                case_id=case_id,
                case_version=body.expected_version,
                kind="extraction_attempt",
                state="failed",
                stage=context["stage"],
                run_at=int(time.time()),
                payload="{}",
                error_code=code,
                result=canonical(
                    {
                        "elapsed_ms": round(
                            (time.monotonic() - context["started"]) * 1000
                        )
                    }
                ),
            )
            db.add(attempt)
            db.commit()
            exc.detail["error"]["request_id"] = attempt_id
        raise


@router.post("/cases/{case_id}/reviews")
def review(
    case_id: str,
    body: Review,
    key: Key,
    auth: SessionData = Depends(get_current_session),
    db: Session = Depends(get_db),
):
    case = owned_case(db, auth.user_id, case_id)
    proposal = (
        db.query(Proposal).filter_by(id=body.proposal_id, case_id=case_id).first()
    )
    if proposal is None:
        fail(404, "NOT_FOUND", "Proposal not found.")

    def save():
        claim(db, case, body.expected_version)
        if proposal.state != "review_required":
            fail(409, "PROPOSAL_CLOSED", "Proposal was already reviewed.")
        if proposal.case_version != body.expected_version:
            fail(
                409,
                "VERSION_CONFLICT",
                "Proposal facts changed. Extract again before confirmation.",
            )
        candidates = {
            c.candidate_id: c
            for c in ProposalResult.model_validate_json(proposal.payload).candidates
        }
        if any(d.candidate_id not in candidates for d in body.decisions):
            fail(
                422, "INVALID_CANDIDATE", "Decision contains an invented candidate ID."
            )
        confirmed = []
        for decision in body.decisions:
            candidate = candidates[decision.candidate_id]
            if decision.action == "reject":
                continue
            predecessor = decision.predecessor_id
            if decision.action in ("cancel", "corroborate"):
                old = (
                    db.query(Obligation)
                    .filter_by(id=predecessor, case_id=case_id, state="active")
                    .first()
                )
                if old is None:
                    fail(
                        409,
                        "INVALID_PREDECESSOR",
                        "Select an active predecessor in this case.",
                    )
                if decision.action == "cancel":
                    old.state = "revoked"
                event(
                    db,
                    case_id,
                    (
                        "company_revocation_confirmed"
                        if decision.action == "cancel"
                        else "corroboration_confirmed"
                    ),
                    {
                        "obligation_id": old.id,
                        "proposal_id": proposal.id,
                        "sources": [
                            s.model_dump(mode="json") for s in candidate.sources
                        ],
                    },
                )
                continue
            terms = decision.edited_terms or candidate.terms
            if (
                terms.due_at != candidate.terms.due_at
                and not decision.deadline_override_reason
            ):
                fail(422, "OVERRIDE_REASON_REQUIRED", "Explain the deadline override.")
            if (
                candidate.condition.text
                and candidate.condition.fulfilled is not True
                and terms.due_at
                and not decision.deadline_override_reason
            ):
                fail(
                    422,
                    "CONDITION_UNCONFIRMED",
                    "Confirm the trigger or explicitly explain the deadline override.",
                )
            row = add_obligation(
                db,
                case,
                terms,
                candidate.sources,
                "reviewed_ai",
                predecessor,
                decision.deadline_override_reason or candidate.relation.explanation,
            )
            from backend.app.services.platform.deadlines import attach

            attach(row, decision.deadline, terms, decision.deadline_override_reason)
            confirmed.append(row.id)
        proposal.state = "reviewed"
        event(
            db,
            case_id,
            "proposal_reviewed",
            {
                "proposal_id": proposal.id,
                "decisions": [d.model_dump(mode="json") for d in body.decisions],
                "unselected_policy": "rejected",
                "confirmed_ids": confirmed,
            },
        )
        from backend.app.services.platform.reminders import schedule

        schedule(db, case, auth.user_id)
        return {
            "confirmed_ids": confirmed,
            "case_version": case.version,
            "state": "reviewed",
        }

    return execute(
        db, auth.user_id, "review:" + case_id, key, body.model_dump(mode="json"), save
    )
