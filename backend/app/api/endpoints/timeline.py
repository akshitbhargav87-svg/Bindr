import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.core.auth import get_current_session, SessionData
from backend.app.models.case import Case
from backend.app.models.timeline import TimelineEvent
from backend.app.schemas.contract import TimelineResponse, TimelineEventSchema

router = APIRouter(prefix="/cases/{case_id}/timeline", tags=["Timeline"])


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


@router.get("", response_model=TimelineResponse)
def get_case_timeline(
    case_id: str,
    session: SessionData = Depends(get_current_session),
    db: Session = Depends(get_db)
):
    """Retrieve chronological timeline events associated with an owned case."""
    case = db.query(Case).filter(Case.id == case_id, Case.owner_id == session.user_id).first()
    if not case:
        _api_error(status.HTTP_404_NOT_FOUND, "NOT_FOUND", f"Case {case_id} not found.")

    events = (
        db.query(TimelineEvent)
        .filter(TimelineEvent.case_id == case_id)
        .order_by(TimelineEvent.event_date.asc(), TimelineEvent.created_at.asc(), TimelineEvent.id.asc())
        .all()
    )

    return {"timeline_events": [TimelineEventSchema.model_validate(e) for e in events]}
