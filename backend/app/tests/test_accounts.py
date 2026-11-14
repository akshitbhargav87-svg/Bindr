"""Real HTTP/SQL authorization tests with only Google's external identity boundary stubbed."""
import copy
import hashlib
import time
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.core.config import settings
from backend.app.core.database import get_db
from backend.app.core.auth import create_authenticated_session
from backend.app.models.case import Case
from backend.app.models.account import AccountSession
from backend.app.services import account_auth
from backend.app.services.identity import InvalidIdentity, IdentityUnavailable

ORIGIN = "https://testserver"


class Provider:
    def __init__(self):
        self.records = {}
        self.tokens = {}
        self.revoked = []

    def add(self, uid="person-a", **changes):
        record = {"localId": uid, "email": uid + "@example.test", "emailVerified": True, "displayName": "Test Person", "validSince": "0", "mfaInfo": []}
        record.update(changes)
        self.records[uid] = record
        token = uid + "-" + "x" * 30
        self.tokens[token] = {"uid": uid, "email_verified": True, "auth_time": int(time.time()), "firebase": {"sign_in_provider": "password"}}
        return token

    def verify(self, token):
        if token not in self.tokens:
            raise InvalidIdentity()
        return copy.deepcopy(self.tokens[token])

    def user(self, uid):
        if uid not in self.records:
            raise InvalidIdentity()
        return copy.deepcopy(self.records[uid])

    def revoke(self, uid):
        self.revoked.append(uid)


@pytest.fixture
def accounts(db_session, monkeypatch):
    for name, value in {"AUTH_PROVIDER": "firebase", "ENVIRONMENT": "production", "AUTH_SECRET": "x" * 64,
                        "FIREBASE_PROJECT_ID": "test-project", "FIREBASE_API_KEY": "test-public-key",
                        "FIREBASE_AUTH_DOMAIN": "test-project.firebaseapp.com", "FIREBASE_APP_ID": "test-app"}.items():
        monkeypatch.setattr(settings, name, value)
    monkeypatch.setattr(settings, "CORS_ORIGINS", [ORIGIN])
    provider = Provider()
    monkeypatch.setattr(account_auth, "get_identity_provider", lambda: provider)
    app.dependency_overrides[get_db] = lambda: db_session
    with TestClient(app, base_url=ORIGIN, headers={"Origin": ORIGIN}) as client:
        yield client, provider, db_session
    app.dependency_overrides.clear()


def login(client, token):
    nonce = client.get("/api/v1/auth/csrf").json()["csrf_token"]
    response = client.post("/api/v1/auth/login", json={"id_token": token}, headers={"X-CSRF-Token": nonce})
    if response.status_code == 200:
        client.headers["X-CSRF-Token"] = response.json()["csrf_token"]
        client.headers["X-Bindr-Account"] = response.json()["account"]["id"]
    return response


def test_login_cloud_identity_is_stable_across_devices_and_sessions_are_private(accounts):
    client, provider, db = accounts
    token = provider.add()
    response = login(client, token)
    assert response.status_code == 200
    cookie = next(x for x in response.headers.get_list("set-cookie") if x.startswith("__Host-bindr_session="))
    assert "HttpOnly" in cookie and "Secure" in cookie and "SameSite=lax" in cookie and "Domain=" not in cookie
    raw = client.cookies.get("__Host-bindr_session")
    assert db.query(AccountSession).filter_by(token_hash=hashlib.sha256(raw.encode()).hexdigest()).one()
    case = client.post("/api/v1/cases", json={"title": "Private refund", "merchant_name": "Test Shop"}).json()["case"]
    account_id = response.json()["account"]["id"]
    client.cookies.clear()
    assert client.get("/api/v1/cases").status_code == 401
    assert login(client, token).json()["account"]["id"] == account_id
    assert client.get("/api/v1/cases/" + case["id"]).status_code == 200


@pytest.mark.parametrize("change,expected", [("unverified_claim", 403), ("unverified_record", 401), ("disabled", 401), ("old_login", 401), ("future_login", 401), ("anonymous", 403), ("revoked", 401)])
def test_invalid_identity_never_receives_a_workspace_cookie(accounts, change, expected):
    client, provider, db = accounts
    token = provider.add()
    if change == "unverified_claim": provider.tokens[token]["email_verified"] = False
    if change == "unverified_record": provider.records["person-a"]["emailVerified"] = False
    if change == "disabled": provider.records["person-a"]["disabled"] = True
    if change == "old_login": provider.tokens[token]["auth_time"] -= 301
    if change == "future_login": provider.tokens[token]["auth_time"] += 90
    if change == "anonymous": provider.tokens[token]["firebase"]["sign_in_provider"] = "anonymous"
    if change == "revoked": provider.records["person-a"]["validSince"] = str(int(time.time()) + 1)
    assert login(client, token).status_code == expected
    assert db.query(AccountSession).count() == 0
    assert "__Host-bindr_session" not in client.cookies


def test_mfa_is_enforced_on_server_not_just_in_the_screen(accounts):
    client, provider, _ = accounts
    token = provider.add(mfaInfo=[{"mfaEnrollmentId": "factor-a", "totpInfo": {}}])
    assert login(client, token).json()["error"]["code"] == "MFA_REQUIRED"
    provider.tokens[token]["firebase"]["sign_in_second_factor"] = "totp"
    assert login(client, token).status_code == 200
    assert client.get("/api/v1/auth/me").json()["mfa_enabled"] is True


@pytest.mark.parametrize("change", ["mfa", "disabled", "password_reset", "expired", "revoked", "deleted"])
def test_security_changes_invalidate_existing_sessions(accounts, change):
    client, provider, db = accounts
    assert login(client, provider.add()).status_code == 200
    row = db.query(AccountSession).one()
    if change == "mfa": provider.records["person-a"]["mfaInfo"] = [{"mfaEnrollmentId": "new", "totpInfo": {}}]
    if change == "disabled": provider.records["person-a"]["disabled"] = True
    if change == "password_reset": provider.records["person-a"]["validSince"] = str(int(time.time()) + 1)
    if change == "expired": row.expires_at = int(time.time()) - 1
    if change == "revoked": row.revoked_at = int(time.time())
    if change == "deleted": del provider.records["person-a"]
    db.commit()
    assert client.get("/api/v1/cases").status_code == 401


def test_no_anonymous_or_bearer_bypass_in_account_mode(accounts):
    client, _, _ = accounts
    token, csrf = create_authenticated_session(user_id="demo-user")
    client.cookies.set("pk_session", token)
    client.headers["X-CSRF-Token"] = csrf
    assert client.post("/api/v1/auth/session", json={}).status_code == 401
    assert client.get("/api/v1/cases").status_code == 401
    assert client.get("/api/v1/cases", headers={"Authorization": "Bearer " + token}).status_code == 401


def test_origin_and_csrf_are_required_before_login_and_every_write(accounts):
    client, provider, _ = accounts
    token = provider.add()
    assert client.post("/api/v1/auth/login", json={"id_token": token}).status_code == 403
    nonce = client.get("/api/v1/auth/csrf").json()["csrf_token"]
    assert client.post("/api/v1/auth/login", json={"id_token": token}, headers={"Origin": "https://evil.test", "X-CSRF-Token": nonce}).status_code == 403
    assert login(client, token).status_code == 200
    assert client.post("/api/v1/cases", json={"title": "x", "merchant_name": "y"}, headers={"X-CSRF-Token": "wrong"}).status_code == 403
    assert client.post("/api/v1/cases", json={"title": "x", "merchant_name": "y"}, headers={"Origin": "https://evil.test"}).status_code == 403


def test_logout_revokes_stolen_cookie_even_when_provider_is_unavailable(accounts, monkeypatch):
    client, provider, _ = accounts
    login(client, provider.add())
    raw = client.cookies.get("__Host-bindr_session")
    monkeypatch.setattr(provider, "user", lambda uid: (_ for _ in ()).throw(IdentityUnavailable()))
    assert client.get("/api/v1/cases").status_code == 503
    assert client.post("/api/v1/auth/logout", json={}).status_code == 200
    assert "__Host-bindr_session" not in client.cookies
    client.cookies.set("__Host-bindr_session", raw)
    assert client.get("/api/v1/cases").status_code == 401


def test_cross_account_cases_and_files_are_never_visible(accounts):
    client, provider, _ = accounts
    login(client, provider.add())
    case = client.post("/api/v1/cases", json={"title": "Private", "merchant_name": "Shop"}).json()["case"]
    upload = client.post(f"/api/v1/cases/{case['id']}/evidence", data={"expected_version": case["version"]}, files={"file": ("private.txt", b"We will refund INR 100.", "text/plain")})
    assert upload.status_code == 201
    download = upload.json()["evidence"]["download_path"]
    assert client.get(download).content == b"We will refund INR 100."
    login(client, provider.add("person-b"))
    assert client.get("/api/v1/cases").json()["cases"] == []
    assert client.get("/api/v1/cases/" + case["id"]).status_code == 404
    assert client.get(download).status_code == 404


def test_legacy_workspace_requires_both_sessions_and_cannot_be_claimed_twice(accounts):
    client, provider, db = accounts
    old, old_csrf = create_authenticated_session(user_id="old-browser")
    db.add(Case(owner_id="old-browser", title="Earlier case", merchant_name="Shop")); db.commit()
    client.cookies.set("pk_session", old)
    client.cookies.set("pk_csrf", old_csrf)
    login(client, provider.add())
    assert client.get("/api/v1/auth/me").json()["legacy_case_count"] == 1
    client.get("/api/v1/auth/session")  # Must not overwrite the old CSRF cookie.
    assert client.cookies.get("pk_csrf") == old_csrf
    assert client.post("/api/v1/auth/claim-workspace", json={}).status_code == 403
    assert client.post("/api/v1/auth/claim-workspace", json={}, headers={"X-Legacy-CSRF-Token": old_csrf}).json()["attached_cases"] == 1
    assert len(client.get("/api/v1/cases").json()["cases"]) == 1
    login(client, provider.add("person-b")); client.cookies.set("pk_session", old)
    assert client.post("/api/v1/auth/claim-workspace", json={}, headers={"X-Legacy-CSRF-Token": old_csrf}).status_code == 409


def test_cloud_preferences_and_drafts_are_owned_versioned_and_persist_after_signin(accounts):
    client, provider, _ = accounts
    a = provider.add(); login(client, a)
    case = client.post("/api/v1/cases", json={"title": "Private", "merchant_name": "Shop"}).json()["case"]
    prefs = {"expected_version": 0, "deadline_prompts": False, "case_updates": True, "read_ids": ["event-1"]}
    assert client.put("/api/v1/auth/preferences", json=prefs).status_code == 200
    assert client.put("/api/v1/auth/preferences", json=prefs).status_code == 409
    draft = {"expected_version": 0, "case_version": case["version"], "subject": "Follow up", "body": "Private draft"}
    path = "/api/v1/auth/drafts/" + case["id"]
    assert client.put(path, json=draft).status_code == 200
    assert client.put(path, json=draft).status_code == 409
    login(client, provider.add("person-b"))
    assert client.get("/api/v1/auth/preferences").json()["version"] == 0
    assert client.get("/api/v1/auth/drafts").json()["drafts"] == []
    assert client.put(path, json=draft).status_code == 404
    login(client, a)
    assert client.get("/api/v1/auth/preferences").json()["preferences"]["deadline_prompts"] is False
    assert client.get("/api/v1/auth/drafts").json()["drafts"][0]["body"] == "Private draft"


def test_sign_out_everywhere_revokes_all_account_sessions(accounts):
    client, provider, db = accounts
    token = provider.add(); login(client, token); login(client, token)
    assert client.post("/api/v1/auth/sign-out-everywhere", json={}).status_code == 200
    assert all(row.revoked_at for row in db.query(AccountSession).all())
    assert provider.revoked == ["person-a"]


def test_bad_token_and_caller_selected_identity_cannot_create_an_account_session(accounts):
    client, provider, db = accounts
    assert login(client, "not-a-valid-token-" + "x" * 25).status_code == 401
    nonce = client.get("/api/v1/auth/csrf").json()["csrf_token"]
    assert client.post("/api/v1/auth/login", json={"id_token": provider.add(), "user_id": "someone-else"}, headers={"X-CSRF-Token": nonce}).status_code == 422
    assert db.query(AccountSession).count() == 0


def test_stale_tab_cannot_read_or_write_another_accounts_cookie(accounts):
    client, provider, db = accounts
    login(client, provider.add())
    old_account = client.headers["X-Bindr-Account"]
    login(client, provider.add("person-b"))
    client.headers["X-Bindr-Account"] = old_account
    assert client.get("/api/v1/cases").status_code == 401
    assert client.post("/api/v1/cases", json={"title": "Stale form", "merchant_name": "Shop"}).status_code == 401
    assert client.put("/api/v1/auth/preferences", json={"expected_version": 0, "deadline_prompts": False, "case_updates": True, "read_ids": []}).status_code == 401
    assert client.post("/api/v1/auth/logout", json={}).status_code == 401
    assert db.query(Case).count() == 0
    # /me is the safe refresh path for discovering the newly signed-in account.
    assert client.get("/api/v1/auth/me", headers={"X-Bindr-Account": ""}).status_code == 200


def test_account_write_requires_an_explicit_tab_identity(accounts):
    client, provider, _ = accounts
    login(client, provider.add())
    del client.headers["X-Bindr-Account"]
    assert client.post("/api/v1/cases", json={"title": "Missing context", "merchant_name": "Shop"}).status_code == 403


def test_google_sdk_receives_project_app_and_revocation_check(monkeypatch):
    from firebase_admin import auth
    from backend.app.services.identity import GoogleIdentity
    provider = GoogleIdentity.__new__(GoogleIdentity)
    provider.app = object()
    calls = []
    monkeypatch.setattr(auth, "verify_id_token", lambda token, **kwargs: calls.append((token, kwargs)) or {"uid": "verified-by-sdk"})
    assert provider.verify("opaque-id-token")["uid"] == "verified-by-sdk"
    assert calls == [("opaque-id-token", {"app": provider.app, "check_revoked": True})]
