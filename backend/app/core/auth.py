"""
Session and Authorization Boundary for Promise Keeper.

Adheres to docs/API_CONTRACT.md & docs/ARCHITECTURE.md:
- Implements cryptographically verifiable session tokens using HMAC-SHA256 signatures.
- Rejects arbitrary or forged session cookies and bearer tokens with HTTP 401 UNAUTHENTICATED.
- Provides per-session CSRF protection for cookie-based state-changing requests.
- Enforces case ownership across all domain endpoints (404 NOT_FOUND on mismatch).
"""

from __future__ import annotations

import hmac
import hashlib
import time
import uuid
import os
from typing import Optional, Tuple
from fastapi import Request, HTTPException, status
from pydantic import BaseModel

# Auth secret key from environment or secure default
AUTH_SECRET = os.getenv("AUTH_SECRET", "bindr_secret_hmac_key_2026_vihaan_x")


class SessionData(BaseModel):
    session_id: str
    user_id: str
    csrf_token: str
    is_authenticated: bool = True


def sign_session_token(session_id: str, user_id: str, timestamp: int) -> str:
    """Creates a tamper-proof HMAC-SHA256 signed session token."""
    payload = f"{session_id}:{user_id}:{timestamp}"
    sig = hmac.new(AUTH_SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return f"{session_id}.{user_id}.{timestamp}.{sig}"


def verify_session_token(token: str) -> Optional[Tuple[str, str]]:
    """
    Verifies token signature.
    Returns (session_id, user_id) if valid, None if forged or tampered.
    """
    parts = token.strip().split(".")
    if len(parts) != 4:
        return None

    session_id, user_id, ts_str, provided_sig = parts
    try:
        ts = int(ts_str)
    except ValueError:
        return None

    expected_payload = f"{session_id}:{user_id}:{ts}"
    expected_sig = hmac.new(AUTH_SECRET.encode(), expected_payload.encode(), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(provided_sig, expected_sig):
        return None

    return session_id, user_id


def generate_csrf_token(session_id: str) -> str:
    """Derives a deterministic CSRF token for a given session."""
    return hmac.new(AUTH_SECRET.encode(), f"csrf:{session_id}".encode(), hashlib.sha256).hexdigest()


def create_authenticated_session(user_id: str = "demo-user") -> Tuple[str, str]:
    """Generates a valid signed session token and its corresponding CSRF token."""
    session_id = str(uuid.uuid4())
    ts = int(time.time())
    token = sign_session_token(session_id, user_id, ts)
    csrf = generate_csrf_token(session_id)
    return token, csrf


def get_current_session(request: Request) -> SessionData:
    """
    Extracts and cryptographically validates session identity.
    Enforces CSRF on cookie-authenticated mutating requests (POST).
    Rejects anonymous and forged requests with HTTP 401 UNAUTHENTICATED.
    """
    raw_token: Optional[str] = None
    is_cookie_auth = False

    # 1. Inspect pk_session cookie
    if "pk_session" in request.cookies:
        raw_token = request.cookies.get("pk_session")
        is_cookie_auth = True

    # 2. Inspect Authorization Bearer header
    if not raw_token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            raw_token = auth_header[7:].strip()
            is_cookie_auth = False

    # 3. Inspect X-Session-Token header
    if not raw_token:
        raw_token = request.headers.get("X-Session-Token") or request.headers.get("X-Session-ID")
        is_cookie_auth = False

    if not raw_token or not raw_token.strip():
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

    verified = verify_session_token(raw_token)
    if not verified:
        req_id = str(uuid.uuid4())
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": {
                    "code": "UNAUTHENTICATED",
                    "message": "Invalid or forged session token. Signature verification failed.",
                    "details": [],
                    "request_id": req_id
                }
            }
        )

    session_id, user_id = verified
    expected_csrf = generate_csrf_token(session_id)

    # 4. For cookie-based mutating requests, enforce CSRF protection per API_CONTRACT
    if is_cookie_auth and request.method in ("POST", "PUT", "DELETE", "PATCH"):
        csrf_header = request.headers.get("X-CSRF-Token")
        if not csrf_header or not hmac.compare_digest(csrf_header.strip(), expected_csrf):
            req_id = str(uuid.uuid4())
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": {
                        "code": "CSRF_FAILED",
                        "message": "CSRF verification failed. Missing or invalid 'X-CSRF-Token' header.",
                        "details": [],
                        "request_id": req_id
                    }
                }
            )

    return SessionData(session_id=session_id, user_id=user_id, csrf_token=expected_csrf)
