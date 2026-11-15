"""Explicit SQL worker invocation. Run once from an authenticated scheduler/service identity.

External sends require explicit reviewed/opted-in jobs plus disabled-by-default activation flags.
"""

import argparse
from backend.app.core.database import engine, SessionLocal
from backend.migrations import upgrade
from backend.app.services.platform.jobs import run_one
from backend.app.services.platform.exports import build, expire_exports
from backend.app.services.platform.deletion import cleanup_case
from backend.app.services.platform.reminders import deliver_prompt
from backend.app.services.platform.accounts import cleanup_account, export_account
from backend.app.services.platform.gmail import send_reviewed, poll_thread
from backend.app.services.platform.notifications import dispatch


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-jobs", type=int, default=20)
    args = parser.parse_args()
    if not 1 <= args.max_jobs <= 100:
        parser.error("max-jobs must be 1–100")
    from backend.app.core.auth import get_auth_secret
    from backend.app.core.config import settings

    get_auth_secret()
    if settings.ENVIRONMENT.lower() in {"production", "prod", "staging", "deployed"}:
        if (
            settings.AUTH_PROVIDER != "firebase"
            or settings.EVIDENCE_STORAGE_BACKEND != "gcs"
            or not settings.EVIDENCE_GCS_BUCKET
            or not settings.DATABASE_URL.startswith(
                ("postgres://", "postgresql://", "postgresql+psycopg://")
            )
        ):
            raise RuntimeError(
                "Deployed workers require Firebase, PostgreSQL, and private GCS configuration"
            )
    if settings.ENVIRONMENT.lower() in {"production", "prod", "staging", "deployed"}:
        from backend.migrations import assert_current

        assert_current(engine)
    else:
        upgrade(engine)
    with SessionLocal() as db:
        expire_exports(db)
    handlers = {
        "notification": dispatch,
        "send": send_reviewed,
        "gmail_poll": poll_thread,
        "account_export": export_account,
        "delete_account": cleanup_account,
        "export": build,
        "delete_case": cleanup_case,
        "reminder": deliver_prompt,
        "follow_up": deliver_prompt,
    }
    for _ in range(args.max_jobs):
        if run_one(SessionLocal, handlers) is None:
            break


if __name__ == "__main__":
    main()
