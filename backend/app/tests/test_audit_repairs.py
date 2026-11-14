import io
import pytest
from PIL import Image, ImageDraw
from backend.app.core.config import settings
from backend.app.core.auth import create_authenticated_session
from backend.app.services.ai_adapter import ai_adapter, AIInvalidOutputError


def _create_case(client):
    res = client.post("/api/v1/cases", json={"title": "Audit Case", "merchant_name": "Flipkart"})
    assert res.status_code == 201
    return res.json()["case"]


def _generate_synthetic_screenshot(text: str) -> bytes:
    """Generate a clean synthetic PNG image with rendered text for real RapidOCR recognition."""
    img = Image.new("RGB", (600, 150), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    draw.text((20, 50), text, fill=(0, 0, 0))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def test_ai_function_signature_compatibility():
    """Verify Kunal's extract_commitment_from_evidence signature accepts file_source, filename, evidence_id, metadata."""
    from backend.app.ai import extract_commitment_from_evidence, SourceMetadata

    text = "We will refund INR 500 within 5 business days."
    res = extract_commitment_from_evidence(
        file_source=text.encode("utf-8"),
        filename="refund_note.txt",
        evidence_id="ev_sig_test_1",
        metadata=SourceMetadata(sender="Test Store"),
        fallback_on_error=False,
        timeout=30
    )
    assert res is not None
    assert res.evidence_metadata.evidence_id == "ev_sig_test_1"
    assert res.evidence_metadata.filename == "refund_note.txt"


def test_http_screenshot_upload_rapidocr_mock_ai_end_to_end(client):
    """
    Automated regression:
    HTTP upload of real PNG screenshot -> RapidOCR text recognition -> mock AI provider -> draft -> approval -> saved commitment.
    Does NOT substitute mock OCR.
    """
    settings.AI_PROVIDER = "mock"
    case = _create_case(client)

    # 1. Create a real screenshot with promise text
    screenshot_bytes = _generate_synthetic_screenshot("Refund of INR 1499 will be credited within 3 business days")

    # 2. Upload screenshot via HTTP multipart
    files = {"file": ("chat_screenshot.png", io.BytesIO(screenshot_bytes), "image/png")}
    data = {"expected_version": "1"}
    upload_res = client.post(f"/api/v1/cases/{case['id']}/evidence", files=files, data=data)
    assert upload_res.status_code == 201
    ev_data = upload_res.json()["evidence"]
    assert ev_data["media_type"] == "image/png"

    # 3. Create extraction draft (invoking real RapidOCR in Kunal's pipeline)
    ext_res = client.post(
        f"/api/v1/cases/{case['id']}/extractions",
        json={"evidence_ids": [ev_data["id"]], "expected_version": 2}
    )
    assert ext_res.status_code == 201
    draft = ext_res.json()["extraction"]
    assert draft["status"] == "pending_review"
    assert len(draft["candidates"]) > 0

    cand = draft["candidates"][0]
    assert cand["terms"]["kind"] == "refund"
    assert len(cand["sources"]) > 0
    assert cand["sources"][0]["evidence_id"] == ev_data["id"]

    # 4. Confirm/Review the draft
    review_res = client.post(
        f"/api/v1/cases/{case['id']}/extractions/{draft['id']}/review",
        json={
            "expected_version": 3,
            "decision": "approve",
            "items": [
                {
                    "candidate_id": cand["candidate_id"],
                    "action": "new",
                    "supersedes_id": None,
                    "terms": {
                        "kind": "refund",
                        "description": "Reviewed: Refund of INR 1499 within 3 business days",
                        "amount_minor": 149900,
                        "currency": "INR",
                        "due_at": "2026-11-20T18:30:00Z"
                    },
                    "evidence_ids": [ev_data["id"]]
                }
            ]
        }
    )
    assert review_res.status_code == 200
    review_data = review_res.json()
    assert review_data["extraction"]["status"] == "reviewed"
    assert len(review_data["commitments"]) == 1
    comm = review_data["commitments"][0]
    assert comm["amount_minor"] == 149900
    assert comm["currency"] == "INR"
    assert comm["status"] == "active"


def test_duplicate_evidence_ids_rejected(client):
    """Reject duplicate evidence IDs in extraction request up-front with 422."""
    case = _create_case(client)
    ev_bytes = b"Refund of INR 500 within 5 business days."
    files = {"file": ("note.txt", io.BytesIO(ev_bytes), "text/plain")}
    up_res = client.post(f"/api/v1/cases/{case['id']}/evidence", files=files, data={"expected_version": "1"})
    ev_id = up_res.json()["evidence"]["id"]

    # Pass duplicate evidence IDs
    ext_res = client.post(f"/api/v1/cases/{case['id']}/extractions", json={"evidence_ids": [ev_id, ev_id]})
    assert ext_res.status_code == 422
    err = ext_res.json()["error"]
    assert err["code"] == "VALIDATION_ERROR"


def test_unsupported_ai_schema_version_rejected(client, monkeypatch):
    """Unsupported AI schema versions must be rejected with 502 AI_INVALID_OUTPUT."""
    case = _create_case(client)
    ev_bytes = b"Refund of INR 500 within 5 business days."
    files = {"file": ("note.txt", io.BytesIO(ev_bytes), "text/plain")}
    up_res = client.post(f"/api/v1/cases/{case['id']}/evidence", files=files, data={"expected_version": "1"})
    ev_id = up_res.json()["evidence"]["id"]

    def mock_invalid_schema(*args, **kwargs):
        return {"schema_version": 99, "candidates": []}

    monkeypatch.setattr(ai_adapter, "extract_commitments", mock_invalid_schema)

    ext_res = client.post(f"/api/v1/cases/{case['id']}/extractions", json={"evidence_ids": [ev_id]})
    assert ext_res.status_code == 502
    assert ext_res.json()["error"]["code"] == "AI_INVALID_OUTPUT"


def test_forged_session_token_rejected(anonymous_client):
    """Arbitrary or forged session tokens must be rejected with 401 UNAUTHENTICATED."""
    anonymous_client.cookies.set("pk_session", "forged_session_token_without_signature")
    res = anonymous_client.get("/api/v1/cases")
    assert res.status_code == 401
    assert res.json()["error"]["code"] == "UNAUTHENTICATED"


def test_missing_csrf_on_cookie_mutation_rejected(anonymous_client):
    """Mutating request with cookie auth but missing CSRF token returns 403 CSRF_FAILED."""
    token, _ = create_authenticated_session("test-user")
    anonymous_client.cookies.set("pk_session", token)
    # No X-CSRF-Token header provided
    res = anonymous_client.post("/api/v1/cases", json={"title": "Test", "merchant_name": "Demo"})
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "CSRF_FAILED"


def test_bearer_token_authentication_succeeds_without_csrf(anonymous_client):
    """API clients authenticating with Bearer header do not require CSRF header."""
    token, _ = create_authenticated_session("bearer-user")
    headers = {"Authorization": f"Bearer {token}"}
    res = anonymous_client.post(
        "/api/v1/cases",
        json={"title": "Bearer Case", "merchant_name": "Shop"},
        headers=headers
    )
    assert res.status_code == 201
    assert res.json()["case"]["title"] == "Bearer Case"


def test_cross_user_case_access_rejected_with_404(client, secondary_client):
    """User B cannot view or mutate User A's cases; returns 404 NOT_FOUND."""
    # User A creates a case and uploads evidence
    case_a = _create_case(client)
    files = {"file": ("note.txt", io.BytesIO(b"Secret data"), "text/plain")}
    up_res = client.post(f"/api/v1/cases/{case_a['id']}/evidence", files=files, data={"expected_version": "1"})
    ev_id = up_res.json()["evidence"]["id"]

    # User B attempts to access User A's case
    res_get = secondary_client.get(f"/api/v1/cases/{case_a['id']}")
    assert res_get.status_code == 404
    assert res_get.json()["error"]["code"] == "NOT_FOUND"

    # User B attempts to list evidence of User A's case
    res_ev_list = secondary_client.get(f"/api/v1/cases/{case_a['id']}/evidence")
    assert res_ev_list.status_code == 404

    # User B attempts to stream evidence content of User A's file
    res_ev_content = secondary_client.get(f"/api/v1/cases/{case_a['id']}/evidence/{ev_id}/content")
    assert res_ev_content.status_code == 404

    # User B attempts to trigger extraction on User A's case
    res_ext = secondary_client.post(f"/api/v1/cases/{case_a['id']}/extractions", json={"evidence_ids": [ev_id]})
    assert res_ext.status_code == 404

    # User B lists cases: User A's case is not present
    list_res = secondary_client.get("/api/v1/cases")
    assert list_res.status_code == 200
    listed_ids = [c["id"] for c in list_res.json()["cases"]]
    assert case_a["id"] not in listed_ids
