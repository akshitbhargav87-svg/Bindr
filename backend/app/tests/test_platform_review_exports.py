import copy
import io
import json
import zipfile
import pytest
from backend.app.main import app
from backend.app.api.v2.reviews import get_intelligence
from backend.app.models.workflow import Proposal, Obligation
from backend.app.models.jobs import Job, Export
from backend.app.services.platform.exports import build
from backend.app.services.storage import storage_service


def post(client, path, body, key):
    return client.post("/api/v2" + path, json=body, headers={"Idempotency-Key": key})


def fixture_case(client):
    cid = post(
        client,
        "/cases",
        {"title": "Synthetic multiple refunds", "merchant_name": "Example"},
        "case",
    ).json()["case"]["id"]
    evidence = []
    for i in range(2):
        r = client.post(
            f"/api/v2/cases/{cid}/evidence",
            headers={"Idempotency-Key": f"upload-{i}"},
            files={
                "file": (
                    "source.txt",
                    f"We promise item {i} and refund INR 500.".encode(),
                    "text/plain",
                )
            },
            data={"expected_version": i + 1, "communication": "{}"},
        )
        assert r.status_code == 201, r.text
        evidence.append(r.json()["evidence"]["id"])
    return cid, evidence


class Engine:
    def __init__(self, payload):
        self.payload = payload
        self.calls = 0

    def extract_proposals_v2(self, request):
        self.calls += 1
        assert {e["evidence_id"] for e in request["evidence"]} == {
            s["evidence_id"] for c in self.payload["candidates"] for s in c["sources"]
        }
        return copy.deepcopy(self.payload)


def proposal(ids):
    return {
        "schema_version": 2,
        "proposal_id": "synthetic-proposal",
        "candidates": [
            {
                "candidate_id": f"candidate-{i}",
                "terms": {
                    "kind": "refund",
                    "description": f"Item {i}",
                    "amount_minor": 50000,
                    "currency": "INR",
                    "due_at": None,
                },
                "sources": [
                    {"evidence_id": ids[i % 2], "quote": f"We promise item {i%2}"}
                ],
                "temporal": {"parse_status": "unknown"},
                "relation": {"kind": "new"},
                "condition": {},
                "warnings": [],
            }
            for i in range(4)
        ],
        "document_warnings": [],
    }


def test_multi_review_subset_replay_and_invented_ids(client, db_session):
    cid, ids = fixture_case(client)
    engine = Engine(proposal(ids))
    app.dependency_overrides[get_intelligence] = lambda: engine
    extraction = {"expected_version": 3, "evidence_ids": ids}
    r = post(client, f"/cases/{cid}/extractions", extraction, "extract")
    assert r.status_code == 201, r.text
    assert db_session.query(Obligation).count() == 0
    assert (
        post(client, f"/cases/{cid}/extractions", extraction, "extract").json()
        == r.json()
        and engine.calls == 1
    )
    bad = {
        "expected_version": 4,
        "proposal_id": "synthetic-proposal",
        "decisions": [{"candidate_id": "invented", "action": "confirm"}],
    }
    assert post(client, f"/cases/{cid}/reviews", bad, "bad").status_code == 422
    body = {
        **bad,
        "decisions": [
            {"candidate_id": "candidate-0", "action": "confirm"},
            {"candidate_id": "candidate-2", "action": "confirm"},
        ],
    }
    a = post(client, f"/cases/{cid}/reviews", body, "review")
    assert a.status_code == 200, a.text
    assert len(a.json()["confirmed_ids"]) == 2
    assert post(client, f"/cases/{cid}/reviews", body, "review").json() == a.json()
    assert db_session.query(Obligation).count() == 2
    assert (
        post(
            client, f"/cases/{cid}/reviews", {**body, "expected_version": 5}, "another"
        ).status_code
        == 409
    )


@pytest.mark.parametrize(
    "variant",
    [
        "bad_quote",
        "negative",
        "duplicate_candidate",
        "extra",
        "missing_terms",
        "naive_due",
    ],
)
def test_malformed_ai_is_atomic(client, db_session, variant):
    cid, ids = fixture_case(client)
    data = proposal(ids)
    if variant == "bad_quote":
        data["candidates"][0]["sources"][0]["quote"] = "We promise item 1"
    if variant == "negative":
        data["candidates"][0]["terms"]["amount_minor"] = -1
    if variant == "duplicate_candidate":
        data["candidates"][1]["candidate_id"] = "candidate-0"
    if variant == "extra":
        data["candidates"][0]["invented"] = True
    if variant == "missing_terms":
        del data["candidates"][0]["terms"]
    if variant == "naive_due":
        data["candidates"][0]["terms"]["due_at"] = "2026-12-01T00:00:00"
    app.dependency_overrides[get_intelligence] = lambda: Engine(data)
    r = post(
        client,
        f"/cases/{cid}/extractions",
        {"expected_version": 3, "evidence_ids": ids},
        "extract",
    )
    assert r.status_code == 502, r.text
    assert (
        db_session.query(Proposal).count() == 0
        and db_session.query(Obligation).count() == 0
    )
    assert client.get(f"/api/v2/cases/{cid}").json()["version"] == 3


def test_duplicate_upload_preserves_original_and_case_version(client, db_session):
    cid, ids = fixture_case(client)
    original = storage_service.read_file(
        db_session.query(
            __import__("backend.app.models.evidence", fromlist=["Evidence"]).Evidence
        )
        .filter_by(id=ids[0])
        .one()
        .storage_key
    )
    r = client.post(
        f"/api/v2/cases/{cid}/evidence",
        headers={"Idempotency-Key": "same-content-new-key"},
        files={"file": ("renamed.txt", original, "text/plain")},
        data={"expected_version": 3, "communication": "{}"},
    )
    assert r.status_code == 201, r.text
    assert r.json()["duplicate_of"] == ids[0] and r.json()["case_version"] == 3


def test_private_bundle_hashes_and_original_bytes(client, secondary_client, db_session):
    cid, ids = fixture_case(client)
    r = post(
        client,
        f"/cases/{cid}/exports",
        {
            "expected_version": 3,
            "source_ids": ids,
            "reviewed_wording": "Reviewed synthetic facts",
            "formats": ["bundle"],
        },
        "export",
    )
    assert r.status_code == 202, r.text
    jid = r.json()["job"]["id"]
    eid = r.json()["export_id"]
    assert secondary_client.get("/api/v2/jobs/" + jid).status_code == 404
    assert (
        secondary_client.get("/api/v2/exports/" + eid + "?download=true").status_code
        == 404
    )
    job = db_session.get(Job, jid)
    build(db_session, job)
    db_session.commit()
    download = client.get("/api/v2/exports/" + eid + "?download=true")
    assert download.status_code == 200, download.text
    assert download.headers["cache-control"] == "private, no-store"
    import hashlib, pymupdf

    with zipfile.ZipFile(io.BytesIO(download.content)) as bundle:
        manifest = json.loads(bundle.read("manifest.json"))
        for name, digest in manifest["files"].items():
            assert hashlib.sha256(bundle.read(name)).hexdigest() == digest
        assert (
            bundle.read("originals/" + ids[0] + ".bin")
            == b"We promise item 0 and refund INR 500."
        )
        pdf = pymupdf.open(stream=bundle.read("case.pdf"), filetype="pdf")
        assert "Bindr case snapshot" in "".join(page.get_text() for page in pdf)
    resource = db_session.get(Export, eid)
    storage_service.delete_file(resource.storage_key)
    storage_service.save_file(b"altered", resource.id)
    assert client.get("/api/v2/exports/" + eid + "?download=true").status_code == 409


def test_missing_v2_engine_is_a_typed_failure_not_mock_success(client, db_session):
    cid, ids = fixture_case(client)
    r = post(
        client,
        f"/cases/{cid}/extractions",
        {"expected_version": 3, "evidence_ids": ids},
        "missing-engine",
    )
    assert (
        r.status_code == 503
        and r.json()["error"]["code"] == "INTELLIGENCE_V2_UNAVAILABLE"
    )
    assert (
        db_session.query(Proposal).count() == 0
        and db_session.query(Obligation).count() == 0
    )
    job = db_session.get(Job, r.json()["error"]["request_id"])
    assert job.state == "failed" and job.stage == "configuration"


def test_selected_export_omits_other_facts_and_qr_has_no_case_access(
    client, db_session, monkeypatch, tmp_path
):
    cid, ids = fixture_case(client)
    selected = []
    for index, (description, amount) in enumerate(
        [("Selected synthetic refund", 50000), ("PRIVATE_OTHER_FACT", 999999)]
    ):
        response = post(
            client,
            f"/cases/{cid}/manual-promises",
            {
                "expected_version": 3 + index,
                "origin": "user_attested",
                "confirmed": True,
                "terms": {
                    "kind": "refund",
                    "description": description,
                    "amount_minor": amount,
                    "currency": "INR",
                    "due_at": None,
                },
            },
            "manual-" + str(index),
        )
        assert response.status_code == 201, response.text
        selected.append(response.json()["obligation_id"])
    monkeypatch.setenv(
        "BINDR_VERIFIER_URL", "https://example.test/api/v2/verification-info"
    )
    response = post(
        client,
        f"/cases/{cid}/exports",
        {
            "expected_version": 5,
            "source_ids": [ids[0]],
            "obligation_ids": [selected[0]],
            "include_history": False,
            "reviewed_wording": "Reviewed synthetic export",
            "formats": ["bundle"],
        },
        "selected-export",
    )
    assert response.status_code == 202, response.text
    build(db_session, db_session.get(Job, response.json()["job"]["id"]))
    db_session.commit()
    downloaded = client.get(
        "/api/v2/exports/" + response.json()["export_id"] + "?download=true"
    )
    import pymupdf, cv2, numpy as np

    with zipfile.ZipFile(io.BytesIO(downloaded.content)) as archive:
        record = json.loads(archive.read("record.json"))
        assert len(record["obligations"]) == 1 and record["events"] == []
        assert "PRIVATE_OTHER_FACT" not in archive.read("record.json").decode()
        assert (
            record["projection"]["money_by_currency"]["INR"]["promised_minor"] == 50000
        )
        pdf = archive.read("case.pdf")
        with pymupdf.open(stream=pdf, filetype="pdf") as document:
            text = "".join(p.get_text() for p in document)
            assert "PRIVATE_OTHER_FACT" not in text and "Page 1 of" in text
            decoded = []
            for page in document:
                for image in page.get_images():
                    content = document.extract_image(image[0])["image"]
                    value, _, _ = cv2.QRCodeDetector().detectAndDecode(
                        cv2.imdecode(
                            np.frombuffer(content, dtype=np.uint8), cv2.IMREAD_COLOR
                        )
                    )
                    if value:
                        decoded.append(value)
            assert decoded == ["https://example.test/api/v2/verification-info"]
    assert client.get("/api/v2/verification-info").json()["case_access"] is False
