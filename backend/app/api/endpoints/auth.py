"""
Authentication & Browser Session Bootstrap Endpoints.

Adheres to docs/API_CONTRACT.md:
- Supplies opaque `pk_session` HttpOnly cookie.
- Supplies readable `pk_csrf` cookie (and echoes CSRF token in response payload)
  so frontend can pass it in `X-CSRF-Token` on every state-mutating request.
- Provides session inspection and termination endpoints.
"""

from typing import Optional, Dict, Any
from fastapi import APIRouter, Response, Depends, status
from pydantic import BaseModel, Field

from backend.app.core.auth import create_authenticated_session, get_current_session, SessionData

router = APIRouter(prefix="/auth", tags=["Auth"])


class SessionBootstrapRequest(BaseModel):
    user_id: Optional[str] = Field("demo-user", description="Identity to bootstrap session for.")


class SessionBootstrapResponse(BaseModel):
    session_id: str
    user_id: str
    csrf_token: str


@router.post("/session", response_model=SessionBootstrapResponse, status_code=status.HTTP_201_CREATED)
def create_session(
    response: Response,
    payload: Optional[SessionBootstrapRequest] = None
):
    """
    Bootstrap a legitimate browser session and CSRF token.
    Sets HttpOnly `pk_session` cookie and readable `pk_csrf` cookie.
    """
    user_id = payload.user_id if payload and payload.user_id else "demo-user"
    token, csrf_token = create_authenticated_session(user_id=user_id)
    session_id = token.split(".")[0]

    # Set HttpOnly session cookie
    response.set_cookie(
        key="pk_session",
        value=token,
        httponly=True,
        samesite="lax",
        secure=False,
        path="/"
    )
    # Set client-readable CSRF token cookie for frontend integration
    response.set_cookie(
        key="pk_csrf",
        value=csrf_token,
        httponly=False,
        samesite="lax",
        secure=False,
        path="/"
    )

    return SessionBootstrapResponse(
        session_id=session_id,
        user_id=user_id,
        csrf_token=csrf_token
    )


@router.get("/session", response_model=SessionBootstrapResponse)
def get_session(session: SessionData = Depends(get_current_session)):
    """
    Inspect the currently active authenticated session and retrieve its CSRF token.
    """
    return SessionBootstrapResponse(
        session_id=session.session_id,
        user_id=session.user_id,
        csrf_token=session.csrf_token
    )


@router.delete("/session")
def delete_session(response: Response):
    """
    Terminate session and clear browser authentication cookies.
    """
    response.delete_cookie(key="pk_session", path="/")
    response.delete_cookie(key="pk_csrf", path="/")
    return {"message": "Session terminated successfully."}
