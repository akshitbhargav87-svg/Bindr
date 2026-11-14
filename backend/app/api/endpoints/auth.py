"""Browser-owned anonymous workspaces; no caller can choose an existing owner."""
import uuid
from typing import Optional
from fastapi import APIRouter, Response, Depends, Request, HTTPException, status
from pydantic import BaseModel, ConfigDict
from backend.app.core.auth import (create_authenticated_session, get_current_session,
                                   verify_session_token, generate_csrf_token, SessionData)
from backend.app.core.config import settings

router = APIRouter(prefix="/auth", tags=["Auth"])

class SessionBootstrapRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

class SessionBootstrapResponse(BaseModel):
    session_id: str
    user_id: str
    csrf_token: str


def _check_origin(request: Request):
    origin = request.headers.get("origin")
    same_origin = str(request.base_url).rstrip("/")
    allowed = {o.rstrip("/") for o in settings.CORS_ORIGINS} | {same_origin}
    if origin and origin.rstrip("/") not in allowed:
        raise HTTPException(403, detail="Origin is not permitted.")

@router.post("/session", response_model=SessionBootstrapResponse, status_code=201)
def create_session(request: Request, response: Response,
                   payload: Optional[SessionBootstrapRequest] = None):
    _check_origin(request)
    from backend.app.services.rate_limit import enforce_limit
    enforce_limit(("session", request.client.host if request.client else "unknown"), 60, 60)
    existing = request.cookies.get("pk_session", "")
    verified = verify_session_token(existing)
    if verified:
        session_id, user_id = verified
        token, csrf_token = existing, generate_csrf_token(session_id)
    else:
        user_id = str(uuid.uuid4())
        token, csrf_token = create_authenticated_session(user_id=user_id)
        session_id = token.split(".")[0]
    secure = settings.ENVIRONMENT.lower() in {"production", "prod", "staging", "deployed"}
    for key, value, http_only in (("pk_session", token, True), ("pk_csrf", csrf_token, False)):
        response.set_cookie(key, value, httponly=http_only, samesite="lax", secure=secure,
                            path="/", max_age=settings.SESSION_LIFETIME_SECONDS)
    response.headers["Cache-Control"] = "no-store"
    return SessionBootstrapResponse(session_id=session_id, user_id=user_id, csrf_token=csrf_token)

@router.get("/session", response_model=SessionBootstrapResponse)
def get_session(response: Response, session: SessionData = Depends(get_current_session)):
    response.headers["Cache-Control"] = "no-store"
    secure = settings.ENVIRONMENT.lower() in {"production", "prod", "staging", "deployed"}
    response.set_cookie("pk_csrf", session.csrf_token, httponly=False, samesite="lax",
                        secure=secure, path="/", max_age=settings.SESSION_LIFETIME_SECONDS)
    return SessionBootstrapResponse(session_id=session.session_id, user_id=session.user_id,
                                    csrf_token=session.csrf_token)

@router.delete("/session")
def delete_session(response: Response, session: SessionData = Depends(get_current_session)):
    response.delete_cookie("pk_session", path="/")
    response.delete_cookie("pk_csrf", path="/")
    return {"message": "Browser session cleared. This anonymous workspace cannot be recovered without its cookie."}
