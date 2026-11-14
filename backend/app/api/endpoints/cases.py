import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.core.auth import get_current_session, SessionData
from backend.app.models.case import Case, utc_now_iso
from backend.app.models.timeline import TimelineEvent
from backend.app.models.commitment import Commitment
from backend.app.services.case_state import displayed_case, claim_version, fail
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
    from backend.app.services.rate_limit import enforce_limit
    enforce_limit(("case", session.user_id), 100, 3600)
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
    return {"cases": [displayed_case(c) for c in cases]}


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
        "case": displayed_case(case),
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


from pydantic import BaseModel, ConfigDict, Field, field_validator

class ResolveRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    expected_version: int = Field(..., gt=0, strict=True)
    resolution_note: str = Field(..., min_length=1, max_length=2000)

class ComplaintRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    expected_version: int = Field(..., gt=0, strict=True)
    requested_remedy: str = Field(..., min_length=1, max_length=2000)


def _owned_case(db, case_id, session):
    """
    Enforce case ownership and active state invariant before mutating operations.

    Invariants:
    1. Case Ownership: Scoped strictly by `Case.owner_id == session.user_id`.
       Unknown or cross-tenant case IDs return HTTP 404 NOT_FOUND to prevent ID enumeration.
    2. Immutability of Resolved Cases: Once a case reaches 'resolved' status, it is closed
       to all subsequent state-changing operations, returning HTTP 409 CASE_RESOLVED.
    """
    case = db.query(Case).filter(Case.id == case_id, Case.owner_id == session.user_id).first()
    if not case:
        fail(404, "NOT_FOUND", "Case not found.")
    if case.status == "resolved":
        fail(409, "CASE_RESOLVED", "Resolved cases permit reads only.")
    return case


@router.post("/{case_id}/resolve", response_model=CaseCreateResponse)
def resolve_case(case_id: str, payload: ResolveRequest,
                 session: SessionData = Depends(get_current_session), db: Session = Depends(get_db)):
    case = _owned_case(db, case_id, session)
    current = [c for c in case.commitments if c.status == "active"]
    if not current:
        fail(409, "NO_ACTIVE_COMMITMENT", "Confirm a promise before recording full fulfilment.")
    claim_version(db, case, payload.expected_version)
    now = utc_now_iso()
    for commitment in current:
        commitment.status = "fulfilled"
    case.status = "resolved"
    case.resolution_note = payload.resolution_note
    case.resolved_at = now
    db.add(TimelineEvent(case_id=case_id, event_type="case_resolved",
           description="User confirmed full fulfilment: " + payload.resolution_note,
           event_date=now, created_at=now))
    db.commit()
    db.refresh(case)
    return {"case": CaseSchema.model_validate(case)}


@router.post("/{case_id}/complaint-draft")
def complaint_draft(case_id: str, payload: ComplaintRequest,
                    session: SessionData = Depends(get_current_session), db: Session = Depends(get_db)):
    case = _owned_case(db, case_id, session)
    if case.version != payload.expected_version:
        fail(409, "VERSION_CONFLICT", "This case changed. Refresh before preparing a complaint.")
    current = [c for c in case.commitments if c.status == "active"]
    if not current:
        fail(409, "NO_ACTIVE_COMMITMENT", "Confirm a promise before preparing a complaint.")
    evidence_ids = list(dict.fromkeys(eid for c in current for eid in c.evidence_ids))
    lines = [f"To {case.merchant_name},", "", f"Regarding: {case.title}", "",
             "I am following up on the commitments recorded in this case:"]
    for c in current:
        lines.append("- " + c.description)
        if c.amount_minor is not None:
            lines.append(f"  Amount: {c.currency} {c.amount_minor // 100}.{c.amount_minor % 100:02d}")
        lines.append("  Confirmed deadline (UTC): " + (c.due_at or "Not specified"))
    superseded = sorted([c for c in case.commitments if c.status == "superseded"], key=lambda c: (c.created_at, c.id))
    if superseded:
        lines.extend(["", "Earlier terms retained in the record:"])
        lines.extend("- " + c.description + "; deadline: " + (c.due_at or "Not specified") for c in superseded)
    lines.extend(["", "Requested remedy:", payload.requested_remedy, "", "Linked evidence:"])
    filenames = {e.id: e.filename for e in case.evidence}
    lines.extend(f"- {filenames.get(eid, 'Evidence')} [{eid}]" for eid in evidence_ids)
    lines.extend(["", "Please respond with an update and a clear plan to fulfil the recorded commitment."])
    body = "\n".join(lines)
    if len(body) > 10000:
        fail(422, "DRAFT_TOO_LONG", "This case has too much history for a single complaint preview. Use the case record to prepare a shorter follow-up.")
    if not evidence_ids:
        fail(422, "NO_LINKED_EVIDENCE", "A complaint preview requires a reviewed promise linked to evidence.")
    db.refresh(case, attribute_names=["version", "status"])
    if case.status == "resolved":
        fail(409, "CASE_RESOLVED", "Resolved cases permit reads only.")
    if case.version != payload.expected_version:
        fail(409, "VERSION_CONFLICT", "This case changed while preparing the preview. Refresh and review the latest record.")
    # No provider call or persistence: the preview is generated from reviewed facts only.
    return {"draft": {"subject": f"Follow-up: {case.title}"[:200], "body": body,
                      "evidence_ids": evidence_ids}, "case_version": case.version}
