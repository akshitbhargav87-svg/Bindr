import json
import pytest
from backend.app.models.case import Case
from backend.app.models.integrations import AggregateConsent
from backend.app.models.aggregates import Company, CompanyAssignment
from backend.app.models.workflow import Obligation
from backend.app.services.platform.aggregates import company_summary
from backend.app.services.platform.operations import canonical
from backend.app.services.platform.webhooks import verify_svix, verify_meta


def test_calendar_escapes_newlines_and_has_stable_uid(client, secondary_client):
    cid = client.post(
        "/api/v2/cases",
        headers={"Idempotency-Key": "c"},
        json={"title": "Synthetic calendar", "merchant_name": "Example"},
    ).json()["case"]["id"]
    r = client.post(
        f"/api/v2/cases/{cid}/manual-promises",
        headers={"Idempotency-Key": "m"},
        json={
            "expected_version": 1,
            "origin": "user_attested",
            "confirmed": True,
            "terms": {
                "kind": "service",
                "description": "Test\nBEGIN:VEVENT\nSUMMARY:injected",
                "due_at": "2026-12-20T18:00:00+05:30",
            },
        },
    )
    assert r.status_code == 201, r.text
    a = client.get(f"/api/v2/cases/{cid}/calendar.ics")
    assert a.status_code == 200
    assert a.content.count(b"\r\nBEGIN:VEVENT\r\n") == 1
    assert b"DTSTART:20261220T123000Z" in a.content
    assert b"UID:" + r.json()["obligation_id"].encode() + b"@bindr.invalid" in a.content
    assert secondary_client.get(f"/api/v2/cases/{cid}/calendar.ics").status_code == 404


def test_aggregate_threshold_withdrawal_and_public_disable(client, db_session):
    db_session.add(
        Company(
            id="synthetic-example",
            name="Synthetic Example",
            registry_version="test-only",
        )
    )
    for i in range(20):
        owner = "synthetic-" + str(i)
        cid = "c-" + str(i)
        oid = "o-" + str(i)
        db_session.add(
            Case(id=cid, owner_id=owner, title="Synthetic", merchant_name="Example")
        )
        db_session.flush()
        db_session.add(CompanyAssignment(case_id=cid, company_id="synthetic-example"))
        db_session.add(AggregateConsent(owner_id=owner, enabled=1, version=1))
        db_session.add(
            Obligation(
                id=oid,
                root_id=oid,
                case_id=cid,
                origin="user_attested",
                state="active",
                sources="[]",
                terms=canonical(
                    {
                        "amount_minor": 50000,
                        "currency": "INR",
                        "description": "synthetic",
                        "kind": "refund",
                        "due_at": None,
                    }
                ),
                created_at="2026-11-15T00:00:00Z",
            )
        )
    db_session.commit()
    a = company_summary(db_session, "synthetic-example", "2026-11-01", "2026-11-30")
    assert a["distinct_participants"] == 20 and a["denominator_obligations"] == 20
    assert not any(key in a for key in ("owner_id", "email", "case_id", "sources"))
    consent = db_session.get(AggregateConsent, "synthetic-0")
    consent.enabled = 0
    db_session.commit()
    assert (
        company_summary(db_session, "synthetic-example", "2026-11-01", "2026-11-30")[
            "suppressed"
        ]
        is True
    )
    assert client.get("/api/v2/companies/scoreboard").status_code == 503


def test_real_signature_algorithms_reject_tampered_and_expired_webhooks():
    import base64, hashlib, hmac
    from fastapi import HTTPException

    raw = b'{"type":"synthetic"}'
    timestamp = "1000"
    eid = "message-test"
    key = b"k" * 32
    digest = base64.b64encode(
        hmac.new(
            key, eid.encode() + b"." + timestamp.encode() + b"." + raw, hashlib.sha256
        ).digest()
    ).decode()
    headers = {
        "svix-id": eid,
        "svix-timestamp": timestamp,
        "svix-signature": "v1," + digest,
    }
    secret = "whsec_" + base64.b64encode(key).decode()
    assert verify_svix(raw, headers, secret, now=1000)["type"] == "synthetic"
    with pytest.raises(HTTPException):
        verify_svix(raw + b" ", headers, secret, now=1000)
    with pytest.raises(HTTPException):
        verify_svix(raw, headers, secret, now=1301)
    signature = "sha256=" + hmac.new(key, raw, hashlib.sha256).hexdigest()
    assert verify_meta(raw, signature, key.decode())["type"] == "synthetic"
    with pytest.raises(HTTPException):
        verify_meta(raw + b" ", signature, key.decode())
