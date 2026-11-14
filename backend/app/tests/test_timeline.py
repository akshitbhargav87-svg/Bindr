import io

PNG_BYTES = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4"


def test_timeline_lifecycle(client):
    # 1. Create Case
    case_res = client.post("/api/v1/cases", json={
        "title": "Timeline Test Case",
        "merchant_name": "Acme Retail"
    })
    assert case_res.status_code == 201
    case_id = case_res.json()["case"]["id"]

    # 2. Upload Evidence
    files = {"file": ("proof.png", io.BytesIO(PNG_BYTES), "image/png")}
    ev_res = client.post(f"/api/v1/cases/{case_id}/evidence", files=files, data={"expected_version": 1})
    assert ev_res.status_code == 201

    # 3. Create Commitment
    comm_payload = {
        "kind": "refund",
        "description": "Refund of order 123",
        "amount_minor": 10000,
        "currency": "INR",
        "due_at": "2026-11-20T10:00:00Z",
        "status": "active"
    }
    comm_res = client.post(f"/api/v1/cases/{case_id}/commitments", json=comm_payload)
    assert comm_res.status_code == 201
    comm_id = comm_res.json()["id"]

    # 4. Revise Commitment
    rev_payload = {
        "description": "Refund delayed to 25th",
        "due_at": "2026-11-25T10:00:00Z"
    }
    rev_res = client.post(f"/api/v1/commitments/{comm_id}/revise", json=rev_payload)
    assert rev_res.status_code == 201

    # 5. Fetch Timeline
    timeline_res = client.get(f"/api/v1/cases/{case_id}/timeline")
    assert timeline_res.status_code == 200
    events = timeline_res.json()["timeline_events"]
    assert len(events) >= 4

    types = [e["event_type"] for e in events]
    assert "case_created" in types
    assert "evidence_uploaded" in types
    assert "commitment_created" in types
    assert "commitment_revised" in types


def test_timeline_invalid_case(client):
    res = client.get("/api/v1/cases/00000000-0000-0000-0000-000000000000/timeline")
    assert res.status_code == 404
