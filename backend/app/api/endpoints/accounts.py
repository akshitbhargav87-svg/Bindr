"""Account sessions, legacy-workspace attachment and account-scoped cloud settings."""
import hashlib
import hmac
import json
import secrets
import time
from typing import Annotated
from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from backend.app.core.config import settings
from backend.app.core.database import get_db
from backend.app.core.auth import get_current_session, generate_csrf_token, verify_session_token, SessionData
from backend.app.models.account import Account, AccountSession, WorkspaceClaim, AccountPreferences, AccountDraft
from backend.app.models.case import Case
from backend.app.services.identity import factor_version
from backend.app.services.account_auth import fail, check_origin, cookie_name, set_cookie, provider_call, check_user, deployed

router = APIRouter(prefix="/auth", tags=["Accounts"])


class StrictBody(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class Login(StrictBody):
    id_token: str = Field(min_length=20, max_length=20000, repr=False)


def require_accounts():
    if settings.AUTH_PROVIDER != "firebase":
        fail(503, "AUTH_NOT_CONFIGURED", "Account sign-in is not enabled on this deployment.")


@router.get("/config")
def config():
    enabled = settings.AUTH_PROVIDER == "firebase"
    return {"provider": settings.AUTH_PROVIDER, "configured": enabled and all((settings.FIREBASE_PROJECT_ID, settings.FIREBASE_API_KEY, settings.FIREBASE_AUTH_DOMAIN, settings.FIREBASE_APP_ID)),
            "firebase": {"apiKey": settings.FIREBASE_API_KEY, "authDomain": settings.FIREBASE_AUTH_DOMAIN,
                         "projectId": settings.FIREBASE_PROJECT_ID, "appId": settings.FIREBASE_APP_ID} if enabled else None}


@router.get("/csrf")
def login_csrf(response: Response):
    require_accounts()
    nonce = secrets.token_urlsafe(32)
    set_cookie(response, "login", nonce, 600)
    return {"csrf_token": nonce}


@router.post("/login")
def login(payload: Login, request: Request, response: Response, db: Session = Depends(get_db)):
    require_accounts()
    check_origin(request)
    from backend.app.services.rate_limit import enforce_limit
    enforce_limit(("account-login", request.client.host if request.client else "unknown"), 20, 60)
    nonce = request.cookies.get(cookie_name("login"), "")
    if not nonce or not hmac.compare_digest(nonce, request.headers.get("X-CSRF-Token", "")):
        fail(403, "CSRF_FAILED", "Refresh the sign-in page and try again.")
    claims = provider_call("verify", payload.id_token)
    uid = claims.get("uid") or claims.get("sub")
    now = int(time.time())
    auth_time = claims.get("auth_time")
    firebase = claims.get("firebase", {})
    if not isinstance(uid, str) or not uid or type(auth_time) is not int or not 0 <= now - auth_time <= 300:
        fail(401, "RECENT_LOGIN_REQUIRED", "Sign in again to continue securely.")
    if not claims.get("email_verified"):
        fail(403, "EMAIL_NOT_VERIFIED", "Verify your email address before opening your workspace.")
    if firebase.get("sign_in_provider") not in {"google.com", "password"}:
        fail(403, "PROVIDER_NOT_ALLOWED", "Use Google or email and password to sign in.")
    user = provider_call("user", uid)
    check_user(user, auth_time)
    if user.get("mfaInfo") and firebase.get("sign_in_second_factor") != "totp":
        fail(403, "MFA_REQUIRED", "Complete the authenticator code step before signing in.")
    account = db.query(Account).filter(Account.provider_uid == uid).first()
    if account is None:
        account = Account(provider_uid=uid, email=user["email"], display_name=user.get("displayName", "")[:200], created_at=now)
        db.add(account)
        try:
            db.flush()
        except IntegrityError:
            db.rollback()
            account = db.query(Account).filter(Account.provider_uid == uid).one()
    account.email = user["email"]
    account.display_name = user.get("displayName", "")[:200]
    raw = secrets.token_urlsafe(48)
    session = AccountSession(token_hash=hashlib.sha256(raw.encode()).hexdigest(), account_id=account.id,
                             created_at=now, expires_at=now + min(settings.ACCOUNT_SESSION_SECONDS, 1209600),
                             auth_time=auth_time, factor_version=factor_version(user),
                             user_agent=request.headers.get("user-agent", "")[:200])
    db.add(session)
    # Retire a prior browser session on rotation/account switch.
    prior = request.cookies.get(cookie_name("session"), "")
    if prior:
        db.query(AccountSession).filter(AccountSession.token_hash == hashlib.sha256(prior.encode()).hexdigest()).update({"revoked_at": now})
    db.commit()
    set_cookie(response, "session", raw, session.expires_at - now)
    set_cookie(response, "csrf", generate_csrf_token(session.id), session.expires_at - now, False)
    response.delete_cookie(cookie_name("login"), path="/", secure=deployed())
    return {"account": {"id": account.id, "email": account.email, "display_name": account.display_name}, "csrf_token": generate_csrf_token(session.id)}


@router.get("/me")
def me(request: Request, session: SessionData = Depends(get_current_session), db: Session = Depends(get_db)):
    require_accounts()
    legacy = verify_session_token(request.cookies.get("pk_session", ""))
    legacy_count = db.query(Case).filter(Case.owner_id == legacy[1]).count() if legacy else 0
    return {"account": {"id": session.user_id, "email": session.email, "display_name": session.display_name, "provider_uid": request.state.account.provider_uid},
            "csrf_token": session.csrf_token, "mfa_enabled": session.mfa_enabled,
            "legacy_case_count": legacy_count, "expires_at": request.state.account_session.expires_at}


@router.post("/logout")
def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    require_accounts()
    check_origin(request)
    raw = request.cookies.get(cookie_name("session"), "")
    row = db.query(AccountSession).filter(AccountSession.token_hash == hashlib.sha256(raw.encode()).hexdigest()).first() if raw else None
    if row and request.headers.get("X-Bindr-Account") != row.account_id:
        fail(401, "ACCOUNT_CHANGED", "The account changed in another tab. Reopen your workspace.")
    if row and not hmac.compare_digest(request.headers.get("X-CSRF-Token", ""), generate_csrf_token(row.id)):
        fail(403, "CSRF_FAILED", "Refresh Bindr before signing out.")
    if row:
        row.revoked_at = int(time.time())
    db.commit()
    for kind in ("session", "csrf", "login"):
        response.delete_cookie(cookie_name(kind), path="/", secure=deployed())
    return {"signed_out": True}


@router.post("/sign-out-everywhere")
def sign_out_everywhere(request: Request, response: Response, session: SessionData = Depends(get_current_session), db: Session = Depends(get_db)):
    require_accounts()
    if int(time.time()) - (session.auth_time or 0) > 300:
        fail(401, "RECENT_LOGIN_REQUIRED", "Sign in again before signing out all devices.")
    provider_call("revoke", request.state.account.provider_uid)
    db.query(AccountSession).filter(AccountSession.account_id == session.user_id, AccountSession.revoked_at.is_(None)).update({"revoked_at": int(time.time())})
    db.commit()
    for kind in ("session", "csrf"):
        response.delete_cookie(cookie_name(kind), path="/", secure=deployed())
    return {"signed_out": True}


@router.post("/claim-workspace")
def claim_workspace(request: Request, response: Response, session: SessionData = Depends(get_current_session), db: Session = Depends(get_db)):
    require_accounts()
    old = verify_session_token(request.cookies.get("pk_session", ""))
    if not old or not hmac.compare_digest(request.headers.get("X-Legacy-CSRF-Token", ""), generate_csrf_token(old[0])):
        fail(403, "WORKSPACE_UNAVAILABLE", "This browser no longer has access to the previous workspace.")
    owner = old[1]
    claim = db.get(WorkspaceClaim, owner)
    if claim:
        if claim.account_id != session.user_id:
            fail(409, "WORKSPACE_CLAIMED", "These records have already been attached to an account.")
        return {"attached_cases": 0}
    db.add(WorkspaceClaim(owner_id=owner, account_id=session.user_id, claimed_at=int(time.time())))
    try:
        db.flush()
        count = db.query(Case).filter(Case.owner_id == owner).update({"owner_id": session.user_id})
        db.commit()
    except IntegrityError:
        db.rollback()
        fail(409, "WORKSPACE_CLAIMED", "These records have already been attached. Refresh your cases.")
    response.delete_cookie("pk_session", path="/")
    response.delete_cookie("pk_csrf", path="/")
    return {"attached_cases": count}


class Preferences(StrictBody):
    expected_version: int = Field(ge=0)
    deadline_prompts: bool
    case_updates: bool
    read_ids: Annotated[list[Annotated[str, Field(max_length=160)]], Field(max_length=2000)]


@router.get("/preferences")
def get_preferences(session: SessionData = Depends(get_current_session), db: Session = Depends(get_db)):
    require_accounts()
    row = db.get(AccountPreferences, session.user_id)
    return {"version": row.version if row else 0, "preferences": json.loads(row.payload) if row else {"deadline_prompts": True, "case_updates": True, "read_ids": []}}


@router.put("/preferences")
def put_preferences(payload: Preferences, session: SessionData = Depends(get_current_session), db: Session = Depends(get_db)):
    require_accounts()
    data = json.dumps(payload.model_dump(exclude={"expected_version"}))
    if payload.expected_version == 0:
        db.add(AccountPreferences(account_id=session.user_id, payload=data, version=1))
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            fail(409, "VERSION_CONFLICT", "Preferences changed on another device. Refresh before saving.")
    else:
        count = db.query(AccountPreferences).filter(AccountPreferences.account_id == session.user_id, AccountPreferences.version == payload.expected_version).update({"payload": data, "version": payload.expected_version + 1})
        if not count:
            fail(409, "VERSION_CONFLICT", "Preferences changed on another device. Refresh before saving.")
        db.commit()
    return {"version": payload.expected_version + 1}


class DraftBody(StrictBody):
    expected_version: int = Field(ge=0)
    case_version: int = Field(ge=1)
    subject: str = Field(min_length=1, max_length=200)
    body: str = Field(min_length=1, max_length=10000)


@router.get("/drafts")
def drafts(session: SessionData = Depends(get_current_session), db: Session = Depends(get_db)):
    require_accounts()
    rows = db.query(AccountDraft).join(Case, Case.id == AccountDraft.case_id).filter(AccountDraft.account_id == session.user_id, Case.owner_id == session.user_id).all()
    return {"drafts": [{"case_id": row.case_id, "version": row.version, **json.loads(row.payload)} for row in rows]}


@router.put("/drafts/{case_id}")
def save_draft(case_id: str, payload: DraftBody, session: SessionData = Depends(get_current_session), db: Session = Depends(get_db)):
    require_accounts()
    case = db.query(Case).filter(Case.id == case_id, Case.owner_id == session.user_id).first()
    if not case:
        fail(404, "NOT_FOUND", "Case not found.")
    if case.version != payload.case_version:
        fail(409, "VERSION_CONFLICT", "The case changed. Review its latest facts before saving this draft.")
    data = json.dumps(payload.model_dump(exclude={"expected_version"}))
    if payload.expected_version == 0:
        db.add(AccountDraft(case_id=case_id, account_id=session.user_id, payload=data, version=1))
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            fail(409, "VERSION_CONFLICT", "This draft changed on another device. Refresh before saving.")
    else:
        count = db.query(AccountDraft).filter(AccountDraft.case_id == case_id, AccountDraft.account_id == session.user_id, AccountDraft.version == payload.expected_version).update({"payload": data, "version": payload.expected_version + 1})
        if not count:
            fail(409, "VERSION_CONFLICT", "This draft changed on another device. Refresh before saving.")
        db.commit()
    return {"version": payload.expected_version + 1}
