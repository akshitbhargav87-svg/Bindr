import json
import time
import pytest
from backend.app.tests.test_accounts import accounts, login
from backend.app.models.account import AccountSession
from backend.app.models.case import Case
from backend.app.models.jobs import Job
from backend.app.services.platform.jobs import enqueue, run_one, cancel_case_jobs
from backend.app.services.platform.deletion import cleanup_case
from backend.app.tests.conftest import TestingSessionLocal


def post(client, path, body, key):
    return client.post("/api/v2" + path, json=body, headers={"Idempotency-Key": key})


def test_expired_then_same_account_recovers_but_different_account_cannot(accounts):
    client, provider, db = accounts
    token = provider.add()
    a = login(client, token).json()["account"]["id"]
    saved = post(
        client,
        "/capture-drafts",
        {"capture": {"text": "Exact synthetic unsaved wording 😀"}},
        "draft",
    ).json()["draft"]
    path = "/api/v2/capture-drafts/" + saved["id"]
    session = db.query(AccountSession).one()
    session.expires_at = int(time.time()) - 1
    db.commit()
    assert client.get(path).status_code == 401
    assert login(client, token).json()["account"]["id"] == a
    assert (
        client.get(path).json()["draft"]["capture"]["text"]
        == "Exact synthetic unsaved wording 😀"
    )
    client.cookies.clear()
    client.headers.pop("X-Bindr-Account")
    assert login(client, provider.add("person-b")).status_code == 200
    assert client.get(path).status_code == 404
    assert (
        client.put(
            path,
            json={"expected_version": 1, "capture": {"text": "overwrite"}},
            headers={"Idempotency-Key": "bad"},
        ).status_code
        == 404
    )


def test_delete_immediately_hides_v1_and_v2_then_cleans_original(accounts):
    client, provider, db = accounts
    login(client, provider.add())
    cid = post(
        client,
        "/cases",
        {"title": "Disposable synthetic", "merchant_name": "Example"},
        "case",
    ).json()["case"]["id"]
    r = client.post(
        "/api/v2/cases/" + cid + "/evidence",
        headers={"Idempotency-Key": "upload"},
        files={"file": ("s.txt", b"original synthetic evidence", "text/plain")},
        data={"expected_version": 1, "communication": "{}"},
    )
    assert r.status_code == 201, r.text
    eid = r.json()["evidence"]["id"]
    r = client.request(
        "DELETE",
        "/api/v2/cases/" + cid,
        json={"expected_version": 2, "confirmation": "DELETE"},
        headers={"Idempotency-Key": "delete"},
    )
    assert r.status_code == 202, r.text
    assert client.get("/api/v1/cases/" + cid).status_code == 404
    assert client.get("/api/v2/cases/" + cid).status_code == 404
    assert client.get(f"/api/v1/cases/{cid}/evidence/{eid}/content").status_code == 404
    job = db.get(Job, r.json()["job"]["id"])
    assert cleanup_case(db, job)["deleted"] is True
    db.commit()
    assert db.get(Case, cid) is None
    assert cleanup_case(db, job)["deleted"] is True


def test_job_persists_across_session_and_retries_without_payload_error_leak(db_session):
    job = enqueue(db_session, "u", "synthetic", {"private_text": "synthetic-only"})
    jid = job.id
    db_session.commit()
    calls = []

    def failing(db, row):
        calls.append(row.id)
        raise ValueError("PRIVATE PROVIDER DETAIL")

    assert (
        run_one(TestingSessionLocal, {"synthetic": failing}, now=int(time.time()))
        == jid
    )
    with TestingSessionLocal() as db:
        row = db.get(Job, jid)
        assert row.state == "queued" and row.error_code == "JOB_FAILED"
        retry = row.run_at
    assert (
        run_one(
            TestingSessionLocal, {"synthetic": lambda db, row: {"ok": True}}, now=retry
        )
        == jid
    )
    db_session.expire_all()
    row = db_session.get(Job, jid)
    assert (
        row.state == "succeeded"
        and row.payload == "{}"
        and json.loads(row.result) == {"ok": True}
    )


def test_expired_send_lease_requires_reconciliation_not_resend(db_session):
    job = enqueue(db_session, "u", "send", {})
    job.state = "running"
    job.lease_until = 1
    db_session.commit()
    calls = []
    assert (
        run_one(
            TestingSessionLocal, {"send": lambda db, row: calls.append(row.id)}, now=100
        )
        is None
    )
    db_session.expire_all()
    assert db_session.get(Job, job.id).error_code == "DELIVERY_UNCERTAIN"
    assert calls == []


def test_account_export_excludes_credentials_and_delete_revokes_every_session(
    accounts, monkeypatch
):
    client, provider, db = accounts
    response = login(client, provider.add())
    owner = response.json()["account"]["id"]
    cid = post(
        client,
        "/cases",
        {"title": "Disposable account case", "merchant_name": "Example"},
        "case",
    ).json()["case"]["id"]
    post(
        client,
        "/capture-drafts",
        {"capture": {"text": "Synthetic private capture"}},
        "capture",
    )
    r = post(client, "/account/export", {}, "export")
    assert r.status_code == 202, r.text
    from backend.app.services.platform.accounts import export_account, cleanup_account

    export_account(db, db.get(Job, r.json()["job"]["id"]))
    db.commit()
    content = client.get(
        "/api/v2/exports/" + r.json()["export_id"] + "?download=true"
    ).content
    import zipfile, io

    with zipfile.ZipFile(io.BytesIO(content)) as bundle:
        record = json.loads(bundle.read("record.json"))
        assert record["credentials_included"] is False
        assert (
            record["capture_drafts"][0]["capture"]["text"]
            == "Synthetic private capture"
        )
        assert "token_hash" not in record and "refresh_token" not in record
    r = client.request(
        "DELETE",
        "/api/v2/account",
        json={"confirmation": "DELETE MY ACCOUNT"},
        headers={"Idempotency-Key": "delete-account"},
    )
    assert r.status_code == 202, r.text
    assert client.get("/api/v1/auth/me").status_code == 401
    assert client.get("/api/v1/cases/" + cid).status_code == 401
    assert (
        login(client, provider.tokens.keys().__iter__().__next__()).status_code == 401
    )
    calls = []
    monkeypatch.setattr(
        provider, "delete", lambda uid: calls.append(uid), raising=False
    )
    from backend.app.services import identity

    monkeypatch.setattr(identity, "get_identity_provider", lambda: provider)
    job = db.get(Job, r.json()["job"]["id"])
    assert cleanup_account(db, job)["deleted"]
    db.commit()
    from backend.app.models.account import Account
    from backend.app.models.platform import CaptureDraft

    assert db.get(Account, owner) is None and db.query(CaptureDraft).count() == 0
    assert db.query(AccountSession).count() == 0 and db.get(Case, cid) is None
    assert calls == ["person-a"]


def test_revision_reschedules_and_opt_out_cancels_reminders(client, db_session):
    cid = post(
        client,
        "/cases",
        {"title": "Synthetic reminder", "merchant_name": "Example"},
        "case",
    ).json()["case"]["id"]
    prefs = {
        "expected_version": 0,
        "in_app": True,
        "days_before": [3, 1, 0],
        "follow_up_days": 2,
    }
    r = client.put(
        "/api/v2/notification-preferences",
        json=prefs,
        headers={"Idempotency-Key": "prefs"},
    )
    assert r.status_code == 200, r.text
    terms = {
        "kind": "refund",
        "description": "Refund",
        "amount_minor": 50000,
        "currency": "INR",
        "due_at": "2099-11-20T12:00:00+05:30",
    }
    manual = {
        "expected_version": 1,
        "terms": terms,
        "origin": "user_attested",
        "confirmed": True,
    }
    oid = post(client, f"/cases/{cid}/manual-promises", manual, "manual").json()[
        "obligation_id"
    ]
    old_ids = {
        j.id for j in db_session.query(Job).filter_by(case_id=cid, state="queued").all()
    }
    assert len(old_ids) == 4
    r = post(
        client,
        f"/cases/{cid}/manual-promises",
        {
            **manual,
            "expected_version": 2,
            "predecessor_id": oid,
            "reason": "Reviewed changed date",
            "terms": {**terms, "due_at": "2099-11-25T12:00:00+05:30"},
        },
        "revision",
    )
    assert r.status_code == 201, r.text
    db_session.expire_all()
    new_ids = {
        j.id for j in db_session.query(Job).filter_by(case_id=cid, state="queued").all()
    }
    assert len(new_ids) == 4 and old_ids.isdisjoint(new_ids)
    assert all(db_session.get(Job, j).state == "cancelled" for j in old_ids)
    r = client.put(
        "/api/v2/notification-preferences",
        json={**prefs, "expected_version": 1, "in_app": False},
        headers={"Idempotency-Key": "optout"},
    )
    assert r.status_code == 200, r.text
    assert db_session.query(Job).filter_by(case_id=cid, state="queued").count() == 0


def test_capture_pairing_dies_with_revoked_account_session(accounts):
    client, provider, db = accounts
    login(client, provider.add())
    cid = post(
        client,
        "/cases",
        {"title": "Synthetic pairing", "merchant_name": "Example"},
        "case",
    ).json()["case"]["id"]
    token = post(client, "/connectors/extension/pair", {"case_id": cid}, "pair").json()[
        "capture_token"
    ]
    db.query(AccountSession).update({"revoked_at": int(time.time())})
    db.commit()
    r = client.post(
        "/api/v2/connectors/extension/capture",
        headers={"Authorization": "Capture " + token},
        files={"file": ("s.txt", b"Synthetic only", "text/plain")},
    )
    assert r.status_code == 401
