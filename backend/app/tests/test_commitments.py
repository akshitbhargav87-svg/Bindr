def test_commitment_lifecycle_and_revision_preservation(client):
    # 1. Create a case
    case_res = client.post("/api/v1/cases", json={
        "title": "Refund for DEMO-42",
        "merchant_name": "Demo Shop"
    })
    case_id = case_res.json()["case"]["id"]

    # 2. Create commitment
    comm_payload = {
        "kind": "refund",
        "description": "Refund order DEMO-42",
        "amount_minor": 499900,
        "currency": "INR",
        "due_at": "2026-11-18T18:29:59Z",
        "status": "active",
        "evidence_ids": ["22222222-2222-4222-8222-222222222222"]
    }
    comm_res = client.post(f"/api/v1/cases/{case_id}/commitments", json=comm_payload)
    assert comm_res.status_code == 201
    orig_comm = comm_res.json()
    orig_id = orig_comm["id"]
    assert orig_comm["case_id"] == case_id
    assert orig_comm["status"] == "active"
    assert orig_comm["amount_minor"] == 499900

    # 3. Revise commitment
    revision_payload = {
        "description": "For order DEMO-42, the INR 4999.00 refund deadline is extended to 20 November 2026",
        "due_at": "2026-11-20T18:29:59Z",
        "evidence_ids": ["22222222-2222-4222-8222-333333333333"]
    }
    rev_res = client.post(f"/api/v1/commitments/{orig_id}/revise", json=revision_payload)
    assert rev_res.status_code == 201
    rev_comm = rev_res.json()
    rev_id = rev_comm["id"]
    assert rev_comm["supersedes_id"] == orig_id
    assert rev_comm["status"] == "active"
    assert "22222222-2222-4222-8222-222222222222" in rev_comm["evidence_ids"]
    assert "22222222-2222-4222-8222-333333333333" in rev_comm["evidence_ids"]

    # 4. Check original commitment is preserved and marked superseded
    orig_check = client.get(f"/api/v1/commitments/{orig_id}").json()
    assert orig_check["id"] == orig_id
    assert orig_check["status"] == "superseded"

    # 5. Check case detail includes both commitments
    detail = client.get(f"/api/v1/cases/{case_id}").json()
    assert len(detail["commitments"]) == 2
    ids = [c["id"] for c in detail["commitments"]]
    assert orig_id in ids
    assert rev_id in ids
