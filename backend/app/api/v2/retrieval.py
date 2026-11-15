from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import Field
from backend.app.core.auth import get_current_session, SessionData
from backend.app.core.database import get_db
from backend.app.api.v2.reviews import get_intelligence
from backend.app.schemas.platform import Strict
from backend.app.services.platform.retrieval import retrieve, validate_answer
from backend.app.services.case_state import fail

router = APIRouter(prefix="/api/v2", tags=["Authorized retrieval v2"])


class Question(Strict):
    question: str = Field(min_length=1, max_length=4000)
    current_version: int = Field(ge=1, strict=True)


@router.post("/cases/{case_id}/questions")
def question(
    case_id: str,
    body: Question,
    auth: SessionData = Depends(get_current_session),
    db: Session = Depends(get_db),
    engine=Depends(get_intelligence),
):
    snapshot, citations = retrieve(db, auth.user_id, case_id, body.current_version)
    method = getattr(engine, "answer_case_v2", None)
    if method is None:
        fail(503, "INTELLIGENCE_V2_UNAVAILABLE", "Case answers are not configured.")
    from backend.app.services.rate_limit import enforce_limit

    enforce_limit(("question", auth.user_id), 20, 3600)
    from backend.app.services.platform.intelligence_boundary import invoke
    from fastapi import HTTPException

    try:
        answer = invoke(
            method,
            {
                "schema_version": 2,
                "question": body.question,
                "snapshot": snapshot,
                "tools": [],
            },
        )
    except HTTPException:
        raise
    except Exception:
        fail(503, "AI_UNAVAILABLE", "Case answer did not complete.")
    # A new transaction sees edits committed while the pure engine was running.
    db.rollback()
    from backend.app.services.platform.workflow import owned_case

    if owned_case(db, auth.user_id, case_id).version != body.current_version:
        fail(409, "VERSION_CONFLICT", "Case changed while answering.")
    return {"version": body.current_version, **validate_answer(answer, citations)}
