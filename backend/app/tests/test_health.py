def test_health_endpoint(client):
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.json()["status"] == "healthy"

    res_v1 = client.get("/api/v1/health")
    assert res_v1.status_code == 200
    assert res_v1.json()["status"] == "healthy"


def test_root_endpoint(client):
    res = client.get("/")
    from pathlib import Path
    from backend.app.main import frontend_dir
    if Path(frontend_dir, "index.html").is_file():
        assert res.status_code == 200
        assert "text/html" in res.headers["content-type"]
        assert '<div id="root">' in res.text
    else:
        assert res.status_code == 503
    ready = client.get("/healthz")
    assert ready.status_code == 200
