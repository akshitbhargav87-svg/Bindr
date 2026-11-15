import json
import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, text
from backend.app.models.case import Case
from backend.app.models.platform import CaptureDraft, Operation
from backend.app.services.platform.operations import execute
from backend.migrations import upgrade, REVISIONS


def create(client, key="create-1"):
    return client.post(
        "/api/v2/cases",
        headers={"Idempotency-Key": key},
        json={"title": "Synthetic refund", "merchant_name": "Example"},
    )


def test_case_replay_and_account_scope(client, secondary_client, db_session):
    a = create(client)
    assert a.status_code == 201
    assert create(client).json() == a.json()
    assert db_session.query(Case).count() == 1
    changed = client.post(
        "/api/v2/cases",
        headers={"Idempotency-Key": "create-1"},
        json={"title": "Changed", "merchant_name": "Example"},
    )
    assert (
        changed.status_code == 409
        and changed.json()["error"]["code"] == "IDEMPOTENCY_CONFLICT"
    )
    assert (
        create(client, "intentional-second").json()["case"]["id"]
        != a.json()["case"]["id"]
    )
    assert create(secondary_client).json()["case"]["id"] != a.json()["case"]["id"]


def test_capture_recovery_and_stale_operations(client, secondary_client):
    body = {
        "capture": {
            "text": "हमें ₹500 वापस मिलेंगे",
            "communication": {
                "date": "2099-12-28",
                "precision": "date",
                "timezone": "Asia/Kolkata",
                "provenance": "user_confirmed",
            },
        }
    }
    a = client.post(
        "/api/v2/capture-drafts", json=body, headers={"Idempotency-Key": "save"}
    ).json()["draft"]
    path = "/api/v2/capture-drafts/" + a["id"]
    assert a["warnings"] == ["future_communication_date_requires_confirmation"]
    assert (
        client.get(path).json()["draft"]["capture"]["text"] == body["capture"]["text"]
    )
    assert secondary_client.get(path).status_code == 404
    update = {**body, "expected_version": 1}
    r = client.put(path, json=update, headers={"Idempotency-Key": "update"})
    assert r.status_code == 200 and r.json()["draft"]["version"] == 2
    assert (
        client.put(path, json=update, headers={"Idempotency-Key": "update"}).json()
        == r.json()
    )
    assert (
        client.put(
            path, json=update, headers={"Idempotency-Key": "new-stale"}
        ).status_code
        == 409
    )


@pytest.mark.parametrize(
    "capture",
    [
        {"text": "test", "communication": {"date": "2026-11-31", "precision": "date"}},
        {
            "text": "test",
            "communication": {"date": "2026-11-30", "precision": "unknown"},
        },
        {"text": "test", "communication": {"timezone": "Invented/Zone"}},
        {"text": "test", "evidence_ids": ["invented"]},
        {"text": "test", "evidence_ids": ["same", "same"]},
    ],
)
def test_invalid_capture_not_persisted(client, db_session, capture):
    r = client.post(
        "/api/v2/capture-drafts",
        json={"capture": capture},
        headers={"Idempotency-Key": "bad"},
    )
    assert r.status_code in (404, 422)
    assert set(r.json()) == {"error"}
    assert db_session.query(CaptureDraft).count() == 0
    assert db_session.query(Operation).count() == 0


def test_operation_failure_is_atomic(db_session):
    def broken():
        db_session.add(Case(owner_id="u", title="Synthetic", merchant_name="Example"))
        db_session.flush()
        raise ValueError("synthetic failure")

    with pytest.raises(ValueError):
        execute(db_session, "u", "test", "key", {}, broken)
    assert db_session.query(Case).count() == 0
    assert db_session.query(Operation).count() == 0
    assert execute(db_session, "u", "test", "key", {}, lambda: {"ok": True}) == {
        "ok": True
    }


def test_populated_legacy_migration_preserves_records(tmp_path):
    engine = create_engine("sqlite:///" + str(tmp_path / "legacy.db"))
    with engine.begin() as c:
        c.execute(
            text(
                "CREATE TABLE cases (id VARCHAR(36) PRIMARY KEY,title VARCHAR(255),merchant_name VARCHAR(255),status VARCHAR(20),created_at VARCHAR(50))"
            )
        )
        c.execute(
            text(
                "INSERT INTO cases VALUES ('old','Original','Example','open','2026-11-01T00:00:00Z')"
            )
        )
    upgrade(engine)
    upgrade(engine)
    with engine.connect() as c:
        row = c.execute(text("SELECT id,title,owner_id,version FROM cases")).one()
        assert tuple(row) == ("old", "Original", "legacy-unclaimed", 1)
        assert c.execute(
            text("SELECT count(*) FROM bindr_schema_revisions")
        ).scalar() == len(REVISIONS)
    engine.dispose()


def test_unknown_migration_refuses_changes(tmp_path):
    engine = create_engine("sqlite:///" + str(tmp_path / "future.db"))
    with engine.begin() as c:
        c.execute(
            text(
                "CREATE TABLE bindr_schema_revisions(version INTEGER PRIMARY KEY,name TEXT,applied_at TEXT)"
            )
        )
        c.execute(
            text("INSERT INTO bindr_schema_revisions VALUES (999,'future','now')")
        )
    with pytest.raises(RuntimeError, match="Unknown database revision"):
        upgrade(engine)
    from sqlalchemy import inspect

    assert inspect(engine).get_table_names() == ["bindr_schema_revisions"]
    engine.dispose()


def test_deployment_schema_check_never_creates_tables(tmp_path):
    from sqlalchemy import inspect
    from backend.migrations import assert_current

    engine = create_engine("sqlite:///" + str(tmp_path / "readiness.db"))
    with pytest.raises(RuntimeError, match="Apply and verify"):
        assert_current(engine)
    assert inspect(engine).get_table_names() == []
    upgrade(engine)
    assert assert_current(engine) == max(REVISIONS)
    engine.dispose()
