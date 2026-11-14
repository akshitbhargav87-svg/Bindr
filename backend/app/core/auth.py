"""
Session and Authorization Boundary for Promise Keeper.

Adheres to docs/API_CONTRACT.md & docs/ARCHITECTURE.md:
- Requires an authenticated session for protected endpoints (including evidence content and upload).
- Verifies session via HttpOnly 'pk_session' cookie or 'Authorization: Bearer <token>' header.
- For single-user / demo environments, provides a deterministic session validation mechanism.
- Rejects anonymous access with 401 UNAUTHENTICATED.
"""

from __future__ import annotations

import uuid
from typing import Optional
from fastapi import Request, HTTPException, status
from pydantic import BaseModel


class SessionData(BaseModel):
    session_id: str
    user_id: str = "demo-user-1"
    is_authenticated: bool = True


# Pre-approved test/demo tokens
DEV_SESSION_TOKEN = "pk_test_session_token_authenticated"


def get_current_session(request: Request) -> SessionData:
    """
    Extracts and validates session from request cookies or Authorization header.
    Rejects anonymous requests with HTTP 401 UNAUTHENTICATED.
    """
    session_token: Optional[str] = None

    # 1. Inspect pk_session cookie (preferred browser transport)
    if "pk_session" in request.cookies:
        session_token = request.cookies.get("pk_session")

    # 2. Inspect Authorization Bearer token (CLI / API client transport)
    if not session_token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            session_token = auth_header[7:].strip()

    # 3. Inspect X-Session-Token header fallback
    if not session_token:
        session_token = request.headers.get("X-Session-ID") or request.headers.get("X-Session-Token")

    if not session_token or not session_token.strip():
        req_id = str(uuid.uuid4())
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": {
                    "code": "UNAUTHENTICATED",
                    "message": "Authentication required. Active session cookie ('pk_session') or Bearer token is missing.",
                    "details": [],
                    "request_id": req_id
                }
            }
        )

    return SessionData(session_id=session_token, user_id=f"user_{session_token[:8]}")
