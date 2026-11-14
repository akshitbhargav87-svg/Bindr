def test_create_and_get_case(client):
    payload = {
        "title": "Refund for DEMO-42",
        "merchant_name": "Demo Shop"
    }
    # Test POST /api/v1/cases
    res = client.post("/api/v1/cases", json=payload)
    assert res.status_code == 201
    data = res.json()["case"]
    case_id = data["id"]
    assert data["title"] == payload["title"]
    assert data["merchant_name"] == payload["merchant_name"]
    assert data["status"] == "open"
    assert data["version"] == 1

    # Test GET /api/v1/cases
    list_res = client.get("/api/v1/cases")
    assert list_res.status_code == 200
    cases = list_res.json()["cases"]
    assert len(cases) >= 1
    assert any(c["id"] == case_id for c in cases)

    # Test GET /api/v1/cases/{case_id}
    detail_res = client.get(f"/api/v1/cases/{case_id}")
    assert detail_res.status_code == 200
    detail = detail_res.json()
    assert detail["case"]["id"] == case_id
    assert "evidence" in detail
    assert "commitments" in detail


def test_get_case_not_found(client):
    res = client.get("/api/v1/cases/00000000-0000-0000-0000-000000000000")
    assert res.status_code == 404
