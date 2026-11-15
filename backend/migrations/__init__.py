"""Transactional, versioned, additive migrations for PostgreSQL and SQLite.

No implicit destructive downgrade: rollback uses an approved database backup.
"""

from datetime import datetime, timezone
from sqlalchemy import inspect, text

REVISIONS = {
    1: "account_aware_baseline",
    2: "platform_operation_draft_communication",
    3: "versioned_obligation_ledger",
    4: "durable_jobs_private_exports",
    5: "integration_custody_intake_privacy",
    6: "canonical_aggregate_opt_in",
    7: "provider_pairing",
    8: "short_lived_capture_capability",
    9: "private_push_devices",
    10: "intake_message_identity",
    11: "causal_event_order_and_future_job_timestamps",
}


def upgrade(engine):
    from backend.app.core.database import Base
    from backend.app import models
    from backend.app.models import platform

    with engine.connect() as conn:
        try:
            if conn.dialect.name == "postgresql":
                conn.execute(text("SELECT pg_advisory_xact_lock(7310492201)"))
            elif conn.dialect.name == "sqlite":
                conn.exec_driver_sql("BEGIN IMMEDIATE")
            else:
                raise RuntimeError("Unsupported migration database")
            conn.execute(
                text(
                    "CREATE TABLE IF NOT EXISTS bindr_schema_revisions (version INTEGER PRIMARY KEY, name VARCHAR(200) NOT NULL, applied_at VARCHAR(40) NOT NULL)"
                )
            )
            applied = dict(
                conn.execute(
                    text("SELECT version, name FROM bindr_schema_revisions")
                ).all()
            )
            if any(v not in REVISIONS or REVISIONS[v] != n for v, n in applied.items()):
                raise RuntimeError("Unknown database revision; refusing schema changes")
            if applied and set(applied) != set(range(1, max(applied) + 1)):
                raise RuntimeError(
                    "Noncontiguous database revisions; refusing schema changes"
                )
            if 1 not in applied:
                # Current account release is adopted, not recreated or reassigned.
                existing = inspect(conn).get_table_names()
                if "cases" in existing:
                    names = {c["name"] for c in inspect(conn).get_columns("cases")}
                    for name, ddl in {
                        "owner_id": "VARCHAR(100) NOT NULL DEFAULT 'legacy-unclaimed'",
                        "version": "INTEGER NOT NULL DEFAULT 1",
                        "resolution_note": "TEXT",
                        "resolved_at": "VARCHAR(50)",
                    }.items():
                        if name not in names:
                            conn.exec_driver_sql(
                                f"ALTER TABLE cases ADD COLUMN {name} {ddl}"
                            )
                tables = [
                    t
                    for t in Base.metadata.sorted_tables
                    if t.name
                    not in {
                        "platform_operations",
                        "capture_drafts",
                        "evidence_communication",
                        "obligations_v2",
                        "case_events_v2",
                        "proposals_v2",
                        "case_control_v2",
                        "platform_jobs",
                        "notification_preferences_v2",
                        "private_exports_v2",
                        "provider_connections_v2",
                        "oauth_states_v2",
                        "intake_aliases_v2",
                        "private_intake_v2",
                        "account_control_v2",
                        "aggregate_consent_v2",
                        "canonical_companies_v2",
                        "case_company_v2",
                        "provider_links_v2",
                        "capture_capabilities_v2",
                        "private_push_devices_v2",
                        "intake_message_identity_v2",
                    }
                ]
                Base.metadata.create_all(conn, tables=tables)
            if 2 not in applied:
                for model in [
                    platform.Operation,
                    platform.CaptureDraft,
                    platform.EvidenceCommunication,
                ]:
                    model.__table__.create(conn, checkfirst=True)
            if 3 not in applied:
                from backend.app.models.workflow import (
                    Obligation,
                    CaseEvent,
                    Proposal,
                    CaseControl,
                )

                for model in [Obligation, CaseEvent, Proposal, CaseControl]:
                    model.__table__.create(conn, checkfirst=True)
            if 4 not in applied:
                from backend.app.models.jobs import Job, NotificationPreferences, Export

                for model in [Job, NotificationPreferences, Export]:
                    model.__table__.create(conn, checkfirst=True)
            if 5 not in applied:
                from backend.app.models.integrations import (
                    Connection,
                    OAuthState,
                    IntakeAlias,
                    Intake,
                    AccountControl,
                    AggregateConsent,
                )

                for model in [
                    Connection,
                    OAuthState,
                    IntakeAlias,
                    Intake,
                    AccountControl,
                    AggregateConsent,
                ]:
                    model.__table__.create(conn, checkfirst=True)
            if 6 not in applied:
                from backend.app.models.aggregates import Company, CompanyAssignment

                for model in [Company, CompanyAssignment]:
                    model.__table__.create(conn, checkfirst=True)
            if 7 not in applied:
                from backend.app.models.integrations import ProviderLink

                ProviderLink.__table__.create(conn, checkfirst=True)
            if 8 not in applied:
                from backend.app.models.pairing import CaptureCapability

                CaptureCapability.__table__.create(conn, checkfirst=True)
            if 9 not in applied:
                from backend.app.models.devices import PushDevice

                PushDevice.__table__.create(conn, checkfirst=True)
            if 10 not in applied:
                from backend.app.models.integrations import MessageIdentity

                MessageIdentity.__table__.create(conn, checkfirst=True)
            if 11 not in applied:
                names = {c["name"] for c in inspect(conn).get_columns("case_events_v2")}
                for name in ["case_version", "sequence"]:
                    if name not in names:
                        conn.exec_driver_sql(
                            f"ALTER TABLE case_events_v2 ADD COLUMN {name} INTEGER"
                        )
                if conn.dialect.name == "postgresql":
                    conn.exec_driver_sql(
                        "ALTER TABLE platform_jobs ALTER COLUMN run_at TYPE BIGINT, ALTER COLUMN lease_until TYPE BIGINT"
                    )
                    conn.exec_driver_sql(
                        "ALTER TABLE private_exports_v2 ALTER COLUMN expires_at TYPE BIGINT"
                    )
            for version, name in REVISIONS.items():
                if version not in applied:
                    conn.execute(
                        text(
                            "INSERT INTO bindr_schema_revisions(version,name,applied_at) VALUES (:v,:n,:t)"
                        ),
                        {
                            "v": version,
                            "n": name,
                            "t": datetime.now(timezone.utc).isoformat(),
                        },
                    )
            conn.commit()
        except BaseException:
            conn.rollback()
            raise


def assert_current(engine):
    """Read-only deployment gate; schema changes belong to a separately approved migration job."""
    try:
        with engine.connect() as connection:
            applied = dict(
                connection.execute(
                    text("SELECT version,name FROM bindr_schema_revisions")
                ).all()
            )
        from backend.app.core.database import Base
        from backend.app import models

        inspector = inspect(engine)
        existing = set(inspector.get_table_names())
        if any(
            table.name not in existing
            or set(table.columns.keys())
            - {c["name"] for c in inspector.get_columns(table.name)}
            for table in Base.metadata.sorted_tables
        ):
            raise RuntimeError("Schema objects missing")
        if applied != REVISIONS:
            raise RuntimeError("Schema revision mismatch")
    except Exception:
        raise RuntimeError(
            "Apply and verify the versioned platform migrations before starting this revision."
        ) from None
    return max(REVISIONS)
