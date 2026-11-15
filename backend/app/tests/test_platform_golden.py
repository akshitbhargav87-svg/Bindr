"""Desired platform behavior against authored seam fixtures, not real model semantic verdicts."""

import copy
import time
import pytest
from backend.app.main import app
from backend.app.api.v2.reviews import get_intelligence
from backend.app.models.workflow import Proposal, Obligation

TEXT = """Airtel Support synthetic fixture:
1. Your ₹799 recharge refund will be completed by November 17, 2026.
2. Your broadband connection will be restored by November 16, 2026.
3. A ₹200 goodwill credit will be added to your account by November 19, 2026.
4. Our technician will visit your home on November 15, 2026.
"""


def post(client, path, body, key):
    return client.post("/api/v2" + path, json=body, headers={"Idempotency-Key": key})


def setup(client):
    cid = post(
        client,
        "/cases",
        {"title": "Synthetic Airtel four promises", "merchant_name": "Airtel"},
        "case",
    ).json()["case"]["id"]
    r = client.post(
        f"/api/v2/cases/{cid}/evidence",
        headers={"Idempotency-Key": "upload"},
        files={"file": ("synthetic.txt", TEXT.encode(), "text/plain")},
        data={
            "expected_version": 1,
            "communication": '{"date":"2026-11-14","precision":"date","provenance":"user_confirmed"}',
        },
    )
    assert r.status_code == 201, r.text
    return cid, r.json()["evidence"]["id"]


def output(eid):
    candidates = []
    for i, (description, kind, amount, currency) in enumerate(
        [
            ("Recharge refund", "refund", 79900, "INR"),
            ("Broadband restoration", "service", None, None),
            ("Goodwill credit", "other", 20000, "INR"),
            ("Technician visit", "service", None, None),
        ]
    ):
        candidates.append(
            {
                "candidate_id": "c" + str(i),
                "terms": {
                    "kind": kind,
                    "description": description,
                    "amount_minor": amount,
                    "currency": currency,
                    "due_at": None,
                },
                "sources": [{"evidence_id": eid, "quote": TEXT.splitlines()[i + 1]}],
                "temporal": {
                    "parse_status": "parsed",
                    "original_wording": [
                        "November 17, 2026",
                        "November 16, 2026",
                        "November 19, 2026",
                        "November 15, 2026",
                    ][i],
                },
                "relation": {"kind": "new"},
                "condition": {},
                "warnings": [],
            }
        )
    return {
        "schema_version": 2,
        "proposal_id": "four-airtel",
        "candidates": candidates,
        "document_warnings": [],
    }


def test_four_airtel_obligations_persist_only_after_human_review(client, db_session):
    cid, eid = setup(client)
    result = output(eid)

    class Engine:
        def extract_proposals_v2(self, request):
            return copy.deepcopy(result)

    app.dependency_overrides[get_intelligence] = lambda: Engine()
    r = post(
        client,
        f"/cases/{cid}/extractions",
        {"expected_version": 2, "evidence_ids": [eid]},
        "extract",
    )
    assert r.status_code == 201, r.text
    assert db_session.query(Obligation).count() == 0
    decisions = [
        {"candidate_id": c["candidate_id"], "action": "confirm"}
        for c in result["candidates"]
    ]
    r = post(
        client,
        f"/cases/{cid}/reviews",
        {
            "expected_version": 3,
            "proposal_id": result["proposal_id"],
            "decisions": decisions,
        },
        "review",
    )
    assert r.status_code == 200 and len(r.json()["confirmed_ids"]) == 4, r.text
    snapshot = client.get(f"/api/v2/cases/{cid}").json()
    assert len(snapshot["obligations"]) == 4
    assert snapshot["projection"]["money_by_currency"]["INR"]["promised_minor"] == 99900
    assert all(o["sources"][0]["evidence_id"] == eid for o in snapshot["obligations"])
    assert all(
        o["terms"]["due_at"] is None for o in snapshot["obligations"]
    )  # dates remain proposals until explicitly confirmed


def test_timeout_never_persists_late_results(client, db_session, monkeypatch):
    cid, eid = setup(client)

    class Slow:
        def extract_proposals_v2(self, request):
            time.sleep(0.08)
            return output(eid)

    app.dependency_overrides[get_intelligence] = lambda: Slow()
    from backend.app.services.platform import intelligence_boundary

    real = intelligence_boundary.invoke
    monkeypatch.setattr(
        intelligence_boundary,
        "invoke",
        lambda method, request: real(method, request, timeout=0.01),
    )
    r = post(
        client,
        f"/cases/{cid}/extractions",
        {"expected_version": 2, "evidence_ids": [eid]},
        "timeout",
    )
    assert r.status_code == 504 and r.json()["error"]["code"] == "AI_TIMEOUT"
    time.sleep(0.1)
    assert (
        db_session.query(Proposal).count() == 0
        and db_session.query(Obligation).count() == 0
    )
    assert client.get(f"/api/v2/cases/{cid}").json()["version"] == 2


def test_real_screenshot_ocr_through_v2_review_and_original_preservation(
    client, db_session, monkeypatch
):
    import io, hashlib
    from PIL import Image, ImageDraw, ImageFont
    from backend.app.ai import document_processor
    from backend.app.models.evidence import Evidence
    from backend.app.services.storage import storage_service

    image = Image.new("RGB", (1200, 180), "white")
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default(size=32)
    draw.text(
        (30, 45),
        "We will refund INR 500 by November 20, 2026.",
        font=font,
        fill="black",
    )
    stream = io.BytesIO()
    image.save(stream, format="PNG")
    original = stream.getvalue()
    calls = []
    real = document_processor.get_ocr_engine

    def ocr():
        calls.append(1)
        return real()

    monkeypatch.setattr(document_processor, "get_ocr_engine", ocr)
    cid = post(
        client,
        "/cases",
        {"title": "Synthetic screenshot OCR", "merchant_name": "Example"},
        "case",
    ).json()["case"]["id"]
    r = client.post(
        f"/api/v2/cases/{cid}/evidence",
        headers={"Idempotency-Key": "png"},
        files={"file": ("synthetic.png", original, "image/png")},
        data={"expected_version": 1, "communication": "{}"},
    )
    assert r.status_code == 201, r.text
    eid = r.json()["evidence"]["id"]

    class ExplicitMockAI:
        def extract_proposals_v2(self, request):
            text = request["evidence"][0]["text"]
            assert "refund" in text.lower() and "500" in text
            candidate = output(eid)["candidates"][0]
            candidate["candidate_id"] = "screenshot-refund"
            candidate["terms"]["amount_minor"] = 50000
            candidate["sources"] = [{"evidence_id": eid, "quote": text}]
            return {
                "schema_version": 2,
                "proposal_id": "screenshot-proposal",
                "candidates": [candidate],
                "document_warnings": [],
            }

    app.dependency_overrides[get_intelligence] = lambda: ExplicitMockAI()
    r = post(
        client,
        f"/cases/{cid}/extractions",
        {"expected_version": 2, "evidence_ids": [eid]},
        "extract",
    )
    assert r.status_code == 201, r.text
    assert calls and db_session.query(Obligation).count() == 0
    r = post(
        client,
        f"/cases/{cid}/reviews",
        {
            "expected_version": 3,
            "proposal_id": "screenshot-proposal",
            "decisions": [{"candidate_id": "screenshot-refund", "action": "confirm"}],
        },
        "review",
    )
    assert r.status_code == 200, r.text
    stored = db_session.get(Evidence, eid)
    assert storage_service.read_file(stored.storage_key) == original
    assert stored.sha256 == hashlib.sha256(original).hexdigest()
    snapshot = client.get(f"/api/v2/cases/{cid}").json()
    assert snapshot["obligations"][0]["sources"][0]["evidence_id"] == eid
    assert snapshot["obligations"][0]["terms"]["amount_minor"] == 50000
    assert any(e["kind"] == "proposal_reviewed" for e in snapshot["events"])
