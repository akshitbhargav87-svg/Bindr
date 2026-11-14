"""Cloud storage contract and API privacy, using an in-memory GCS boundary."""
import hashlib
from uuid import uuid4

import pytest
from google.api_core.exceptions import NotFound, PreconditionFailed, ServiceUnavailable

from backend.app.core.config import settings
from backend.app.services.storage import (
    GCSEvidenceStorage, StorageError, FileTooLargeError, create_storage_service,
    validate_cloud_run_settings,
)
from backend.app.api.endpoints import evidence, extractions


class MemoryBucket:
    def __init__(self):
        self.objects = {}
        self.reads = 0
        self.unavailable = False

    def bucket(self, name):
        return self

    def blob(self, key):
        return MemoryBlob(self, key)


class MemoryBlob:
    def __init__(self, bucket, key):
        self.bucket, self.key = bucket, key
        self.size = self.generation = None

    def reload(self, **kwargs):
        self.bucket.reads += 1
        if self.bucket.unavailable:
            raise ServiceUnavailable("private-bucket/provider-details")
        if self.key not in self.bucket.objects:
            raise NotFound("missing")
        self.size = len(self.bucket.objects[self.key])
        self.generation = 1

    def upload_from_string(self, data, *, if_generation_match, **kwargs):
        assert if_generation_match == 0
        if self.key in self.bucket.objects:
            raise PreconditionFailed("Original already exists")
        self.bucket.objects[self.key] = data

    def download_as_bytes(self, *, if_generation_match, **kwargs):
        assert if_generation_match == 1
        return self.bucket.objects[self.key]

    def delete(self, *, if_generation_match, **kwargs):
        assert if_generation_match == 1
        del self.bucket.objects[self.key]


@pytest.fixture
def cloud_storage(monkeypatch):
    bucket = MemoryBucket()
    storage = GCSEvidenceStorage("private-test-bucket", client=bucket)
    monkeypatch.setattr(evidence, "storage_service", storage)
    monkeypatch.setattr(extractions, "storage_service", storage)
    return storage, bucket


def upload(client):
    case = client.post("/api/v1/cases", json={"title": "Cloud evidence", "merchant_name": "Test Shop"}).json()["case"]
    original = b"We will refund INR 4999 within 5 business days."
    result = client.post(
        f"/api/v1/cases/{case['id']}/evidence", data={"expected_version": 1},
        files={"file": ("original.txt", original, "text/plain")},
    )
    assert result.status_code == 201, result.text
    return case, result.json(), original


def test_cloud_original_survives_new_storage_client_and_extraction(client, cloud_storage, monkeypatch):
    storage, bucket = cloud_storage
    case, uploaded, original = upload(client)
    ev = uploaded["evidence"]
    assert ev["sha256"] == hashlib.sha256(original).hexdigest()
    # Simulate another process reading the same private bucket, with no local files.
    replacement = GCSEvidenceStorage("private-test-bucket", client=bucket)
    monkeypatch.setattr(evidence, "storage_service", replacement)
    monkeypatch.setattr(extractions, "storage_service", replacement)
    response = client.get(ev["download_path"])
    assert response.content == original
    assert response.headers["cache-control"] == "private, no-store"
    assert response.headers["content-disposition"].startswith("attachment;")
    assert response.headers["x-content-type-options"] == "nosniff"
    result = client.post(f"/api/v1/cases/{case['id']}/extractions", json={
        "evidence_ids": [ev["id"]], "expected_version": uploaded["case_version"],
    })
    assert result.status_code == 201, result.text
    assert result.json()["extraction"]["candidates"]


def test_other_workspace_cannot_trigger_cloud_read(client, secondary_client, cloud_storage):
    _, bucket = cloud_storage
    _, uploaded, _ = upload(client)
    before = bucket.reads
    response = secondary_client.get(uploaded["evidence"]["download_path"])
    assert response.status_code == 404
    assert bucket.reads == before


def test_missing_cloud_original_and_provider_outage_are_distinct(client, cloud_storage):
    _, bucket = cloud_storage
    _, uploaded, original = upload(client)
    path = uploaded["evidence"]["download_path"]
    bucket.unavailable = True
    response = client.get(path)
    assert response.status_code == 503
    assert "private-bucket" not in response.text
    bucket.unavailable = False
    bucket.objects.clear()
    response = client.get(path)
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "FILE_NOT_FOUND"


def test_original_cannot_be_overwritten_and_oversize_rejected(cloud_storage, monkeypatch):
    storage, bucket = cloud_storage
    evidence_id = str(uuid4())
    key, _, _ = storage.save_file(b"original", evidence_id)
    with pytest.raises(StorageError):
        storage.save_file(b"replacement", evidence_id)
    assert storage.read_file(key) == b"original"
    monkeypatch.setattr(settings, "MAX_UPLOAD_SIZE_BYTES", 2)
    with pytest.raises(FileTooLargeError):
        storage.save_file(b"large", str(uuid4()))
    with pytest.raises(StorageError):
        storage.read_file(key)
    assert storage.delete_file(key)
    assert not bucket.objects


def test_failed_database_flush_removes_cloud_upload(client, db_session, cloud_storage, monkeypatch):
    _, bucket = cloud_storage
    case = client.post("/api/v1/cases", json={"title": "Rollback", "merchant_name": "Test Shop"}).json()["case"]
    def failed_flush(*args, **kwargs):
        raise RuntimeError("synthetic flush failure")
    monkeypatch.setattr(db_session, "flush", failed_flush)
    result = client.post(f"/api/v1/cases/{case['id']}/evidence", data={"expected_version": 1},
                         files={"file": ("proof.txt", b"original", "text/plain")})
    assert result.status_code == 500
    assert not bucket.objects


def test_lost_commit_acknowledgement_preserves_original(client, db_session, cloud_storage, monkeypatch):
    _, bucket = cloud_storage
    case = client.post("/api/v1/cases", json={"title": "Lost acknowledgement", "merchant_name": "Test Shop"}).json()["case"]
    original_commit = db_session.commit
    def lost_acknowledgement():
        original_commit()
        raise RuntimeError("synthetic connection loss after commit")
    monkeypatch.setattr(db_session, "commit", lost_acknowledgement)
    result = client.post(f"/api/v1/cases/{case['id']}/evidence", data={"expected_version": 1},
                         files={"file": ("proof.txt", b"original", "text/plain")})
    assert result.status_code == 500
    assert len(bucket.objects) == 1
    monkeypatch.setattr(db_session, "commit", original_commit)
    detail = client.get(f"/api/v1/cases/{case['id']}").json()
    assert len(detail["evidence"]) == 1
    assert client.get(detail["evidence"][0]["download_path"]).content == b"original"


@pytest.mark.parametrize("key", ["../outside.bin", "gs://other/object", "/etc/passwd", "x.bin"])
def test_cloud_key_rejects_paths(cloud_storage, key):
    storage, bucket = cloud_storage
    with pytest.raises(StorageError):
        storage.read_file(key)
    assert bucket.reads == 0


def test_cloud_run_rejects_ephemeral_defaults(monkeypatch):
    monkeypatch.setenv("K_SERVICE", "bindr")
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    with pytest.raises(RuntimeError, match="GCS"):
        validate_cloud_run_settings()
    monkeypatch.setattr(settings, "EVIDENCE_STORAGE_BACKEND", "gcs")
    monkeypatch.setattr(settings, "EVIDENCE_GCS_BUCKET", "private-test")
    with pytest.raises(RuntimeError, match="PostgreSQL"):
        validate_cloud_run_settings()
    monkeypatch.setattr(settings, "DATABASE_URL", "postgresql+psycopg://user:pass@/bindr?host=/cloudsql/project:region:db")
    validate_cloud_run_settings()
    monkeypatch.setattr(settings, "ENVIRONMENT", "development")
    with pytest.raises(RuntimeError, match="production"):
        validate_cloud_run_settings()


def test_storage_configuration_fails_closed(monkeypatch):
    monkeypatch.setattr(settings, "EVIDENCE_STORAGE_BACKEND", "gcs")
    monkeypatch.setattr(settings, "EVIDENCE_GCS_BUCKET", None)
    with pytest.raises(ValueError, match="EVIDENCE_GCS_BUCKET"):
        create_storage_service()
    monkeypatch.setattr(settings, "EVIDENCE_STORAGE_BACKEND", "typo")
    with pytest.raises(ValueError, match="local or gcs"):
        create_storage_service()
