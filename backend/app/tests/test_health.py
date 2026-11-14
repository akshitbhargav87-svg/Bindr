def test_health_endpoint(client):
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.json()["status"] == "healthy"

    res_v1 = client.get("/api/v1/health")
    assert res_v1.status_code == 200
    assert res_v1.json()["status"] == "healthy"


def test_root_endpoint(client):
    res = client.get("/")
    assert res.status_code == 200
    assert "Welcome" in res.json()["message"]
