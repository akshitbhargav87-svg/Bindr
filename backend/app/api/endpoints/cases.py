import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.core.auth import get_current_session, SessionData
from backend.app.models.case import Case, utc_now_iso
from backend.app.models.timeline import TimelineEvent
from backend.app.schemas.contract import (
    CaseCreateRequest, CaseCreateResponse, CaseListResponse, CaseDetailResponse,
    CaseSchema, EvidenceSchema, CommitmentSchema, ExtractionSchema
)

router = APIRouter(prefix="/cases", tags=["Cases"])


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


@router.post("", response_model=CaseCreateResponse, status_code=status.HTTP_201_CREATED)
def create_case(
    payload: CaseCreateRequest,
    session: SessionData = Depends(get_current_session),
    db: Session = Depends(get_db)
):
    """Create a new case per API_CONTRACT. Associated with the authenticated session owner."""
    new_case = Case(
        owner_id=session.user_id,
        title=payload.title.strip(),
        merchant_name=payload.merchant_name.strip(),
        status="open",
        version=1,
        created_at=utc_now_iso()
    )
    db.add(new_case)
    db.flush()

    timeline = TimelineEvent(
        case_id=new_case.id,
        event_type="case_created",
        description=f"Case '{new_case.title}' created for merchant '{new_case.merchant_name}'.",
        event_date=new_case.created_at
    )
    db.add(timeline)
    db.commit()
    db.refresh(new_case)

    return {"case": CaseSchema.model_validate(new_case)}


@router.get("", response_model=CaseListResponse)
def list_cases(
    session: SessionData = Depends(get_current_session),
    db: Session = Depends(get_db)
):
    """Retrieve cases owned by authenticated user, sorted by created_at descending, then id ascending."""
    cases = (
        db.query(Case)
        .filter(Case.owner_id == session.user_id)
        .order_by(Case.created_at.desc(), Case.id.asc())
        .all()
    )
    return {"cases": [CaseSchema.model_validate(c) for c in cases]}


@router.get("/{case_id}", response_model=CaseDetailResponse)
def get_case(
    case_id: str,
    session: SessionData = Depends(get_current_session),
    db: Session = Depends(get_db)
):
    """Retrieve full case details per API_CONTRACT. Inaccessible or unknown IDs return 404."""
    case = db.query(Case).filter(Case.id == case_id, Case.owner_id == session.user_id).first()
    if not case:
        _api_error(status.HTTP_404_NOT_FOUND, "NOT_FOUND", f"Case {case_id} not found.")

    # Sort commitments, evidence, and extractions by created_at ascending, then id ascending
    commitments_sorted = sorted(case.commitments, key=lambda c: (c.created_at, c.id))
    evidence_sorted = sorted(case.evidence, key=lambda e: (e.created_at, e.id))
    extractions_sorted = sorted(case.extractions, key=lambda x: (x.created_at, x.id))

    return {
        "case": CaseSchema.model_validate(case),
        "evidence": [EvidenceSchema.model_validate(e) for e in evidence_sorted],
        "commitments": [
            CommitmentSchema(
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
            ) for c in commitments_sorted
        ],
        "extractions": [
            ExtractionSchema(
                id=x.id,
                case_id=x.case_id,
                evidence_ids=x.evidence_ids,
                status=x.status,
                candidates=x.candidates,
                reviewed_commitment_ids=x.reviewed_commitment_ids,
                created_at=x.created_at
            ) for x in extractions_sorted
        ]
    }
