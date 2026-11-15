"""Provider-independent custody/intake plus fixed-origin Gmail OAuth transport."""

import base64
import hashlib
import json
import os
import secrets
import time
from urllib.parse import urlencode
import requests
from sqlalchemy import update
from sqlalchemy.exc import IntegrityError
from backend.app.models.integrations import Connection, OAuthState, IntakeAlias, Intake
from backend.app.models.jobs import Job
from backend.app.services.case_state import fail
from backend.app.services.platform.operations import canonical
from backend.app.services.platform.credentials import cipher, seal, open_credential
from backend.app.services.storage import storage_service

SCOPES = {
    "send": "https://www.googleapis.com/auth/gmail.send",
    "read": "https://www.googleapis.com/auth/gmail.readonly",
}


def gmail_config():
    values = {
        key: os.getenv("GMAIL_" + key, "")
        for key in ("CLIENT_ID", "CLIENT_SECRET", "REDIRECT_URI")
    }
    if not all(values.values()) or not values["REDIRECT_URI"].startswith("https://"):
        fail(
            503,
            "PROVIDER_NOT_CONFIGURED",
            "Gmail OAuth requires configured client, fixed HTTPS callback, and custody key.",
        )
    try:
        cipher()
    except RuntimeError:
        fail(503, "PROVIDER_NOT_CONFIGURED", "Connector custody is not configured.")
    return values


def begin_gmail(db, auth, capability):
    config = gmail_config()
    raw = secrets.token_urlsafe(32)
    verifier = secrets.token_urlsafe(48)
    scopes = (
        list(SCOPES.values()) if capability == "send_and_read" else [SCOPES[capability]]
    )
    db.add(
        OAuthState(
            digest=hashlib.sha256(raw.encode()).hexdigest(),
            owner_id=auth.user_id,
            session_id=auth.session_id,
            verifier=seal(auth.user_id, "gmail-state", {"verifier": verifier}),
            scopes=canonical(scopes),
            expires_at=int(time.time()) + 600,
        )
    )
    query = {
        "client_id": config["CLIENT_ID"],
        "redirect_uri": config["REDIRECT_URI"],
        "response_type": "code",
        "scope": " ".join(scopes),
        "access_type": "offline",
        "prompt": "consent",
        "state": raw,
        "code_challenge": base64.urlsafe_b64encode(
            hashlib.sha256(verifier.encode()).digest()
        )
        .decode()
        .rstrip("="),
        "code_challenge_method": "S256",
    }
    return {
        "authorization_url": "https://accounts.google.com/o/oauth2/v2/auth?"
        + urlencode(query),
        "expires_in": 600,
    }


def finish_gmail(db, auth, state, code, http=requests):
    config = gmail_config()
    digest = hashlib.sha256(state.encode()).hexdigest()
    row = db.get(OAuthState, digest)
    if (
        row is None
        or row.owner_id != auth.user_id
        or row.session_id != auth.session_id
        or row.used_at is not None
        or row.expires_at < int(time.time())
    ):
        fail(
            400,
            "INVALID_OAUTH_STATE",
            "OAuth state is expired, used, or belongs to another session.",
        )
    count = db.execute(
        update(OAuthState)
        .where(OAuthState.digest == digest, OAuthState.used_at.is_(None))
        .values(used_at=int(time.time())),
        execution_options={"synchronize_session": False},
    ).rowcount
    if count != 1:
        fail(400, "INVALID_OAUTH_STATE", "OAuth state was already consumed.")
    verifier = open_credential(auth.user_id, "gmail-state", row.verifier)["verifier"]
    scopes = json.loads(row.scopes)
    db.commit()  # Consume before contacting provider; uncertain callbacks require a new handshake.
    try:
        response = http.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": config["CLIENT_ID"],
                "client_secret": config["CLIENT_SECRET"],
                "redirect_uri": config["REDIRECT_URI"],
                "grant_type": "authorization_code",
                "code": code,
                "code_verifier": verifier,
            },
            timeout=30,
            allow_redirects=False,
        )
        response.raise_for_status()
        tokens = response.json()
        granted = tokens.get("scope", "").split()
        if not tokens.get("refresh_token") or not set(scopes) <= set(granted):
            raise ValueError("Incomplete grant")
    except Exception:
        fail(
            502,
            "OAUTH_EXCHANGE_FAILED",
            "Could not complete Gmail connection. Start a new connection attempt.",
        )
    connection = (
        db.query(Connection).filter_by(owner_id=auth.user_id, provider="gmail").first()
    )
    if connection is None:
        connection = Connection(owner_id=auth.user_id, provider="gmail", generation=1)
        db.add(connection)
    else:
        connection.generation += 1
    connection.credential = seal(
        auth.user_id, "gmail", {"refresh_token": tokens["refresh_token"]}
    )
    connection.scopes = canonical(scopes)
    connection.state = "connected"
    db.commit()
    return {
        "state": "connected",
        "capabilities": {
            "send": SCOPES["send"] in scopes,
            "read": SCOPES["read"] in scopes,
        },
        "live_acceptance": False,
    }


def revoke_gmail(db, owner, http=requests):
    row = db.query(Connection).filter_by(owner_id=owner, provider="gmail").first()
    remote = "not_connected"
    if row and row.credential:
        try:
            token = open_credential(owner, "gmail", row.credential)["refresh_token"]
            response = http.post(
                "https://oauth2.googleapis.com/revoke",
                data={"token": token},
                timeout=20,
                allow_redirects=False,
            )
            response.raise_for_status()
            remote = "revoked"
        except Exception:
            remote = "unconfirmed_retry_at_google_account_permissions"
        row.credential = None
        row.state = "disconnected"
        row.generation += 1
    db.query(Job).filter(
        Job.owner_id == owner,
        Job.kind.in_(["send", "gmail_poll"]),
        Job.state.in_(["queued", "running"]),
    ).update({"state": "cancelled", "payload": "{}"}, synchronize_session=False)
    return {"state": "disconnected", "remote_revocation": remote}


def receive(db, alias_token, provider, event_id, original, alias_override=None):
    """Call ONLY after the adapter verifies provider signature and replay freshness.

    Alias possession never supplies read permissions; content is always unconfirmed intake.
    """
    alias = alias_override or db.get(
        IntakeAlias, hashlib.sha256(alias_token.encode()).hexdigest()
    )
    if alias is None or alias.revoked_at is not None:
        fail(404, "NOT_FOUND", "Intake destination not found.")
    from backend.app.services.platform.accounts import ensure_active

    ensure_active(db, alias.owner_id)
    if alias.case_id:
        from backend.app.services.platform.workflow import owned_case

        owned_case(db, alias.owner_id, alias.case_id)
    if not original or len(original) > 10 * 1024 * 1024:
        fail(413, "FILE_TOO_LARGE", "Intake exceeds limits.")
    if not isinstance(event_id, str) or not event_id or len(event_id) > 200:
        fail(422, "VALIDATION_ERROR", "Invalid provider event ID.")
    digest = hashlib.sha256(original).hexdigest()
    message_identity = None
    body_hash = None
    if provider in ("gmail", "resend"):
        from email.parser import BytesHeaderParser
        import re

        header, separator, content = original.partition(b"\r\n\r\n")
        if not separator:
            header, separator, content = original.partition(b"\n\n")
        if len(header) > 65536:
            fail(413, "HEADER_LIMIT", "Email headers exceed intake limits.")
        message_id = (
            BytesHeaderParser().parsebytes(header).get("Message-ID", "").strip()
        )
        if re.fullmatch(r"<[^<>\s]{1,300}>", message_id):
            message_identity = hashlib.sha256(message_id.encode()).hexdigest()
            body_hash = hashlib.sha256(content).hexdigest()
    if db.bind.dialect.name == "postgresql":
        from sqlalchemy import text

        lock = int.from_bytes(
            hashlib.sha256(
                (
                    alias.owner_id
                    + ":"
                    + str(alias.case_id)
                    + ":"
                    + (message_identity or digest)
                ).encode()
            ).digest()[:8],
            "big",
            signed=True,
        )
        db.execute(text("SELECT pg_advisory_xact_lock(:lock)"), {"lock": lock})
    from backend.app.models.integrations import MessageIdentity

    identity_key = (alias.owner_id, alias.case_id or "account-inbox", message_identity)
    if message_identity:
        previous = db.get(MessageIdentity, identity_key)
        if previous:
            if previous.body_hash != body_hash:
                fail(
                    409,
                    "MESSAGE_ID_CONFLICT",
                    "Message ID was reused with different content; review the provider original.",
                )
            return {
                "intake_id": previous.intake_id,
                "duplicate": True,
                "state": "review_required",
                "original_reference_preserved": True,
            }
    existing = db.query(Intake).filter_by(provider=provider, event_id=event_id).first()
    if existing:
        if existing.owner_id != alias.owner_id or existing.message_hash != digest:
            fail(409, "EVENT_CONFLICT", "Provider event identity was reused.")
        return {"intake_id": existing.id, "duplicate": True, "state": existing.state}
    existing = (
        db.query(Intake)
        .filter_by(owner_id=alias.owner_id, case_id=alias.case_id, message_hash=digest)
        .first()
    )
    if existing:
        return {"intake_id": existing.id, "duplicate": True, "state": existing.state}
    from backend.app.models.workflow import identity

    iid = identity()
    key, _, _ = storage_service.save_file(original, iid)
    row = Intake(
        id=iid,
        owner_id=alias.owner_id,
        case_id=alias.case_id,
        provider=provider,
        event_id=event_id,
        message_hash=digest,
        storage_key=key,
    )
    try:
        with db.begin_nested():
            db.add(row)
            db.flush()
    except IntegrityError:
        storage_service.delete_file(key)
        existing = (
            db.query(Intake)
            .filter_by(
                owner_id=alias.owner_id, case_id=alias.case_id, message_hash=digest
            )
            .first()
        )
        if existing:
            return {
                "intake_id": existing.id,
                "duplicate": True,
                "state": existing.state,
            }
        fail(409, "EVENT_CONFLICT", "Concurrent provider event conflict.")
    if message_identity:
        db.add(
            MessageIdentity(
                owner_id=alias.owner_id,
                case_scope=alias.case_id or "account-inbox",
                message_digest=message_identity,
                body_hash=body_hash,
                intake_id=row.id,
            )
        )
        db.flush()
    if alias.case_id:
        db.query(Job).filter(
            Job.case_id == alias.case_id,
            Job.kind == "follow_up",
            Job.state.in_(["queued", "running"]),
        ).update(
            {"state": "cancelled", "stage": "reply_received"}, synchronize_session=False
        )
    return {"intake_id": row.id, "duplicate": False, "state": "review_required"}
