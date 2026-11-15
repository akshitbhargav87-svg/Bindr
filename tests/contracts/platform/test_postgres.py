"""Actual PostgreSQL overlapping transactions; never replace this with SQLite.

Set BINDR_TEST_DATABASE_URL to a disposable database. A unique schema isolates each test.
"""

import os
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from backend.migrations import upgrade
from backend.app.models.case import Case
from backend.app.models.account import Account, AccountSession, AccountDraft
from backend.app.models.evidence import Evidence
from backend.app.models.platform import CaptureDraft
from backend.app.services.platform.operations import execute
from backend.app.services.platform.workflow import claim


@pytest.fixture
def postgres():
    url = os.getenv("BINDR_TEST_DATABASE_URL")
    if not url:
        pytest.skip(
            "Requires explicit disposable PostgreSQL URL; SQLite cannot prove overlap"
        )
    if not url.startswith("postgresql+psycopg://"):
        pytest.fail("Requires psycopg PostgreSQL URL")
    schema = "platform_test_" + uuid.uuid4().hex
    admin = create_engine(url)
    with admin.begin() as c:
        c.execute(text("CREATE SCHEMA " + schema))
    engine = create_engine(
        url, connect_args={"options": "-csearch_path=" + schema}, pool_size=5
    )
    upgrade(engine)
    yield engine, sessionmaker(bind=engine, expire_on_commit=False)
    engine.dispose()
    with admin.begin() as c:
        c.execute(text("DROP SCHEMA " + schema + " CASCADE"))
    admin.dispose()


def test_matching_operation_serializes_and_commits_one_case(postgres):
    engine, factory = postgres
    barrier = threading.Barrier(2)
    calls = []

    def work():
        with factory() as db:
            barrier.wait(timeout=5)

            def save():
                calls.append(1)
                time.sleep(0.15)
                row = Case(
                    owner_id="same", title="Synthetic overlap", merchant_name="Example"
                )
                db.add(row)
                db.flush()
                return {"case_id": row.id}

            return execute(
                db, "same", "create", "same-key", {"title": "Synthetic overlap"}, save
            )

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: work(), range(2)))
    assert results[0] == results[1] and len(calls) == 1
    with factory() as db:
        assert db.query(Case).count() == 1


def test_two_new_operations_cas_have_exactly_one_winner(postgres):
    engine, factory = postgres
    with factory() as db:
        case = Case(owner_id="u", title="Synthetic CAS", merchant_name="Example")
        db.add(case)
        db.commit()
        cid = case.id
    barrier = threading.Barrier(2)

    def work(index):
        with factory() as db:
            case = db.get(Case, cid)
            barrier.wait(timeout=5)

            def save():
                claim(db, case, 1)
                return {"version": case.version}

            try:
                execute(db, "u", "mutation", str(index), {"expected_version": 1}, save)
                return "winner"
            except HTTPException as exc:
                return exc.detail["error"]["code"]

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(work, range(2)))
    assert sorted(results) == ["VERSION_CONFLICT", "winner"]
    with factory() as db:
        assert db.get(Case, cid).version == 2


def test_populated_postgres_upgrade_preserves_private_account_records(postgres):
    engine, factory = postgres
    with factory() as db:
        account = Account(
            id="a",
            provider_uid="synthetic-provider",
            email="synthetic@example.test",
            created_at=1,
        )
        case = Case(id="c", owner_id="a", title="मूल मामला", merchant_name="Example")
        db.add(account)
        db.add(case)
        db.flush()
        db.add(
            AccountSession(
                id="s",
                token_hash="a" * 64,
                account_id="a",
                created_at=1,
                expires_at=1900000000,
                auth_time=1,
                factor_version="v",
                user_agent="synthetic",
            )
        )
        db.add(
            AccountDraft(
                case_id="c",
                account_id="a",
                payload='{"text":"retained draft"}',
                version=4,
            )
        )
        db.add(
            Evidence(
                id="e",
                case_id="c",
                filename="original.txt",
                media_type="text/plain",
                size_bytes=3,
                sha256="b" * 64,
                storage_key="private-original.bin",
            )
        )
        db.commit()
    # Simulate the previous release's populated schema at revision 1: remove only new
    # empty tables/revision rows, keeping all original account/case tables intact.
    from backend.app.core.database import Base

    names = [
        "intake_message_identity_v2",
        "private_push_devices_v2",
        "capture_capabilities_v2",
        "provider_links_v2",
        "case_company_v2",
        "canonical_companies_v2",
        "aggregate_consent_v2",
        "account_control_v2",
        "private_intake_v2",
        "intake_aliases_v2",
        "oauth_states_v2",
        "provider_connections_v2",
        "private_exports_v2",
        "notification_preferences_v2",
        "platform_jobs",
        "case_control_v2",
        "proposals_v2",
        "case_events_v2",
        "obligations_v2",
        "evidence_communication",
        "capture_drafts",
        "platform_operations",
    ]
    with engine.begin() as conn:
        for name in names:
            Base.metadata.tables[name].drop(conn)
        conn.execute(text("DELETE FROM bindr_schema_revisions WHERE version>1"))
    upgrade(engine)
    upgrade(engine)
    with factory() as db:
        assert db.get(Case, "c").title == "मूल मामला"
        assert db.get(Case, "c").owner_id == "a"
        assert db.get(AccountDraft, "c").version == 4
        assert db.get(AccountSession, "s").token_hash == "a" * 64
        assert db.get(Evidence, "e").sha256 == "b" * 64
        assert db.get(Evidence, "e").storage_key == "private-original.bin"


def test_concurrent_identical_upload_has_one_original_and_one_version(
    postgres, tmp_path, monkeypatch
):
    engine, factory = postgres
    from fastapi.testclient import TestClient
    from backend.app.main import app
    from backend.app.core.database import get_db
    from backend.app.core.auth import create_authenticated_session
    from backend.app.core.config import settings
    from backend.app.services.storage import storage_service

    monkeypatch.setattr(settings, "AUTH_PROVIDER", "anonymous")
    monkeypatch.setattr(settings, "ENVIRONMENT", "development")
    monkeypatch.setattr(storage_service, "base_dir", str(tmp_path))
    with factory() as db:
        row = Case(owner_id="u", title="Concurrent original", merchant_name="Example")
        db.add(row)
        db.commit()
        cid = row.id

    def dependency():
        with factory() as db:
            yield db

    app.dependency_overrides[get_db] = dependency
    barrier = threading.Barrier(2)

    def upload(index):
        token, csrf = create_authenticated_session("u")
        with TestClient(app) as client:
            client.cookies.set("pk_session", token)
            barrier.wait(timeout=5)
            r = client.post(
                f"/api/v2/cases/{cid}/evidence",
                headers={"X-CSRF-Token": csrf, "Idempotency-Key": str(index)},
                files={"file": ("same.txt", b"Exact synthetic bytes", "text/plain")},
                data={"expected_version": 1, "communication": "{}"},
            )
            assert r.status_code == 201, r.text
            return r.json()

    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(upload, range(2)))
        assert results[0]["evidence"]["id"] == results[1]["evidence"]["id"]
        assert all(r["case_version"] == 2 for r in results)
        assert sum(r["duplicate_of"] is not None for r in results) == 1
        with factory() as db:
            assert db.query(Evidence).count() == 1 and db.get(Case, cid).version == 2
        assert len(list(tmp_path.glob("*.bin"))) == 1
    finally:
        app.dependency_overrides.clear()


def test_postgres_delete_preserves_other_owner_and_removes_legacy_and_v2_rows(
    postgres, tmp_path, monkeypatch
):
    engine, factory = postgres
    from types import SimpleNamespace
    from backend.app.models.commitment import Commitment
    from backend.app.models.workflow import CaseControl, Obligation
    from backend.app.models.integrations import Intake, IntakeAlias
    from backend.app.services.platform.deletion import cleanup_case
    from backend.app.services.storage import storage_service
    from backend.app.services.platform.operations import canonical

    monkeypatch.setattr(storage_service, "base_dir", str(tmp_path))
    with factory() as db:
        a = Case(
            id="a",
            owner_id="deleted:a",
            title="Synthetic deleted",
            merchant_name="Example",
        )
        db.add(a)
        db.add(
            Case(id="b", owner_id="other", title="Retained", merchant_name="Example")
        )
        db.flush()
        db.add(CaseControl(case_id="a", owner_id="owner", state="deleting"))
        ekey, sha, size = storage_service.save_file(b"Original", str(uuid.uuid4()))
        ikey, _, _ = storage_service.save_file(b"Private inbound", str(uuid.uuid4()))
        db.add(
            Evidence(
                id="e",
                case_id="a",
                filename="original.txt",
                media_type="text/plain",
                storage_key=ekey,
                size_bytes=size,
                sha256=sha,
            )
        )
        db.add(Commitment(id="old", case_id="a", description="Original legacy promise"))
        db.add(
            Commitment(
                id="new",
                case_id="a",
                description="Legacy revision",
                supersedes_id="old",
            )
        )
        db.add(
            Obligation(
                id="v2old",
                case_id="a",
                root_id="v2old",
                origin="user_attested",
                terms="{}",
                sources="[]",
            )
        )
        db.flush()
        db.add(
            Obligation(
                id="v2new",
                case_id="a",
                root_id="v2old",
                predecessor_id="v2old",
                origin="user_attested",
                terms="{}",
                sources="[]",
            )
        )
        db.add(
            Intake(
                id="intake",
                owner_id="owner",
                case_id="a",
                provider="synthetic",
                event_id="event",
                message_hash="x" * 64,
                storage_key=ikey,
            )
        )
        db.add(IntakeAlias(digest="alias", owner_id="owner", case_id="a"))
        db.commit()
        assert cleanup_case(
            db, SimpleNamespace(case_id="a", owner_id="owner", id="delete-job")
        )["deleted"]
        db.commit()
        assert db.get(Case, "a") is None and db.get(Case, "b").owner_id == "other"
        assert (
            db.query(Commitment).count() == 0
            and db.query(Obligation).count() == 0
            and db.query(Intake).count() == 0
        )
        assert not list(tmp_path.glob("*.bin"))
