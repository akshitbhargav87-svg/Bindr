import uuid
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.core.auth import get_current_session, SessionData
from backend.app.models.case import Case, utc_now_iso
from backend.app.models.evidence import Evidence
from backend.app.models.commitment import Commitment
from backend.app.models.timeline import TimelineEvent
from backend.app.models.extraction import Extraction
from backend.app.schemas.contract import (
    ExtractionSchema, ExtractionCreateRequest, ExtractionReviewRequest,
    ExtractionCreateResponse, ExtractionReviewResponse, CommitmentSchema
)
from backend.app.services.storage import storage_service
from backend.app.services.ai_adapter import (
    ai_adapter,
    AITimeoutError, AIServiceUnavailableError, AIInvalidOutputError,
    AIValidationError, UnreadableEvidenceError
)

router = APIRouter(prefix="/cases/{case_id}/extractions", tags=["Extractions"])


def _api_error(status_code: int, code: str, message: str, details: Optional[list] = None):
    req_id = str(uuid.uuid4())
    raise HTTPException(
        status_code=status_code,
        detail={
            "error": {
                "code": code,
                "message": message,
                "details": details or [],
                "request_id": req_id
            }
        }
    )


@router.post("", response_model=ExtractionCreateResponse, status_code=status.HTTP_201_CREATED)
def create_extraction(
    case_id: str,
    payload: ExtractionCreateRequest,
    session: SessionData = Depends(get_current_session),
    db: Session = Depends(get_db)
):
    """
    Process evidence through AI extraction and return a pending review draft.
    Does NOT save commitments until confirmed by user review.
    Enforces case ownership, rejects duplicate evidence IDs, and forwards raw file bytes to AI pipeline.
    """
    case = db.query(Case).filter(Case.id == case_id, Case.owner_id == session.user_id).first()
    if not case:
        _api_error(status.HTTP_404_NOT_FOUND, "NOT_FOUND", f"Case {case_id} not found.")

    if case.status == "resolved":
        _api_error(status.HTTP_409_CONFLICT, "CASE_RESOLVED", "Resolved cases permit reads only.")

    if payload.expected_version is not None and case.version != payload.expected_version:
        _api_error(
            status.HTTP_409_CONFLICT,
            "VERSION_CONFLICT",
            f"Case version conflict: current is {case.version}, expected {payload.expected_version}."
        )

    # Validate 1-10 evidence IDs
    if not payload.evidence_ids or len(payload.evidence_ids) < 1 or len(payload.evidence_ids) > 10:
        _api_error(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "VALIDATION_ERROR",
            "Extraction requires 1 to 10 unique evidence IDs."
        )

    # Reject duplicate evidence IDs up-front
    if len(payload.evidence_ids) != len(set(payload.evidence_ids)):
        _api_error(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "VALIDATION_ERROR",
            "Duplicate evidence IDs in extraction request.",
            details=[{"field": "evidence_ids", "message": "Duplicate evidence IDs are not permitted."}]
        )

    # Fetch and verify evidence records belong to this case
    evidence_items = []
    for ev_id in payload.evidence_ids:
        ev = db.query(Evidence).filter(Evidence.id == ev_id, Evidence.case_id == case_id).first()
        if not ev:
            _api_error(
                status.HTTP_404_NOT_FOUND,
                "NOT_FOUND",
                f"Evidence {ev_id} not found under case {case_id}."
            )

        # Read stored file bytes directly so Kunal's pipeline (DocumentProcessor/RapidOCR) processes images & PDFs
        try:
            file_bytes = storage_service.read_file(ev.storage_key)
        except Exception as e:
            _api_error(
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                "INTERNAL_ERROR",
                "Could not read stored evidence."
            )

        evidence_items.append({
            "evidence_id": ev.id,
            "filename": ev.filename,
            "media_type": ev.media_type,
            "file_bytes": file_bytes,
            "occurred_at": None
        })

    # Prepare existing commitments for context
    existing_comm_schemas = [
        {
            "id": c.id,
            "case_id": c.case_id,
            "kind": c.kind,
            "description": c.description,
            "status": c.status,
            "amount_minor": c.amount_minor,
            "currency": c.currency,
            "due_at": c.due_at,
            "supersedes_id": c.supersedes_id,
            "evidence_ids": c.evidence_ids
        }
        for c in case.commitments
    ]

    # Invoke AI adapter boundary
    try:
        ai_result = ai_adapter.extract_commitments(
            case_id=case_id,
            evidence=evidence_items,
            existing_commitments=existing_comm_schemas,
            merchant_name=case.merchant_name
        )
    except AITimeoutError as e:
        _api_error(status.HTTP_504_GATEWAY_TIMEOUT, "AI_TIMEOUT", str(e))
    except AIServiceUnavailableError as e:
        _api_error(status.HTTP_503_SERVICE_UNAVAILABLE, "AI_UNAVAILABLE", str(e))
    except AIInvalidOutputError as e:
        _api_error(status.HTTP_502_BAD_GATEWAY, "AI_INVALID_OUTPUT", str(e))
    except (AIValidationError, UnreadableEvidenceError) as e:
        _api_error(status.HTTP_422_UNPROCESSABLE_ENTITY, "VALIDATION_ERROR", str(e))
    except Exception as e:
        _api_error(status.HTTP_500_INTERNAL_SERVER_ERROR, "INTERNAL_ERROR", "AI extraction failed.")

    # Validate output schema_version
    if ai_result.get("schema_version") != 1:
        _api_error(status.HTTP_502_BAD_GATEWAY, "AI_INVALID_OUTPUT", "Unsupported AI schema version.")

    # Persist pending_review draft
    now_iso = utc_now_iso()
    extraction = Extraction(
        case_id=case_id,
        status="pending_review",
        created_at=now_iso
    )
    extraction.evidence_ids = payload.evidence_ids
    extraction.candidates = ai_result.get("candidates", [])
    extraction.reviewed_commitment_ids = []

    db.add(extraction)
    case.version += 1

    timeline = TimelineEvent(
        case_id=case_id,
        event_type="extraction_created",
        description=f"AI extraction created with {len(extraction.candidates)} candidate(s) for review.",
        event_date=now_iso,
        created_at=now_iso
    )
    db.add(timeline)
    db.commit()
    db.refresh(extraction)
    db.refresh(case)

    return {
        "extraction": ExtractionSchema(
            id=extraction.id,
            case_id=extraction.case_id,
            evidence_ids=extraction.evidence_ids,
            status=extraction.status,
            candidates=extraction.candidates,
            reviewed_commitment_ids=extraction.reviewed_commitment_ids,
            created_at=extraction.created_at
        ),
        "case_version": case.version
    }


@router.post("/{extraction_id}/review", response_model=ExtractionReviewResponse)
def review_extraction(
    case_id: str,
    extraction_id: str,
    payload: ExtractionReviewRequest,
    session: SessionData = Depends(get_current_session),
    db: Session = Depends(get_db)
):
    """
    Review and confirm or reject an AI extraction draft in an owned case.
    Saves confirmed commitments atomically.
    Repeated reviews on closed drafts return 409 DRAFT_CLOSED.
    Rejects invented candidate IDs and negative refund amounts.
    """
    case = db.query(Case).filter(Case.id == case_id, Case.owner_id == session.user_id).first()
    if not case:
        _api_error(status.HTTP_404_NOT_FOUND, "NOT_FOUND", f"Case {case_id} not found.")

    if case.status == "resolved":
        _api_error(status.HTTP_409_CONFLICT, "CASE_RESOLVED", "Resolved cases permit reads only.")

    if payload.expected_version is not None and case.version != payload.expected_version:
        _api_error(
            status.HTTP_409_CONFLICT,
            "VERSION_CONFLICT",
            f"Case version conflict: current is {case.version}, expected {payload.expected_version}."
        )

    extraction = db.query(Extraction).filter(
        Extraction.id == extraction_id,
        Extraction.case_id == case_id
    ).first()
    if not extraction:
        _api_error(status.HTTP_404_NOT_FOUND, "NOT_FOUND", f"Extraction draft {extraction_id} not found.")

    if extraction.status != "pending_review":
        _api_error(
            status.HTTP_409_CONFLICT,
            "DRAFT_CLOSED",
            f"Extraction draft {extraction_id} is already closed ({extraction.status})."
        )

    now_iso = utc_now_iso()

    # --- REJECT BRANCH ---
    if payload.decision == "reject":
        if payload.items and len(payload.items) > 0:
            _api_error(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "VALIDATION_ERROR",
                "Rejecting an extraction requires items: []."
            )
        extraction.status = "rejected"
        case.version += 1

        timeline = TimelineEvent(
            case_id=case_id,
            event_type="extraction_rejected",
            description=f"Extraction draft {extraction_id} was rejected by user.",
            event_date=now_iso,
            created_at=now_iso
        )
        db.add(timeline)
        db.commit()
        db.refresh(extraction)
        db.refresh(case)

        return {
            "extraction": ExtractionSchema(
                id=extraction.id,
                case_id=extraction.case_id,
                evidence_ids=extraction.evidence_ids,
                status=extraction.status,
                candidates=extraction.candidates,
                reviewed_commitment_ids=extraction.reviewed_commitment_ids,
                created_at=extraction.created_at
            ),
            "commitments": [],
            "case_version": case.version
        }

    # --- APPROVE BRANCH ---
    if not payload.items or len(payload.items) < 1:
        _api_error(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "VALIDATION_ERROR",
            "Approving an extraction requires 1 to 10 confirmed items."
        )

    valid_candidate_ids = {c.get("candidate_id") for c in extraction.candidates if isinstance(c, dict)}
    seen_candidate_ids = set()
    created_commitments: List[Commitment] = []

    for idx, item in enumerate(payload.items):
        # 1. Reject invented candidate IDs
        if item.candidate_id not in valid_candidate_ids:
            _api_error(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "VALIDATION_ERROR",
                f"Candidate ID '{item.candidate_id}' does not exist in extraction draft.",
                details=[{"field": f"items[{idx}].candidate_id", "message": f"Candidate ID '{item.candidate_id}' not found in draft"}]
            )

        # 2. Reject duplicate approvals within items
        if item.candidate_id in seen_candidate_ids:
            _api_error(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "VALIDATION_ERROR",
                f"Duplicate candidate_id '{item.candidate_id}' in review items.",
                details=[{"field": f"items[{idx}].candidate_id", "message": "Duplicate candidate_id"}]
            )
        seen_candidate_ids.add(item.candidate_id)

        # 3. Reject negative money values and invalid currency pairings
        amt = item.terms.amount_minor
        curr = item.terms.currency

        if amt is not None and amt < 0:
            _api_error(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "VALIDATION_ERROR",
                "amount_minor must be a non-negative integer.",
                details=[{"field": f"items[{idx}].terms.amount_minor", "message": "Must be a non-negative integer"}]
            )

        if (amt is None and curr is not None) or (amt is not None and curr is None):
            _api_error(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "VALIDATION_ERROR",
                "Amount and currency must be either both null or both populated.",
                details=[{"field": f"items[{idx}].terms.amount_minor", "message": "Amount and currency must be paired"}]
            )

        # 4. Reject non-positive refund amounts
        if item.terms.kind == "refund":
            if amt is None or amt <= 0 or curr is None:
                _api_error(
                    status.HTTP_422_UNPROCESSABLE_ENTITY,
                    "VALIDATION_ERROR",
                    "A reviewed refund commitment requires both positive amount_minor and valid currency.",
                    details=[{"field": f"items[{idx}].terms.amount_minor", "message": "Reviewed refund commitment requires positive amount_minor"}]
                )

        # Evidence validation: at least one evidence ID from extraction
        if not any(eid in extraction.evidence_ids for eid in item.evidence_ids):
            _api_error(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "VALIDATION_ERROR",
                f"Item for candidate '{item.candidate_id}' must reference at least one evidence ID from the extraction.",
                details=[{"field": f"items[{idx}].evidence_ids", "message": "Must reference at least one evidence ID from extraction"}]
            )

        # Verify all referenced evidence IDs belong to this case
        for eid in item.evidence_ids:
            ev = db.query(Evidence).filter(Evidence.id == eid, Evidence.case_id == case_id).first()
            if not ev:
                _api_error(
                    status.HTTP_404_NOT_FOUND,
                    "NOT_FOUND",
                    f"Evidence {eid} does not belong to case {case_id}."
                )

        # Action: 'new' vs 'revision'
        if item.action == "new":
            if item.supersedes_id is not None:
                _api_error(
                    status.HTTP_422_UNPROCESSABLE_ENTITY,
                    "VALIDATION_ERROR",
                    "Action 'new' requires supersedes_id to be null."
                )
        elif item.action == "revision":
            if not item.supersedes_id:
                _api_error(
                    status.HTTP_422_UNPROCESSABLE_ENTITY,
                    "VALIDATION_ERROR",
                    "Action 'revision' requires an active supersedes_id."
                )
            predecessor = db.query(Commitment).filter(
                Commitment.id == item.supersedes_id,
                Commitment.case_id == case_id
            ).first()
            if not predecessor:
                _api_error(
                    status.HTTP_404_NOT_FOUND,
                    "NOT_FOUND",
                    f"Predecessor commitment {item.supersedes_id} not found in case {case_id}."
                )
            if predecessor.status != "active":
                _api_error(
                    status.HTTP_409_CONFLICT,
                    "INVALID_REVISION",
                    f"Predecessor commitment {item.supersedes_id} is not active ({predecessor.status})."
                )

            # Mark predecessor superseded
            predecessor.status = "superseded"
            # Ensure revision includes predecessor's evidence IDs
            combined_evidence = list(set(predecessor.evidence_ids + item.evidence_ids))
            item.evidence_ids = combined_evidence

        comm = Commitment(
            case_id=case_id,
            extraction_id=extraction_id,
            candidate_id=item.candidate_id,
            kind=item.terms.kind,
            description=item.terms.description.strip(),
            amount_minor=item.terms.amount_minor,
            currency=item.terms.currency,
            due_at=item.terms.due_at,
            status="active",
            supersedes_id=item.supersedes_id,
            reviewed_at=now_iso,
            created_at=now_iso
        )
        comm.evidence_ids = item.evidence_ids
        created_commitments.append(comm)

    # Execute all review state persistence inside an atomic transaction
    try:
        for c in created_commitments:
            db.add(c)
            db.flush()

            timeline_event_type = "commitment_created" if not c.supersedes_id else "commitment_revised"
            timeline_desc = (
                f"Commitment confirmed from AI extraction '{c.candidate_id}': {c.description[:60]}..."
                if not c.supersedes_id
                else f"Commitment revised from AI extraction '{c.candidate_id}' superseding {c.supersedes_id}."
            )
            timeline = TimelineEvent(
                case_id=case_id,
                event_type=timeline_event_type,
                description=timeline_desc,
                event_date=now_iso,
                created_at=now_iso
            )
            db.add(timeline)

        # Close extraction draft
        extraction.status = "reviewed"
        extraction.reviewed_commitment_ids = [c.id for c in created_commitments]
        case.version += 1

        db.commit()
        db.refresh(extraction)
        db.refresh(case)
        for c in created_commitments:
            db.refresh(c)

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        _api_error(status.HTTP_500_INTERNAL_SERVER_ERROR, "INTERNAL_ERROR", "Failed to persist reviewed commitments.")

    return {
        "extraction": ExtractionSchema(
            id=extraction.id,
            case_id=extraction.case_id,
            evidence_ids=extraction.evidence_ids,
            status=extraction.status,
            candidates=extraction.candidates,
            reviewed_commitment_ids=extraction.reviewed_commitment_ids,
            created_at=extraction.created_at
        ),
        "commitments": [CommitmentSchema.model_validate(c) for c in created_commitments],
        "case_version": case.version
    }
