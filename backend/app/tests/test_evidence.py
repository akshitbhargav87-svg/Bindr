import io
import hashlib
from backend.app.core.config import settings

# Sample valid binary headers
PNG_BYTES = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4"
JPEG_BYTES = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00\xff\xdb\x00C\x00"
PDF_BYTES = b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n>>\nendobj\ntrailer\n<<\n>>\n%%EOF"
TEXT_BYTES = b"We promise to refund INR 4999.00 within 5 business days."


def _create_case(client):
    res = client.post("/api/v1/cases", json={"title": "Test Case", "merchant_name": "Test Merchant"})
    assert res.status_code == 201
    return res.json()["case"]


def test_upload_valid_png(client):
    case = _create_case(client)
    files = {"file": ("screenshot.png", io.BytesIO(PNG_BYTES), "image/png")}
    data = {"expected_version": 1}

    res = client.post(f"/api/v1/cases/{case['id']}/evidence", files=files, data=data)
    assert res.status_code == 201
    payload = res.json()
    assert "evidence" in payload
    ev = payload["evidence"]
    assert ev["media_type"] == "image/png"
    assert ev["filename"] == "screenshot.png"
    assert ev["size_bytes"] == len(PNG_BYTES)
    assert ev["sha256"] == hashlib.sha256(PNG_BYTES).hexdigest()
    assert ev["case_id"] == case["id"]
    assert payload["case_version"] == 2


def test_upload_valid_jpeg(client):
    case = _create_case(client)
    files = {"file": ("receipt.jpg", io.BytesIO(JPEG_BYTES), "image/jpeg")}

    res = client.post(f"/api/v1/cases/{case['id']}/evidence", files=files)
    assert res.status_code == 201
    ev = res.json()["evidence"]
    assert ev["media_type"] == "image/jpeg"
    assert ev["filename"] == "receipt.jpg"


def test_upload_valid_pdf(client):
    case = _create_case(client)
    files = {"file": ("contract.pdf", io.BytesIO(PDF_BYTES), "application/pdf")}

    res = client.post(f"/api/v1/cases/{case['id']}/evidence", files=files)
    assert res.status_code == 201
    ev = res.json()["evidence"]
    assert ev["media_type"] == "application/pdf"
    assert ev["filename"] == "contract.pdf"


def test_upload_valid_text(client):
    case = _create_case(client)
    files = {"file": ("chat_log.txt", io.BytesIO(TEXT_BYTES), "text/plain")}

    res = client.post(f"/api/v1/cases/{case['id']}/evidence", files=files)
    assert res.status_code == 201
    ev = res.json()["evidence"]
    assert ev["media_type"] == "text/plain"


def test_upload_unsupported_format(client):
    case = _create_case(client)
    # Executable magic bytes 'MZ'
    bad_bytes = b"MZ\x90\x00\x03\x00\x00\x00\x04\x00\x00\x00\xff\xff\x00\x00"
    files = {"file": ("app.exe", io.BytesIO(bad_bytes), "application/octet-stream")}

    res = client.post(f"/api/v1/cases/{case['id']}/evidence", files=files)
    assert res.status_code == 415


def test_upload_disguised_file(client):
    case = _create_case(client)
    # Disguised as .png but binary data is arbitrary/unsupported
    fake_png = b"NOT_A_PNG_HEADER_RANDOM_GARBAGE\x00\x01\x02"
    files = {"file": ("fake.png", io.BytesIO(fake_png), "image/png")}

    res = client.post(f"/api/v1/cases/{case['id']}/evidence", files=files)
    assert res.status_code == 415


def test_upload_zero_bytes(client):
    case = _create_case(client)
    files = {"file": ("empty.png", io.BytesIO(b""), "image/png")}

    res = client.post(f"/api/v1/cases/{case['id']}/evidence", files=files)
    assert res.status_code == 422


def test_upload_oversized_file(client, monkeypatch):
    case = _create_case(client)
    # Patch MAX_UPLOAD_SIZE_BYTES to 100 bytes for fast testing
    monkeypatch.setattr(settings, "MAX_UPLOAD_SIZE_BYTES", 100)
    oversized = PNG_BYTES + (b"X" * 150)
    files = {"file": ("large.png", io.BytesIO(oversized), "image/png")}

    res = client.post(f"/api/v1/cases/{case['id']}/evidence", files=files)
    assert res.status_code == 413


def test_upload_invalid_case_id(client):
    files = {"file": ("doc.pdf", io.BytesIO(PDF_BYTES), "application/pdf")}
    res = client.post("/api/v1/cases/00000000-0000-0000-0000-000000000000/evidence", files=files)
    assert res.status_code == 404


def test_upload_version_conflict(client):
    case = _create_case(client)
    files = {"file": ("test.png", io.BytesIO(PNG_BYTES), "image/png")}
    # Case current version is 1; sending expected_version = 99
    data = {"expected_version": 99}

    res = client.post(f"/api/v1/cases/{case['id']}/evidence", files=files, data=data)
    assert res.status_code == 409


def test_filename_path_traversal_sanitized(client):
    case = _create_case(client)
    malicious_filename = "../../../etc/passwd.png"
    files = {"file": (malicious_filename, io.BytesIO(PNG_BYTES), "image/png")}

    res = client.post(f"/api/v1/cases/{case['id']}/evidence", files=files)
    assert res.status_code == 201
    ev = res.json()["evidence"]
    assert ".." not in ev["filename"]
    assert "/" not in ev["filename"]
    assert "\\" not in ev["filename"]
    assert ev["filename"] == "passwd.png"


def test_evidence_retrieval_and_content_streaming(client):
    case = _create_case(client)
    files = {"file": ("evidence_report.pdf", io.BytesIO(PDF_BYTES), "application/pdf")}
    upload_res = client.post(f"/api/v1/cases/{case['id']}/evidence", files=files)
    assert upload_res.status_code == 201
    ev_id = upload_res.json()["evidence"]["id"]

    # 1. List evidence for case
    list_res = client.get(f"/api/v1/cases/{case['id']}/evidence")
    assert list_res.status_code == 200
    evidence_list = list_res.json()["evidence"]
    assert len(evidence_list) == 1
    assert evidence_list[0]["id"] == ev_id

    # 2. Get single metadata
    get_res = client.get(f"/api/v1/cases/{case['id']}/evidence/{ev_id}")
    assert get_res.status_code == 200
    assert get_res.json()["filename"] == "evidence_report.pdf"

    # 3. Stream raw content
    content_res = client.get(f"/api/v1/cases/{case['id']}/evidence/{ev_id}/content")
    assert content_res.status_code == 200
    assert content_res.content == PDF_BYTES
    assert content_res.headers["Content-Type"] == "application/pdf"
    assert content_res.headers["Cache-Control"] == "private, no-store"
    assert content_res.headers["X-Content-Type-Options"] == "nosniff"
    assert "attachment" in content_res.headers["Content-Disposition"]
