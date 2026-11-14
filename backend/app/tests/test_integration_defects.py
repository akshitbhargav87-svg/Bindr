import io
import pytest
from backend.app.core.config import settings
from backend.app.services.ai_adapter import (
    AIModuleAdapter,
    AIInvalidOutputError,
    AIServiceUnavailableError,
)


def _create_case(client):
    res = client.post("/api/v1/cases", json={"title": "Test Case", "merchant_name": "Test Merchant"})
    assert res.status_code == 201
    return res.json()["case"]


def _upload_text_evidence(client, case_id, content: str, filename: str = "note.txt", expected_version=1):
    file_bytes = content.encode("utf-8")
    files = {"file": (filename, io.BytesIO(file_bytes), "text/plain")}
    data = {"expected_version": str(expected_version)}
    res = client.post(f"/api/v1/cases/{case_id}/evidence", files=files, data=data)
    assert res.status_code == 201
    return res.json()["evidence"], res.json()["case_version"]


def test_anonymous_evidence_access_rejected(anonymous_client, client):
    """Anonymous access to evidence content must return 401 UNAUTHENTICATED."""
    case = _create_case(client)
    evidence, version = _upload_text_evidence(client, case["id"], "Secret customer data")

    # Access via anonymous client (no pk_session cookie or auth token)
    res = anonymous_client.get(f"/api/v1/cases/{case['id']}/evidence/{evidence['id']}/content")
    assert res.status_code == 401
    body = res.json()
    assert "error" in body
    assert body["error"]["code"] == "UNAUTHENTICATED"
    assert "request_id" in body["error"]


def test_anonymous_upload_rejected(anonymous_client, client):
    """Anonymous file upload must return 401 UNAUTHENTICATED."""
    case = _create_case(client)
    files = {"file": ("unauth.txt", io.BytesIO(b"Data"), "text/plain")}
    res = anonymous_client.post(f"/api/v1/cases/{case['id']}/evidence", files=files, data={"expected_version": 1})
    assert res.status_code == 401
    assert res.json()["error"]["code"] == "UNAUTHENTICATED"


def test_error_response_conforms_to_canonical_envelope(client):
    """All error responses must match {"error": {"code", "message", "details", "request_id"}}."""
    # 404 NOT_FOUND
    res_404 = client.get("/api/v1/cases/00000000-0000-0000-0000-000000000000")
    assert res_404.status_code == 404
    err_404 = res_404.json()["error"]
    assert err_404["code"] == "NOT_FOUND"
    assert isinstance(err_404["details"], list)
    assert "request_id" in err_404

    # 422 VALIDATION_ERROR (Pydantic validation)
    res_422 = client.post("/api/v1/cases", json={"title": ""})
    assert res_422.status_code == 422
    err_422 = res_422.json()["error"]
    assert err_422["code"] == "VALIDATION_ERROR"
    assert len(err_422["details"]) > 0
    assert "request_id" in err_422


def test_quotation_attributed_to_wrong_file_is_rejected():
    """Validating source quotations against specific files; cannot cite file A for a quote only in file B."""
    adapter = AIModuleAdapter()

    evidence_a = {"evidence_id": "ev-A", "text": "File A: Your package has been dispatched via BlueDart."}
    evidence_b = {"evidence_id": "ev-B", "text": "File B: We will issue a full refund of INR 2500 within 48 hours."}

    # Simulate model producing a quote from File B but attributing it to File A
    malformed_candidates = [
        {
            "candidate_id": "c1",
            "terms": {"kind": "refund", "description": "Refund promise", "amount_minor": 250000, "currency": "INR", "due_at": None},
            "sources": [{"evidence_id": "ev-A", "quote": "We will issue a full refund of INR 2500 within 48 hours."}],
            "confidence": 0.95,
            "warnings": [],
            "revision": {"relation": "new", "supersedes_id": None, "reason": "New"}
        }
    ]

    with pytest.raises(AIInvalidOutputError) as exc_info:
        adapter._validate_and_sanitize_candidates(malformed_candidates, [evidence_a, evidence_b])

    assert "not a verbatim substring" in str(exc_info.value)
    assert "ev-A" not in str(exc_info.value)  # Public provider errors omit evidence identifiers.


def test_quotation_validated_per_individual_evidence_not_concatenated():
    """Source quotation is validated and linked to the specific individual evidence record."""
    adapter = AIModuleAdapter()
    adapter._engine = None

    settings.AI_PROVIDER = "mock"
    settings.MODEL_API_KEY = None

    ev1 = {"evidence_id": "ev-1", "text": "We will refund INR 500 within 3 days for order 1."}
    ev2 = {"evidence_id": "ev-2", "text": "Replacement item dispatched for order 2."}

    output = adapter.extract_commitments(
        case_id="11111111-1111-4111-8111-111111111111",
        evidence=[ev1, ev2]
    )

    assert "candidates" in output
    for cand in output["candidates"]:
        for src in cand["sources"]:
            cited_id = src["evidence_id"]
            quote = src["quote"]
            if cited_id == "ev-1":
                assert quote in ev1["text"]
            elif cited_id == "ev-2":
                assert quote in ev2["text"]


def test_review_rejects_invented_candidate_id(client):
    """Submitting an invented candidate ID during review returns 422 VALIDATION_ERROR."""
    case = _create_case(client)
    evidence, version = _upload_text_evidence(client, case["id"], "We will refund INR 1500 within 5 business days for order 123.", expected_version=1)

    # Create extraction draft
    ext_res = client.post(f"/api/v1/cases/{case['id']}/extractions", json={"expected_version": version, "evidence_ids": [evidence["id"]]})
    assert ext_res.status_code == 201
    draft = ext_res.json()["extraction"]
    assert len(draft["candidates"]) > 0

    # Attempt to review with an invented candidate ID 'c999'
    review_payload = {
        "expected_version": ext_res.json()["case_version"],
        "decision": "approve",
        "items": [
            {
                "candidate_id": "c999",  # Invented
                "action": "new",
                "supersedes_id": None,
                "terms": {
                    "kind": "refund",
                    "description": "Invented refund",
                    "amount_minor": 150000,
                    "currency": "INR",
                    "due_at": None
                },
                "evidence_ids": [evidence["id"]]
            }
        ]
    }

    rev_res = client.post(f"/api/v1/cases/{case['id']}/extractions/{draft['id']}/review", json=review_payload)
    assert rev_res.status_code == 422
    err = rev_res.json()["error"]
    assert err["code"] == "VALIDATION_ERROR"
    assert any("c999" in str(d) for d in err["details"] or [err["message"]])


def test_review_rejects_negative_amounts(client):
    """Negative amount_minor must be rejected with 422 VALIDATION_ERROR."""
    case = _create_case(client)
    evidence, version = _upload_text_evidence(client, case["id"], "We will refund INR 1000 within 5 business days.")
    ext_res = client.post(f"/api/v1/cases/{case['id']}/extractions", json={"expected_version": version, "evidence_ids": [evidence["id"]]})
    draft = ext_res.json()["extraction"]
    assert len(draft["candidates"]) > 0
    candidate_id = draft["candidates"][0]["candidate_id"]

    review_payload = {
        "expected_version": ext_res.json()["case_version"],
        "decision": "approve",
        "items": [
            {
                "candidate_id": candidate_id,
                "action": "new",
                "supersedes_id": None,
                "terms": {
                    "kind": "refund",
                    "description": "Refund with negative amount",
                    "amount_minor": -50000,  # Negative
                    "currency": "INR",
                    "due_at": None
                },
                "evidence_ids": [evidence["id"]]
            }
        ]
    }

    res = client.post(f"/api/v1/cases/{case['id']}/extractions/{draft['id']}/review", json=review_payload)
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "VALIDATION_ERROR"


def test_review_rejects_missing_refund_amount(client):
    """Reviewed refund requires a populated amount and currency pair."""
    case = _create_case(client)
    evidence, version = _upload_text_evidence(client, case["id"], "We will refund INR 1000 within 5 business days.")
    ext_res = client.post(f"/api/v1/cases/{case['id']}/extractions", json={"expected_version": version, "evidence_ids": [evidence["id"]]})
    draft = ext_res.json()["extraction"]
    assert len(draft["candidates"]) > 0
    candidate_id = draft["candidates"][0]["candidate_id"]

    review_payload = {
        "expected_version": ext_res.json()["case_version"],
        "decision": "approve",
        "items": [
            {
                "candidate_id": candidate_id,
                "action": "new",
                "supersedes_id": None,
                "terms": {
                    "kind": "refund",
                    "description": "Zero refund",
                    "amount_minor": None,  # Refund must have a populated amount
                    "currency": "INR",
                    "due_at": None
                },
                "evidence_ids": [evidence["id"]]
            }
        ]
    }

    res = client.post(f"/api/v1/cases/{case['id']}/extractions/{draft['id']}/review", json=review_payload)
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "VALIDATION_ERROR"


def test_review_rejects_duplicate_candidate_in_items(client):
    """Review payload containing duplicate candidate IDs must be rejected."""
    case = _create_case(client)
    evidence, version = _upload_text_evidence(client, case["id"], "We will refund INR 1000 within 5 business days.")
    ext_res = client.post(f"/api/v1/cases/{case['id']}/extractions", json={"expected_version": version, "evidence_ids": [evidence["id"]]})
    draft = ext_res.json()["extraction"]
    assert len(draft["candidates"]) > 0
    candidate_id = draft["candidates"][0]["candidate_id"]

    item = {
        "candidate_id": candidate_id,
        "action": "new",
        "supersedes_id": None,
        "terms": {
            "kind": "refund",
            "description": "Refund promise",
            "amount_minor": 100000,
            "currency": "INR",
            "due_at": None
        },
        "evidence_ids": [evidence["id"]]
    }

    review_payload = {
        "expected_version": ext_res.json()["case_version"],
        "decision": "approve",
        "items": [item, item]  # Duplicate item with same candidate_id
    }

    res = client.post(f"/api/v1/cases/{case['id']}/extractions/{draft['id']}/review", json=review_payload)
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "VALIDATION_ERROR"


def test_no_silent_mock_fallback_when_meta_provider_unconfigured(client):
    """When AI_PROVIDER=meta, missing MODEL_API_KEY must return 503 AI_UNAVAILABLE, never silent mock."""
    case = _create_case(client)
    evidence, version = _upload_text_evidence(client, case["id"], "We will refund INR 500.")

    settings.AI_PROVIDER = "meta"
    settings.MODEL_API_KEY = None

    res = client.post(f"/api/v1/cases/{case['id']}/extractions", json={"expected_version": version, "evidence_ids": [evidence["id"]]})
    assert res.status_code == 503
    assert res.json()["error"]["code"] == "AI_UNAVAILABLE"


def test_end_to_end_upload_ai_review_workflow(client):
    """Full HTTP upload -> AI extraction -> review approval -> commitment persistence workflow."""
    # 1. Create Case
    case = _create_case(client)
    assert case["version"] == 1

    # 2. Upload Evidence
    text_content = "We will refund INR 3499.00 for your order within 5 days."
    evidence, v2 = _upload_text_evidence(client, case["id"], text_content, filename="receipt.txt", expected_version=1)
    assert v2 == 2

    # 3. Request Extraction
    ext_res = client.post(f"/api/v1/cases/{case['id']}/extractions", json={"evidence_ids": [evidence["id"]], "expected_version": 2})
    assert ext_res.status_code == 201
    draft = ext_res.json()["extraction"]
    assert draft["status"] == "pending_review"
    assert len(draft["candidates"]) == 1
    cand = draft["candidates"][0]

    # Verify no commitments created yet
    case_detail = client.get(f"/api/v1/cases/{case['id']}").json()
    assert len(case_detail["commitments"]) == 0

    # 4. User confirms draft candidate
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
                        "description": "Reviewed: Refund INR 3499.00 within 5 days",
                        "amount_minor": 349900,
                        "currency": "INR",
                        "due_at": "2026-11-20T18:00:00Z"
                    },
                    "evidence_ids": [evidence["id"]]
                }
            ]
        }
    )
    assert review_res.status_code == 200
    review_data = review_res.json()
    assert review_data["extraction"]["status"] == "reviewed"
    assert len(review_data["commitments"]) == 1
    comm = review_data["commitments"][0]
    assert comm["kind"] == "refund"
    assert comm["amount_minor"] == 349900
    assert comm["currency"] == "INR"
    assert comm["status"] == "active"
    assert comm["evidence_ids"] == [evidence["id"]]

    # Verify atomic persistence in case detail
    final_case = client.get(f"/api/v1/cases/{case['id']}").json()
    assert len(final_case["commitments"]) == 1
    assert final_case["commitments"][0]["id"] == comm["id"]
    assert final_case["case"]["version"] == 4
