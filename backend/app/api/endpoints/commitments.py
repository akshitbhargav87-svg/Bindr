import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.core.auth import get_current_session, SessionData
from backend.app.models.case import Case, utc_now_iso
from backend.app.models.commitment import Commitment
from backend.app.models.timeline import TimelineEvent
from backend.app.schemas.contract import (
    CommitmentCreateRequest, CommitmentReviseRequest, CommitmentSchema
)

router = APIRouter(tags=["Commitments"])


def _api_error(status_code: int, code: str, message: str):
    req_id = str(uuid.uuid4())
    raise HTTPException(
        status_code=status_code,
        detail={
            "error": {
                "code": code,
                "message": message,
                "details": [],
                "request_id": req_id
            }
        }
    )


def _commitment_to_schema(c: Commitment) -> CommitmentSchema:
    return CommitmentSchema(
        id=c.id,
        case_id=c.case_id,
        extraction_id=c.extraction_id,
        candidate_id=c.candidate_id,
        kind=c.kind,
        description=c.description,
        amount_minor=c.amount_minor,
        currency=c.currency,
        due_at=c.due_at,
        status=c.status,
        supersedes_id=c.supersedes_id,
        evidence_ids=c.evidence_ids,
        reviewed_at=c.reviewed_at,
        created_at=c.created_at
    )


@router.post("/cases/{case_id}/commitments", response_model=CommitmentSchema, status_code=status.HTTP_201_CREATED)
def create_commitment_for_case(
    case_id: str,
    payload: CommitmentCreateRequest,
    session: SessionData = Depends(get_current_session),
    db: Session = Depends(get_db)
):
    """Create a commitment associated with an owned case."""
    case = db.query(Case).filter(Case.id == case_id, Case.owner_id == session.user_id).first()
    if not case:
        _api_error(status.HTTP_404_NOT_FOUND, "NOT_FOUND", f"Case {case_id} not found.")

    new_commitment = Commitment(
        case_id=case_id,
        kind=payload.kind,
        description=payload.description.strip(),
        amount_minor=payload.amount_minor,
        currency=payload.currency,
        due_at=payload.due_at,
        status=payload.status,
        supersedes_id=payload.supersedes_id,
        reviewed_at=utc_now_iso(),
        created_at=utc_now_iso()
    )
    new_commitment.evidence_ids = payload.evidence_ids
    db.add(new_commitment)
    db.flush()

    timeline = TimelineEvent(
        case_id=case_id,
        event_type="commitment_created",
        description=f"Commitment created: '{new_commitment.description[:60]}...'",
        event_date=new_commitment.created_at
    )
    db.add(timeline)
    db.commit()
    db.refresh(new_commitment)

    return _commitment_to_schema(new_commitment)


@router.get("/commitments/{commitment_id}", response_model=CommitmentSchema)
def get_commitment(
    commitment_id: str,
    session: SessionData = Depends(get_current_session),
    db: Session = Depends(get_db)
):
    """Retrieve details of a single commitment in an owned case."""
    comm = db.query(Commitment).join(Case).filter(
        Commitment.id == commitment_id,
        Case.owner_id == session.user_id
    ).first()
    if not comm:
        _api_error(status.HTTP_404_NOT_FOUND, "NOT_FOUND", f"Commitment {commitment_id} not found.")
    return _commitment_to_schema(comm)


@router.post("/commitments/{commitment_id}/revise", response_model=CommitmentSchema, status_code=status.HTTP_201_CREATED)
def revise_commitment(
    commitment_id: str,
    payload: CommitmentReviseRequest,
    session: SessionData = Depends(get_current_session),
    db: Session = Depends(get_db)
):
    """
    Revise an existing commitment in an owned case.
    Preserves original commitment: original is marked as 'superseded' and a new commitment is created.
    """
    original = db.query(Commitment).join(Case).filter(
        Commitment.id == commitment_id,
        Case.owner_id == session.user_id
    ).first()
    if not original:
        _api_error(status.HTTP_404_NOT_FOUND, "NOT_FOUND", f"Original commitment {commitment_id} not found.")

    original.status = "superseded"

    revised = Commitment(
        case_id=original.case_id,
        extraction_id=original.extraction_id,
        candidate_id=original.candidate_id,
        kind=payload.kind or original.kind,
        description=payload.description.strip(),
        amount_minor=payload.amount_minor if payload.amount_minor is not None else original.amount_minor,
        currency=payload.currency or original.currency,
        due_at=payload.due_at or original.due_at,
        status="active",
        supersedes_id=original.id,
        reviewed_at=utc_now_iso(),
        created_at=utc_now_iso()
    )
    combined_evidence = list(set(original.evidence_ids + payload.evidence_ids))
    revised.evidence_ids = combined_evidence
    db.add(revised)
    db.flush()

    timeline = TimelineEvent(
        case_id=original.case_id,
        event_type="commitment_revised",
        description=f"Commitment {original.id} superseded by revised commitment {revised.id}.",
        event_date=revised.created_at
    )
    db.add(timeline)
    db.commit()
    db.refresh(revised)

    return _commitment_to_schema(revised)
