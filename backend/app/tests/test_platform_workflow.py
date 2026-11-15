import pytest
from backend.app.models.workflow import CaseEvent, Obligation


def post(client, path, body, key):
    return client.post("/api/v2" + path, json=body, headers={"Idempotency-Key": key})


def setup_case(client):
    c = post(
        client,
        "/cases",
        {"title": "Synthetic receipt", "merchant_name": "Example"},
        "case",
    ).json()["case"]
    path = "/cases/" + c["id"]
    body = {
        "expected_version": 1,
        "terms": {
            "kind": "refund",
            "description": "Refund ₹500",
            "amount_minor": 50000,
            "currency": "INR",
            "due_at": None,
        },
        "origin": "user_attested",
        "confirmed": True,
    }
    r = post(client, path + "/manual-promises", body, "manual")
    assert r.status_code == 201, r.text
    return path, r.json()["obligation_id"], body


def test_partial_pending_full_correction_reopen_and_replay(client):
    path, oid, manual = setup_case(client)
    assert post(client, path + "/manual-promises", manual, "manual").status_code == 201
    body = {
        "expected_version": 2,
        "kind": "partial",
        "allocations": [{"obligation_id": oid, "amount_minor": 20000}],
        "received_at": "2026-01-01T00:00:00Z",
    }
    a = post(client, path + "/outcomes", body, "receipt")
    assert a.status_code == 201, a.text
    assert post(client, path + "/outcomes", body, "receipt").json() == a.json()
    assert post(client, path + "/outcomes", body, "stale").status_code == 409
    body = {
        "expected_version": 3,
        "kind": "pending",
        "allocations": [{"obligation_id": oid}],
        "note": "Company says it is pending",
    }
    assert post(client, path + "/outcomes", body, "pending").status_code == 201
    view = client.get("/api/v2" + path).json()
    assert view["projection"]["money_by_currency"] == {
        "INR": {
            "promised_minor": 50000,
            "received_minor": 20000,
            "outstanding_minor": 30000,
        }
    }
    assert view["projection"]["status"] != "resolved"
    full = {
        "expected_version": 4,
        "kind": "full",
        "allocations": [{"obligation_id": oid, "amount_minor": 30000}],
        "received_at": "2026-01-02T00:00:00Z",
    }
    r = post(client, path + "/outcomes", full, "full")
    assert r.status_code == 201, r.text
    assert client.get("/api/v2" + path).json()["projection"]["status"] == "resolved"
    correction = {
        "expected_version": 5,
        "kind": "correction",
        "corrects_event_id": r.json()["event_id"],
        "note": "Receipt was reversed",
    }
    assert post(client, path + "/outcomes", correction, "correction").status_code == 201
    assert (
        post(
            client,
            path + "/lifecycle",
            {"expected_version": 6, "action": "reopen", "reason": "Still outstanding"},
            "reopen",
        ).status_code
        == 200
    )
    view = client.get("/api/v2" + path).json()
    assert view["projection"]["money_by_currency"]["INR"]["received_minor"] == 20000
    assert len([e for e in view["events"] if e["kind"] == "full"]) == 1


def test_revisions_keep_original_and_receipts(client, db_session):
    path, oid, body = setup_case(client)
    r = post(
        client,
        path + "/manual-promises",
        {
            **body,
            "expected_version": 2,
            "predecessor_id": oid,
            "reason": "Deadline changed",
            "terms": {**body["terms"], "due_at": "2026-12-20T18:00:00+05:30"},
        },
        "revision",
    )
    assert r.status_code == 201, r.text
    rows = client.get("/api/v2" + path).json()["obligations"]
    old = next(x for x in rows if x["id"] == oid)
    new = next(x for x in rows if x["id"] == r.json()["obligation_id"])
    assert old["state"] == "superseded" and old["terms"]["due_at"] is None
    assert new["predecessor_id"] == oid and old["root_id"] == new["root_id"]
    assert (
        post(
            client,
            path + "/manual-promises",
            {**body, "expected_version": 3, "predecessor_id": oid, "reason": "Branch"},
            "branch",
        ).status_code
        == 409
    )
    assert db_session.query(Obligation).count() == 2


@pytest.mark.parametrize(
    "terms",
    [
        {"kind": "refund", "description": "x", "amount_minor": -1, "currency": "INR"},
        {"kind": "refund", "description": "x", "amount_minor": 1.5, "currency": "INR"},
        {"kind": "refund", "description": "x", "amount_minor": 10, "currency": None},
        {"kind": "refund", "description": "x", "due_at": "2026-12-01T10:00:00"},
    ],
)
def test_bad_money_or_naive_deadline_rejected(client, db_session, terms):
    path, oid, body = setup_case(client)
    r = post(
        client,
        path + "/manual-promises",
        {**body, "expected_version": 2, "terms": terms},
        "invalid",
    )
    assert r.status_code == 422
    assert db_session.query(Obligation).count() == 1


def test_cross_case_outcome_is_atomic(client, db_session, secondary_client):
    path, oid, _ = setup_case(client)
    assert secondary_client.get("/api/v2" + path).status_code == 404
    before = db_session.query(CaseEvent).count()
    r = post(
        client,
        path + "/outcomes",
        {
            "expected_version": 2,
            "kind": "full",
            "allocations": [{"obligation_id": "invented", "amount_minor": 1}],
            "received_at": "2026-01-01T00:00:00Z",
        },
        "bad",
    )
    assert r.status_code == 404
    assert db_session.query(CaseEvent).count() == before
    assert client.get("/api/v2" + path).json()["version"] == 2


@pytest.mark.parametrize(
    "anchor,unit,minimum,maximum,expected",
    [
        ("2026-12-28", "calendar_days", 5, 5, ("2027-01-02", "2027-01-02")),
        ("2026-11-13", "business_days", 5, 7, ("2026-11-20", "2026-11-24")),
        ("2028-02-28", "calendar_days", 1, 2, ("2028-02-29", "2028-03-01")),
    ],
)
def test_calendar_boundaries(client, anchor, unit, minimum, maximum, expected):
    r = post(
        client,
        "/deadline-preview",
        {
            "anchor": {"date": anchor, "precision": "date"},
            "anchor_confirmed": True,
            "unit": unit,
            "minimum": minimum,
            "maximum": maximum,
        },
        "unused",
    )
    assert r.status_code == 200, r.text
    d = r.json()["deadline"]
    assert (d["earliest"], d["latest"]) == expected
    assert d["calendar"]["coverage"] == "weekends_only_no_holiday_coverage"


def test_missing_anchor_condition_and_holiday_policy(client):
    body = {
        "anchor": {},
        "anchor_confirmed": False,
        "unit": "calendar_days",
        "minimum": 5,
        "maximum": 7,
    }
    assert (
        post(client, "/deadline-preview", body, "a").json()["deadline"]["status"]
        == "anchor_missing"
    )
    assert (
        post(client, "/deadline-preview", {**body, "conditional": True}, "b").json()[
            "deadline"
        ]["status"]
        == "condition_unconfirmed"
    )
    body.update(
        anchor={"date": "2026-11-13", "precision": "date"},
        anchor_confirmed=True,
        unit="business_days",
        minimum=1,
        maximum=1,
        calendar_id="custom",
        calendar_version="user-holidays-1",
        holidays=["2026-11-16"],
    )
    assert (
        post(client, "/deadline-preview", body, "c").json()["deadline"]["latest"]
        == "2026-11-17"
    )


def test_deadline_inputs_persist_and_dst_is_not_normalized(client):
    path, oid, base = setup_case(client)
    selection = {
        "anchor": {
            "date": "2026-12-28",
            "precision": "date",
            "timezone": "Asia/Kolkata",
        },
        "anchor_confirmed": True,
        "unit": "calendar_days",
        "minimum": 5,
        "maximum": 5,
    }
    body = {
        **base,
        "expected_version": 2,
        "deadline": selection,
        "terms": {**base["terms"], "due_at": "2027-01-02T18:00:00+05:30"},
    }
    r = post(client, path + "/manual-promises", body, "dated")
    assert r.status_code == 201, r.text
    row = next(
        o
        for o in client.get("/api/v2" + path).json()["obligations"]
        if o["id"] == r.json()["obligation_id"]
    )
    assert row["deadline"]["input"]["anchor"]["date"] == "2026-12-28"
    assert row["deadline"]["proposal"]["latest"] == "2027-01-02"
    assert row["deadline"]["proposal"]["calendar"]["version"] == "1"
    bad = {
        **body,
        "expected_version": 3,
        "terms": {**body["terms"], "due_at": "2027-01-04T18:00:00+05:30"},
    }
    assert post(client, path + "/manual-promises", bad, "bad-date").status_code == 422
    assert (
        post(
            client,
            path + "/manual-promises",
            {
                **bad,
                "deadline_override_reason": "User reviewed a separately confirmed date",
            },
            "override",
        ).status_code
        == 201
    )
    dst = {
        "anchor": {
            "date": "2026-11-01",
            "precision": "date",
            "timezone": "America/New_York",
        },
        "anchor_confirmed": True,
        "unit": "explicit_date",
        "explicit_date": "2026-11-01",
        "explicit_time": "01:30:00",
    }
    result = post(client, "/deadline-preview", dst, "dst").json()["deadline"]
    assert result["earliest_at"] is None
    assert (
        "ambiguous_or_nonexistent_local_time_requires_explicit_offset"
        in result["warnings"]
    )


def test_received_counter_uses_receipt_currency_after_an_unpaid_revision(client):
    path, oid, body = setup_case(client)
    revision = {
        **body,
        "expected_version": 2,
        "predecessor_id": oid,
        "reason": "User confirmed corrected currency before any receipt",
        "terms": {**body["terms"], "amount_minor": 10000, "currency": "USD"},
    }
    r = post(client, path + "/manual-promises", revision, "currency-fix")
    assert r.status_code == 201, r.text
    receipt = {
        "expected_version": 3,
        "kind": "partial",
        "allocations": [
            {"obligation_id": r.json()["obligation_id"], "amount_minor": 2000}
        ],
        "received_at": "2026-01-01T00:00:00Z",
    }
    assert post(client, path + "/outcomes", receipt, "receipt").status_code == 201
    result = client.get("/api/v2/account/received-counter").json()
    assert result["received_minor_by_currency"] == {"USD": 2000}
    events = client.get("/api/v2" + path).json()["events"]
    assert [e["sequence"] for e in events] == list(range(1, len(events) + 1))
