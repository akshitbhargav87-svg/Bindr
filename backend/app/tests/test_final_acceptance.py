import io
import time
import pytest
from sqlalchemy import create_engine, text, Column, String, Integer, Table, MetaData
from sqlalchemy.orm import sessionmaker

from backend.app.core.config import settings
from backend.app.core.auth import (
    sign_session_token,
    verify_session_token,
    create_authenticated_session,
    get_auth_secret,
    generate_csrf_token,
)
from backend.app.core.database import run_sqlite_migrations
from backend.app.services.ai_adapter import (
    ai_adapter,
    validate_ai_extraction_output,
    AIInvalidOutputError,
)
from backend.app.models.case import Case
from backend.app.models.extraction import Extraction


def _create_case(client, title="Audit Case", merchant="Shop"):
    res = client.post("/api/v1/cases", json={"title": title, "merchant_name": merchant})
    assert res.status_code == 201
    return res.json()["case"]


def _upload_text_evidence(client, case_id, text_content, expected_version=1):
    files = {"file": ("note.txt", io.BytesIO(text_content.encode("utf-8")), "text/plain")}
    res = client.post(
        f"/api/v1/cases/{case_id}/evidence",
        files=files,
        data={"expected_version": str(expected_version)}
    )
    assert res.status_code == 201
    return res.json()["evidence"], res.json()["case_version"]


# ---------------------------------------------------------------------------
# 1. SIX MALFORMED AI-OUTPUT VARIANTS REJECTED BEFORE DRAFT PERSISTENCE
# ---------------------------------------------------------------------------

def test_ai_malformed_variant_1_schema_version_and_root_keys(client, db_session, monkeypatch):
    """Variant 1: Invalid schema_version or unexpected root keys rejected before persistence."""
    case = _create_case(client)
    evidence, ver = _upload_text_evidence(client, case["id"], "We will refund INR 500 within 3 days.")

    # 1a. Unsupported schema version
    monkeypatch.setattr(ai_adapter, "extract_commitments", lambda **kw: {"schema_version": 2, "candidates": []})
    res = client.post(f"/api/v1/cases/{case['id']}/extractions", json={"evidence_ids": [evidence["id"]]})
    assert res.status_code == 502
    assert res.json()["error"]["code"] == "AI_INVALID_OUTPUT"

    # Verify no draft was persisted in the DB
    drafts = db_session.query(Extraction).filter(Extraction.case_id == case["id"]).all()
    assert len(drafts) == 0

    # 1b. Unexpected root keys
    monkeypatch.setattr(
        ai_adapter, "extract_commitments",
        lambda **kw: {"schema_version": 1, "candidates": [], "unexpected_extra_key": True}
    )
    res2 = client.post(f"/api/v1/cases/{case['id']}/extractions", json={"evidence_ids": [evidence["id"]]})
    assert res2.status_code == 502
    assert res2.json()["error"]["code"] == "AI_INVALID_OUTPUT"


def test_ai_malformed_variant_2_candidate_shape_id_and_uniqueness(client, db_session, monkeypatch):
    """Variant 2: Non-matching candidate_id regex or duplicate candidate_ids rejected."""
    case = _create_case(client)
    evidence, ver = _upload_text_evidence(client, case["id"], "We will refund INR 500 within 3 days.")

    # 2a. Invalid candidate_id format (must match ^c[1-9][0-9]*$)
    bad_id_cand = {
        "candidate_id": "invalid-id-123",
        "terms": {"kind": "refund", "description": "Refund", "amount_minor": 50000, "currency": "INR", "due_at": None},
        "sources": [{"evidence_id": evidence["id"], "quote": "refund INR 500"}],
        "confidence": 0.95,
        "warnings": [],
        "revision": {"relation": "new", "supersedes_id": None, "reason": "New"}
    }
    monkeypatch.setattr(
        ai_adapter, "extract_commitments",
        lambda **kw: {"schema_version": 1, "candidates": [bad_id_cand]}
    )
    res = client.post(f"/api/v1/cases/{case['id']}/extractions", json={"evidence_ids": [evidence["id"]]})
    assert res.status_code == 502
    assert res.json()["error"]["code"] == "AI_INVALID_OUTPUT"

    # 2b. Duplicate candidate IDs within the same draft
    cand_dup1 = dict(bad_id_cand, candidate_id="c1")
    cand_dup2 = dict(bad_id_cand, candidate_id="c1")
    monkeypatch.setattr(
        ai_adapter, "extract_commitments",
        lambda **kw: {"schema_version": 1, "candidates": [cand_dup1, cand_dup2]}
    )
    res2 = client.post(f"/api/v1/cases/{case['id']}/extractions", json={"evidence_ids": [evidence["id"]]})
    assert res2.status_code == 502
    assert res2.json()["error"]["code"] == "AI_INVALID_OUTPUT"

    # Verify no draft persisted
    assert db_session.query(Extraction).filter(Extraction.case_id == case["id"]).count() == 0


def test_ai_malformed_variant_3_terms_validation_and_bounds(client, db_session, monkeypatch):
    """Variant 3: Invalid kind enum, empty description, or negative amount_minor rejected."""
    case = _create_case(client)
    evidence, ver = _upload_text_evidence(client, case["id"], "We will refund INR 500 within 3 days.")

    # 3a. Invalid kind enum
    bad_kind_cand = {
        "candidate_id": "c1",
        "terms": {"kind": "unsupported_kind", "description": "Refund", "amount_minor": 50000, "currency": "INR", "due_at": None},
        "sources": [{"evidence_id": evidence["id"], "quote": "refund INR 500"}],
        "confidence": 0.95,
        "warnings": [],
        "revision": {"relation": "new", "supersedes_id": None, "reason": "New"}
    }
    monkeypatch.setattr(
        ai_adapter, "extract_commitments",
        lambda **kw: {"schema_version": 1, "candidates": [bad_kind_cand]}
    )
    res = client.post(f"/api/v1/cases/{case['id']}/extractions", json={"evidence_ids": [evidence["id"]]})
    assert res.status_code == 502
    assert res.json()["error"]["code"] == "AI_INVALID_OUTPUT"

    # 3b. Negative amount_minor
    bad_amt_cand = {
        "candidate_id": "c1",
        "terms": {"kind": "refund", "description": "Refund", "amount_minor": -100, "currency": "INR", "due_at": None},
        "sources": [{"evidence_id": evidence["id"], "quote": "refund INR 500"}],
        "confidence": 0.95,
        "warnings": [],
        "revision": {"relation": "new", "supersedes_id": None, "reason": "New"}
    }
    monkeypatch.setattr(
        ai_adapter, "extract_commitments",
        lambda **kw: {"schema_version": 1, "candidates": [bad_amt_cand]}
    )
    res2 = client.post(f"/api/v1/cases/{case['id']}/extractions", json={"evidence_ids": [evidence["id"]]})
    assert res2.status_code == 502
    assert res2.json()["error"]["code"] == "AI_INVALID_OUTPUT"


def test_ai_malformed_variant_4_money_pairing_rules(client, db_session, monkeypatch):
    """Variant 4: Amount without currency or currency without amount rejected."""
    case = _create_case(client)
    evidence, ver = _upload_text_evidence(client, case["id"], "We will refund INR 500 within 3 days.")

    # 4a. Amount present without currency
    bad_pairing_1 = {
        "candidate_id": "c1",
        "terms": {"kind": "refund", "description": "Refund", "amount_minor": 50000, "currency": None, "due_at": None},
        "sources": [{"evidence_id": evidence["id"], "quote": "refund INR 500"}],
        "confidence": 0.95,
        "warnings": [],
        "revision": {"relation": "new", "supersedes_id": None, "reason": "New"}
    }
    monkeypatch.setattr(
        ai_adapter, "extract_commitments",
        lambda **kw: {"schema_version": 1, "candidates": [bad_pairing_1]}
    )
    res = client.post(f"/api/v1/cases/{case['id']}/extractions", json={"evidence_ids": [evidence["id"]]})
    assert res.status_code == 502
    assert res.json()["error"]["code"] == "AI_INVALID_OUTPUT"

    # 4b. Currency present without amount
    bad_pairing_2 = dict(bad_pairing_1, terms={"kind": "refund", "description": "Refund", "amount_minor": None, "currency": "INR", "due_at": None})
    monkeypatch.setattr(
        ai_adapter, "extract_commitments",
        lambda **kw: {"schema_version": 1, "candidates": [bad_pairing_2]}
    )
    res2 = client.post(f"/api/v1/cases/{case['id']}/extractions", json={"evidence_ids": [evidence["id"]]})
    assert res2.status_code == 502
    assert res2.json()["error"]["code"] == "AI_INVALID_OUTPUT"


def test_ai_malformed_variant_5_sources_citation_and_verbatim_check(client, db_session, monkeypatch):
    """Variant 5: Empty sources, invented evidence ID, or non-verbatim quote rejected."""
    case = _create_case(client)
    evidence, ver = _upload_text_evidence(client, case["id"], "We will refund INR 500 within 3 days.")

    # 5a. Invented evidence ID not in request
    invented_eid_cand = {
        "candidate_id": "c1",
        "terms": {"kind": "refund", "description": "Refund", "amount_minor": 50000, "currency": "INR", "due_at": None},
        "sources": [{"evidence_id": "invented-evidence-9999", "quote": "refund INR 500"}],
        "confidence": 0.95,
        "warnings": [],
        "revision": {"relation": "new", "supersedes_id": None, "reason": "New"}
    }
    monkeypatch.setattr(
        ai_adapter, "extract_commitments",
        lambda **kw: {"schema_version": 1, "candidates": [invented_eid_cand]}
    )
    res = client.post(f"/api/v1/cases/{case['id']}/extractions", json={"evidence_ids": [evidence["id"]]})
    assert res.status_code == 502
    assert res.json()["error"]["code"] == "AI_INVALID_OUTPUT"

    # 5b. Non-verbatim quote (quote not in evidence text)
    bad_quote_cand = {
        "candidate_id": "c1",
        "terms": {"kind": "refund", "description": "Refund", "amount_minor": 50000, "currency": "INR", "due_at": None},
        "sources": [{"evidence_id": evidence["id"], "quote": "This sentence definitely does not exist in note"}],
        "confidence": 0.95,
        "warnings": [],
        "revision": {"relation": "new", "supersedes_id": None, "reason": "New"}
    }
    monkeypatch.setattr(
        ai_adapter, "extract_commitments",
        lambda **kw: {"schema_version": 1, "candidates": [bad_quote_cand]}
    )
    res2 = client.post(f"/api/v1/cases/{case['id']}/extractions", json={"evidence_ids": [evidence["id"]]})
    assert res2.status_code == 502
    assert res2.json()["error"]["code"] == "AI_INVALID_OUTPUT"


def test_ai_malformed_variant_6_metadata_and_revision_bounds(client, db_session, monkeypatch):
    """Variant 6: Confidence out of range [0, 1] or invalid revision relation rejected."""
    case = _create_case(client)
    evidence, ver = _upload_text_evidence(client, case["id"], "We will refund INR 500 within 3 days.")

    # 6a. Confidence > 1.0
    bad_conf_cand = {
        "candidate_id": "c1",
        "terms": {"kind": "refund", "description": "Refund", "amount_minor": 50000, "currency": "INR", "due_at": None},
        "sources": [{"evidence_id": evidence["id"], "quote": "refund INR 500"}],
        "confidence": 1.5,
        "warnings": [],
        "revision": {"relation": "new", "supersedes_id": None, "reason": "New"}
    }
    monkeypatch.setattr(
        ai_adapter, "extract_commitments",
        lambda **kw: {"schema_version": 1, "candidates": [bad_conf_cand]}
    )
    res = client.post(f"/api/v1/cases/{case['id']}/extractions", json={"evidence_ids": [evidence["id"]]})
    assert res.status_code == 502
    assert res.json()["error"]["code"] == "AI_INVALID_OUTPUT"

    # 6b. Invalid revision relation
    bad_rev_cand = {
        "candidate_id": "c1",
        "terms": {"kind": "refund", "description": "Refund", "amount_minor": 50000, "currency": "INR", "due_at": None},
        "sources": [{"evidence_id": evidence["id"], "quote": "refund INR 500"}],
        "confidence": 0.9,
        "warnings": [],
        "revision": {"relation": "invented_relation", "supersedes_id": None, "reason": "Reason"}
    }
    monkeypatch.setattr(
        ai_adapter, "extract_commitments",
        lambda **kw: {"schema_version": 1, "candidates": [bad_rev_cand]}
    )
    res2 = client.post(f"/api/v1/cases/{case['id']}/extractions", json={"evidence_ids": [evidence["id"]]})
    assert res2.status_code == 502
    assert res2.json()["error"]["code"] == "AI_INVALID_OUTPUT"


# ---------------------------------------------------------------------------
# 2. SESSION EXPIRATION, FUTURE-ISSUED TIMESTAMPS, AND LIFETIME VALIDATION
# ---------------------------------------------------------------------------

def test_session_token_expired_is_rejected(anonymous_client):
    """Session token older than SESSION_LIFETIME_SECONDS is rejected with 401."""
    now = int(time.time())
    # Issued 2 days ago (default lifetime 86400s = 1 day)
    expired_ts = now - 172800
    expired_token = sign_session_token("test-session-id", "demo-user", expired_ts)

    anonymous_client.cookies.set("pk_session", expired_token)
    res = anonymous_client.get("/api/v1/cases")
    assert res.status_code == 401
    assert res.json()["error"]["code"] == "UNAUTHENTICATED"


def test_session_token_future_issued_is_rejected(anonymous_client):
    """Session token issued in the future (beyond clock skew) is rejected with 401."""
    now = int(time.time())
    # Issued 1 hour into the future
    future_ts = now + 3600
    future_token = sign_session_token("test-session-id", "demo-user", future_ts)

    anonymous_client.cookies.set("pk_session", future_token)
    res = anonymous_client.get("/api/v1/cases")
    assert res.status_code == 401
    assert res.json()["error"]["code"] == "UNAUTHENTICATED"


def test_session_token_valid_within_lifetime(anonymous_client):
    """Valid signed token within lifetime succeeds."""
    token, csrf = create_authenticated_session("test-user")
    anonymous_client.cookies.set("pk_session", token)
    anonymous_client.headers["X-CSRF-Token"] = csrf

    res = anonymous_client.get("/api/v1/cases")
    assert res.status_code == 200


# ---------------------------------------------------------------------------
# 3. STRONG CONFIGURED AUTH_SECRET ENFORCEMENT
# ---------------------------------------------------------------------------

def test_production_environment_rejects_weak_or_missing_auth_secret(monkeypatch):
    """In deployed/production environments, weak or missing secret raises RuntimeError."""
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")

    # Missing secret
    monkeypatch.setattr(settings, "AUTH_SECRET", None)
    monkeypatch.delenv("AUTH_SECRET", raising=False)
    with pytest.raises(RuntimeError) as exc:
        get_auth_secret()
    assert "In deployed environments, a strong AUTH_SECRET" in str(exc.value)

    # Insecure/predictable fallback secret
    monkeypatch.setattr(settings, "AUTH_SECRET", "bindr_secret_hmac_key_2026_vihaan_x")
    with pytest.raises(RuntimeError) as exc:
        get_auth_secret()
    assert "Predictable fallbacks are strictly forbidden" in str(exc.value)

    # Strong 32+ character secret succeeds
    strong_key = "a_very_strong_production_hmac_secret_key_exceeding_32_bytes_2026"
    monkeypatch.setattr(settings, "AUTH_SECRET", strong_key)
    assert get_auth_secret() == strong_key


# ---------------------------------------------------------------------------
# 4. CROSS-ORIGIN AND ORIGIN/CSRF POLICY ENFORCEMENT
# ---------------------------------------------------------------------------

def test_unauthorized_cross_origin_request_rejected(anonymous_client):
    """Mutating cookie request from unauthorized Origin returns 403 CSRF_FAILED."""
    token, csrf = create_authenticated_session("demo-user")
    anonymous_client.cookies.set("pk_session", token)
    anonymous_client.headers["X-CSRF-Token"] = csrf
    anonymous_client.headers["Origin"] = "http://evil-attacker.com"

    res = anonymous_client.post("/api/v1/cases", json={"title": "Attack", "merchant_name": "Shop"})
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "CSRF_FAILED"
    assert "Unauthorized cross-origin request" in res.json()["error"]["message"]


def test_authorized_cross_origin_request_succeeds(anonymous_client):
    """Mutating cookie request from authorized Origin succeeds."""
    token, csrf = create_authenticated_session("demo-user")
    anonymous_client.cookies.set("pk_session", token)
    anonymous_client.headers["X-CSRF-Token"] = csrf
    anonymous_client.headers["Origin"] = "http://localhost:3000"

    res = anonymous_client.post("/api/v1/cases", json={"title": "Valid Origin", "merchant_name": "Shop"})
    assert res.status_code == 201


# ---------------------------------------------------------------------------
# 5. SQLITE MIGRATION FOR EXISTING DATABASES
# ---------------------------------------------------------------------------

def test_sqlite_migration_adds_owner_id_to_legacy_table():
    """run_sqlite_migrations adds owner_id column to existing cases table without data loss."""
    # Create an in-memory SQLite database simulating legacy Milestone 1 schema
    legacy_engine = create_engine("sqlite:///:memory:")
    with legacy_engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE cases (
                id VARCHAR(36) PRIMARY KEY,
                title VARCHAR(200) NOT NULL,
                merchant_name VARCHAR(200) NOT NULL,
                status VARCHAR(50) NOT NULL DEFAULT 'open',
                version INTEGER NOT NULL DEFAULT 1,
                created_at VARCHAR(50) NOT NULL
            )
        """))
        conn.execute(text("""
            INSERT INTO cases (id, title, merchant_name, status, version, created_at)
            VALUES ('legacy-c1', 'Old Case', 'Old Merchant', 'open', 1, '2026-11-14T09:00:00Z')
        """))

    # Verify column does not exist initially
    with legacy_engine.connect() as conn:
        cols_before = [row[1] for row in conn.execute(text("PRAGMA table_info(cases)")).fetchall()]
        assert "owner_id" not in cols_before

    # Run safe migration
    run_sqlite_migrations(legacy_engine)

    # Verify column now exists and legacy row has default owner_id
    with legacy_engine.connect() as conn:
        cols_after = [row[1] for row in conn.execute(text("PRAGMA table_info(cases)")).fetchall()]
        assert "owner_id" in cols_after

        row = conn.execute(text("SELECT id, owner_id FROM cases WHERE id = 'legacy-c1'")).fetchone()
        assert row[0] == "legacy-c1"
        assert row[1] == "demo-user"


# ---------------------------------------------------------------------------
# 6. BROWSER SESSION AND CSRF BOOTSTRAP FLOW
# ---------------------------------------------------------------------------

def test_browser_session_bootstrap_flow(anonymous_client):
    """Complete browser bootstrap flow: POST /auth/session -> cookies set -> authenticated mutation."""
    # 1. Bootstrap session
    boot_res = anonymous_client.post("/api/v1/auth/session", json={"user_id": "test-browser-user"})
    assert boot_res.status_code == 201
    boot_data = boot_res.json()
    assert boot_data["user_id"] == "test-browser-user"
    assert "csrf_token" in boot_data
    assert "session_id" in boot_data

    # Cookies must be set
    assert "pk_session" in anonymous_client.cookies
    assert "pk_csrf" in anonymous_client.cookies

    # 2. Inspect session via GET /auth/session
    inspect_res = anonymous_client.get("/api/v1/auth/session")
    assert inspect_res.status_code == 200
    assert inspect_res.json()["user_id"] == "test-browser-user"

    # 3. Perform authenticated POST echoing CSRF token from readable pk_csrf cookie
    csrf_token = anonymous_client.cookies.get("pk_csrf")
    anonymous_client.headers["X-CSRF-Token"] = csrf_token
    case_res = anonymous_client.post("/api/v1/cases", json={"title": "Browser Case", "merchant_name": "Demo"})
    assert case_res.status_code == 201

    # 4. Terminate session via DELETE /auth/session
    del_res = anonymous_client.delete("/api/v1/auth/session")
    assert del_res.status_code == 200
