"""Opaque, server-revocable account cookies backed by cloud SQL and Google identity."""
import hashlib
import hmac
import secrets
import time
from fastapi import HTTPException
from backend.app.core.config import settings
from backend.app.models.account import Account, AccountSession
from backend.app.services.identity import get_identity_provider, factor_version, InvalidIdentity, IdentityUnavailable


def fail(status, code, message):
    raise HTTPException(status, detail={"error": {"code": code, "message": message, "details": [], "request_id": secrets.token_hex(16)}})


def deployed():
    return settings.ENVIRONMENT.lower() in {"production", "prod", "staging", "deployed"}


def cookie_name(kind):
    return ("__Host-bindr_" if deployed() else "bindr_") + kind


def set_cookie(response, kind, value, seconds, http_only=True):
    response.set_cookie(cookie_name(kind), value, max_age=seconds, path="/", secure=deployed(), httponly=http_only, samesite="lax")


def check_origin(request):
    origin = request.headers.get("origin", "").rstrip("/")
    allowed = {o.rstrip("/") for o in settings.CORS_ORIGINS} | {str(request.base_url).rstrip("/")}
    if not origin or origin not in allowed:
        fail(403, "CSRF_FAILED", "Open Bindr directly to complete this request.")


def provider_call(method, *args):
    try:
        return getattr(get_identity_provider(), method)(*args)
    except InvalidIdentity:
        fail(401, "UNAUTHENTICATED", "Sign in again to continue.")
    except IdentityUnavailable:
        fail(503, "AUTH_UNAVAILABLE", "Sign-in is temporarily unavailable. Please try again.")


def check_user(user, auth_time, version=None):
    if user.get("disabled") or not user.get("emailVerified") or not user.get("email"):
        fail(401, "UNAUTHENTICATED", "Verify your email and sign in again.")
    if auth_time < int(user.get("validSince", 0)):
        fail(401, "SESSION_REVOKED", "Your account security changed. Sign in again.")
    if version is not None and version != factor_version(user):
        fail(401, "SESSION_REVOKED", "Your two-factor settings changed. Sign in again.")


def current_account_session(request, db):
    from backend.app.core.auth import SessionData, generate_csrf_token
    raw = request.cookies.get(cookie_name("session"), "")
    if not raw or len(raw) > 256:
        fail(401, "UNAUTHENTICATED", "Sign in to open your workspace.")
    row = db.query(AccountSession).filter(AccountSession.token_hash == hashlib.sha256(raw.encode()).hexdigest()).first()
    now = int(time.time())
    if not row or row.revoked_at is not None or row.expires_at <= now:
        fail(401, "UNAUTHENTICATED", "Your session ended. Sign in again.")
    account = db.get(Account, row.account_id)
    if not account:
        fail(401, "UNAUTHENTICATED", "Sign in again to continue.")
    from backend.app.services.platform.accounts import ensure_active
    ensure_active(db, account.id)
    expected_account = request.headers.get("X-Bindr-Account")
    if expected_account and expected_account != account.id:
        fail(401, "ACCOUNT_CHANGED", "The account changed in another tab. Reopen your workspace.")
    if request.method in {"POST", "PUT", "PATCH", "DELETE"} and expected_account != account.id:
        fail(403, "ACCOUNT_REQUIRED", "Refresh your account before trying again.")
    user = provider_call("user", account.provider_uid)
    check_user(user, row.auth_time, row.factor_version)
    csrf = generate_csrf_token(row.id)
    if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
        check_origin(request)
        if not hmac.compare_digest(request.headers.get("X-CSRF-Token", ""), csrf):
            fail(403, "CSRF_FAILED", "Refresh Bindr before trying again.")
    request.state.account = account
    request.state.account_session = row
    request.state.identity_user = user
    return SessionData(session_id=row.id, user_id=account.id, csrf_token=csrf,
                       email=user["email"], display_name=user.get("displayName", ""),
                       mfa_enabled=bool(user.get("mfaInfo")), auth_time=row.auth_time)
