import io
import pytest
from backend.app.services.ai_adapter import (
    ai_adapter, AITimeoutError, AIServiceUnavailableError, AIInvalidOutputError
)

PNG_BYTES = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4"
TEXT_PROMISE = b"We will refund INR 4999.00 within 5 business days for order DEMO-42."


def _setup_case_with_evidence(client, text=TEXT_PROMISE):
    case_res = client.post("/api/v1/cases", json={"title": "Extraction Test", "merchant_name": "Demo Shop"})
    assert case_res.status_code == 201
    case = case_res.json()["case"]

    files = {"file": ("refund_promise.txt", io.BytesIO(text), "text/plain")}
    ev_res = client.post(f"/api/v1/cases/{case['id']}/evidence", files=files)
    assert ev_res.status_code == 201
    evidence = ev_res.json()["evidence"]
    case_version = ev_res.json()["case_version"]

    return case, evidence, case_version


def test_extraction_creates_draft_without_saving_commitments(client):
    case, evidence, version = _setup_case_with_evidence(client)

    # 1. Request AI Extraction
    payload = {
        "evidence_ids": [evidence["id"]],
        "expected_version": version
    }
    res = client.post(f"/api/v1/cases/{case['id']}/extractions", json=payload)
    assert res.status_code == 201
    data = res.json()
    assert "extraction" in data
    ext = data["extraction"]
    assert ext["case_id"] == case["id"]
    assert ext["status"] == "pending_review"
    assert len(ext["candidates"]) >= 1
    assert data["case_version"] == version + 1

    # CRITICAL INVARIANT: Verify 0 commitments have been saved to the case
    case_detail = client.get(f"/api/v1/cases/{case['id']}").json()
    assert len(case_detail["commitments"]) == 0
    assert len(case_detail["extractions"]) == 1
    assert case_detail["extractions"][0]["id"] == ext["id"]


def test_extraction_missing_evidence_id(client):
    case, _, version = _setup_case_with_evidence(client)
    payload = {
        "evidence_ids": ["00000000-0000-0000-0000-000000000000"],
        "expected_version": version
    }
    res = client.post(f"/api/v1/cases/{case['id']}/extractions", json=payload)
    assert res.status_code == 404


def test_extraction_evidence_case_mismatch(client):
    case1, ev1, v1 = _setup_case_with_evidence(client)
    case2, ev2, v2 = _setup_case_with_evidence(client)

    # Try extracting on case1 with evidence from case2
    payload = {
        "evidence_ids": [ev2["id"]],
        "expected_version": v1
    }
    res = client.post(f"/api/v1/cases/{case1['id']}/extractions", json=payload)
    assert res.status_code == 404


def test_extraction_ai_timeout_handling(client, monkeypatch):
    case, evidence, version = _setup_case_with_evidence(client)

    def mock_timeout(*args, **kwargs):
        raise AITimeoutError("AI service request timed out after 45s")

    monkeypatch.setattr(ai_adapter, "extract_commitments", mock_timeout)

    payload = {"evidence_ids": [evidence["id"]]}
    res = client.post(f"/api/v1/cases/{case['id']}/extractions", json=payload)
    assert res.status_code == 504
    assert res.json()["detail"]["error"]["code"] == "AI_TIMEOUT"


def test_extraction_ai_unavailable_handling(client, monkeypatch):
    case, evidence, version = _setup_case_with_evidence(client)

    def mock_unavailable(*args, **kwargs):
        raise AIServiceUnavailableError("Meta model API connection failed")

    monkeypatch.setattr(ai_adapter, "extract_commitments", mock_unavailable)

    payload = {"evidence_ids": [evidence["id"]]}
    res = client.post(f"/api/v1/cases/{case['id']}/extractions", json=payload)
    assert res.status_code == 503
    assert res.json()["detail"]["error"]["code"] == "AI_UNAVAILABLE"


def test_extraction_ai_invalid_output_handling(client, monkeypatch):
    case, evidence, version = _setup_case_with_evidence(client)

    def mock_invalid(*args, **kwargs):
        raise AIInvalidOutputError("Model produced non-verbatim quote")

    monkeypatch.setattr(ai_adapter, "extract_commitments", mock_invalid)

    payload = {"evidence_ids": [evidence["id"]]}
    res = client.post(f"/api/v1/cases/{case['id']}/extractions", json=payload)
    assert res.status_code == 502
    assert res.json()["detail"]["error"]["code"] == "AI_INVALID_OUTPUT"


def test_user_confirmation_and_commitment_persistence(client):
    case, evidence, version = _setup_case_with_evidence(client)

    # 1. Create extraction draft
    ext_res = client.post(f"/api/v1/cases/{case['id']}/extractions", json={
        "evidence_ids": [evidence["id"]],
        "expected_version": version
    })
    assert ext_res.status_code == 201
    ext = ext_res.json()["extraction"]
    draft_id = ext["id"]
    next_ver = ext_res.json()["case_version"]

    # 2. User confirms & approves candidate with verified terms
    review_payload = {
        "expected_version": next_ver,
        "decision": "approve",
        "items": [
            {
                "candidate_id": "c1",
                "action": "new",
                "supersedes_id": None,
                "terms": {
                    "kind": "refund",
                    "description": "Refund order DEMO-42 in full",
                    "amount_minor": 499900,
                    "currency": "INR",
                    "due_at": "2026-11-18T18:29:59Z"
                },
                "evidence_ids": [evidence["id"]]
            }
        ]
    }
    review_res = client.post(f"/api/v1/cases/{case['id']}/extractions/{draft_id}/review", json=review_payload)
    assert review_res.status_code == 200
    review_data = review_res.json()

    # Verify extraction status changed to 'reviewed'
    assert review_data["extraction"]["status"] == "reviewed"
    assert len(review_data["commitments"]) == 1
    saved_comm = review_data["commitments"][0]
    assert saved_comm["amount_minor"] == 499900
    assert saved_comm["currency"] == "INR"
    assert saved_comm["status"] == "active"
    assert evidence["id"] in saved_comm["evidence_ids"]

    # 3. Verify case now contains the persisted commitment
    case_detail = client.get(f"/api/v1/cases/{case['id']}").json()
    assert len(case_detail["commitments"]) == 1
    assert case_detail["commitments"][0]["id"] == saved_comm["id"]

    # 4. Verify timeline has documented commitment creation
    timeline_res = client.get(f"/api/v1/cases/{case['id']}/timeline").json()
    types = [e["event_type"] for e in timeline_res["timeline_events"]]
    assert "extraction_created" in types
    assert "commitment_created" in types


def test_user_rejection_closes_draft_without_saving(client):
    case, evidence, version = _setup_case_with_evidence(client)

    ext_res = client.post(f"/api/v1/cases/{case['id']}/extractions", json={"evidence_ids": [evidence["id"]]})
    draft_id = ext_res.json()["extraction"]["id"]

    # Reject draft
    review_payload = {
        "decision": "reject",
        "items": []
    }
    review_res = client.post(f"/api/v1/cases/{case['id']}/extractions/{draft_id}/review", json=review_payload)
    assert review_res.status_code == 200
    data = review_res.json()
    assert data["extraction"]["status"] == "rejected"
    assert len(data["commitments"]) == 0

    # Verify 0 commitments on case
    case_detail = client.get(f"/api/v1/cases/{case['id']}").json()
    assert len(case_detail["commitments"]) == 0


def test_repeated_review_fails_with_draft_closed(client):
    case, evidence, version = _setup_case_with_evidence(client)
    ext_res = client.post(f"/api/v1/cases/{case['id']}/extractions", json={"evidence_ids": [evidence["id"]]})
    draft_id = ext_res.json()["extraction"]["id"]

    # First review: reject
    client.post(f"/api/v1/cases/{case['id']}/extractions/{draft_id}/review", json={"decision": "reject", "items": []})

    # Second review attempt on same draft: must fail with 409 DRAFT_CLOSED
    res2 = client.post(f"/api/v1/cases/{case['id']}/extractions/{draft_id}/review", json={"decision": "reject", "items": []})
    assert res2.status_code == 409
    assert res2.json()["detail"]["error"]["code"] == "DRAFT_CLOSED"


def test_user_confirms_revision_superseding_previous(client):
    case, evidence, version = _setup_case_with_evidence(client)

    # 1. Manually add an initial active commitment
    init_comm = client.post(f"/api/v1/cases/{case['id']}/commitments", json={
        "kind": "refund",
        "description": "Original refund promise",
        "amount_minor": 499900,
        "currency": "INR",
        "due_at": "2026-11-18T18:29:59Z",
        "evidence_ids": [evidence["id"]]
    }).json()

    # 2. Extract from a new evidence
    ext_res = client.post(f"/api/v1/cases/{case['id']}/extractions", json={"evidence_ids": [evidence["id"]]})
    draft_id = ext_res.json()["extraction"]["id"]

    # 3. Confirm as revision superseding init_comm["id"]
    revision_payload = {
        "decision": "approve",
        "items": [
            {
                "candidate_id": "c1",
                "action": "revision",
                "supersedes_id": init_comm["id"],
                "terms": {
                    "kind": "refund",
                    "description": "Extended refund deadline promise",
                    "amount_minor": 499900,
                    "currency": "INR",
                    "due_at": "2026-11-25T18:29:59Z"
                },
                "evidence_ids": [evidence["id"]]
            }
        ]
    }
    rev_res = client.post(f"/api/v1/cases/{case['id']}/extractions/{draft_id}/review", json=revision_payload)
    assert rev_res.status_code == 200
    revised_comm = rev_res.json()["commitments"][0]
    assert revised_comm["supersedes_id"] == init_comm["id"]
    assert revised_comm["status"] == "active"

    # Verify original commitment is preserved with status 'superseded'
    orig_check = client.get(f"/api/v1/commitments/{init_comm['id']}").json()
    assert orig_check["status"] == "superseded"

    # Both commitments in case
    case_detail = client.get(f"/api/v1/cases/{case['id']}").json()
    assert len(case_detail["commitments"]) == 2
