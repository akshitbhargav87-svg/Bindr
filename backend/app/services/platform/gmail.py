"""Fixed-origin Gmail transport. Dispatch runs only after explicit reviewed-send activation."""

import base64
import hashlib
import json
import os
from email.message import EmailMessage
import requests
from backend.app.models.integrations import Connection
from backend.app.services.platform.credentials import open_credential
from backend.app.services.platform.connectors import gmail_config, SCOPES, receive
from backend.app.services.platform.workflow import owned_case, sources
from backend.app.services.storage import storage_service
from backend.app.services.case_state import fail


def connection(db, owner, capability, generation=None):
    row = (
        db.query(Connection)
        .filter_by(owner_id=owner, provider="gmail", state="connected")
        .first()
    )
    if (
        row is None
        or not row.credential
        or SCOPES[capability] not in json.loads(row.scopes)
        or (generation is not None and row.generation != generation)
    ):
        fail(
            409,
            "CONNECTOR_UNAVAILABLE",
            "Reconnect Gmail with the required capability.",
        )
    return row


def access_token(row, http):
    config = gmail_config()
    secret = open_credential(row.owner_id, "gmail", row.credential)
    response = http.post(
        "https://oauth2.googleapis.com/token",
        data={
            "client_id": config["CLIENT_ID"],
            "client_secret": config["CLIENT_SECRET"],
            "grant_type": "refresh_token",
            "refresh_token": secret["refresh_token"],
        },
        timeout=20,
        allow_redirects=False,
    )
    response.raise_for_status()
    token = response.json()["access_token"]
    if not isinstance(token, str) or not token:
        raise ValueError("Invalid access grant")
    return token


def send_reviewed(db, job, http=requests):
    if os.getenv("GMAIL_REVIEWED_SEND_ENABLED") != "true":
        fail(503, "PROVIDER_NOT_CONFIGURED", "Reviewed sending has not been activated.")
    case = owned_case(db, job.owner_id, job.case_id)
    if case.version != job.case_version:
        fail(409, "VERSION_CONFLICT", "Facts changed before sending.")
    body = json.loads(job.payload)
    row = connection(db, job.owner_id, "send", body["connection_generation"])
    attachments = sources(db, case.id, body["source_ids"])
    message = EmailMessage()
    message["To"] = body["recipient"]
    message["Subject"] = body["subject"]
    # Stable RFC Message-ID enables reconciliation after an uncertain provider response.
    message["Message-ID"] = "<" + job.id + "@bindr.invalid>"
    message.set_content(body["body"])
    for evidence in attachments:
        content = storage_service.read_file(evidence.storage_key)
        if hashlib.sha256(content).hexdigest() != evidence.sha256:
            fail(409, "INTEGRITY_ERROR", "An attachment digest changed.")
        main, sub = evidence.media_type.split("/", 1)
        message.add_attachment(
            content, maintype=main, subtype=sub, filename=evidence.filename
        )
    encoded = base64.urlsafe_b64encode(message.as_bytes()).decode()
    if len(encoded) > 20 * 1024 * 1024:
        fail(
            413,
            "FILE_TOO_LARGE",
            "Reviewed correspondence exceeds the transport limit.",
        )
    token = access_token(row, http)
    response = http.post(
        "https://gmail.googleapis.com/gmail/v1/users/me/messages/send",
        headers={"Authorization": "Bearer " + token},
        json={"raw": encoded},
        timeout=30,
        allow_redirects=False,
    )
    response.raise_for_status()
    receipt = response.json()
    if not receipt.get("id"):
        raise ValueError("Provider response lacked receipt")
    poll_id = None
    if body.get("receive_replies") and receipt.get("threadId"):
        from backend.app.models.integrations import IntakeAlias
        from backend.app.services.platform.jobs import enqueue
        import secrets, time

        digest = hashlib.sha256(secrets.token_bytes(32)).hexdigest()
        db.add(IntakeAlias(digest=digest, owner_id=job.owner_id, case_id=case.id))
        db.flush()
        poll = enqueue(
            db,
            job.owner_id,
            "gmail_poll",
            {
                "connection_generation": row.generation,
                "thread_id": receipt["threadId"],
                "seen_ids": [receipt["id"]],
                "alias_digest": digest,
                "round": 0,
            },
            case.id,
            case.version,
            int(time.time()) + 60,
        )
        poll_id = poll.id
    return {
        "reply_poll_job_id": poll_id,
        "provider": "gmail",
        "provider_message_id": receipt["id"],
        "thread_id": receipt.get("threadId"),
        "rfc_message_id": str(message["Message-ID"]),
        "classification": "user_correspondence_not_company_evidence",
        "delivery_status": "accepted_by_provider_not_proof_of_recipient_delivery",
    }


def import_message(db, owner, message_id, alias_token, http=requests):
    row = connection(db, owner, "read")
    token = access_token(row, http)
    # IDs are validated by the HTTP schema; never accept a user URL/Google resource owner.
    response = http.get(
        "https://gmail.googleapis.com/gmail/v1/users/me/messages/" + message_id,
        params={"format": "raw"},
        headers={"Authorization": "Bearer " + token},
        timeout=30,
        allow_redirects=False,
    )
    response.raise_for_status()
    body = response.json()
    raw = body.get("raw", "")
    if len(raw) > 14 * 1024 * 1024:
        fail(413, "FILE_TOO_LARGE", "Message exceeds intake limits.")
    original = base64.urlsafe_b64decode(raw + "=" * ((4 - len(raw) % 4) % 4))
    # Exact original MIME digest deduplicates an identical forwarding/import path.
    import hashlib
    from backend.app.models.integrations import IntakeAlias

    alias = db.get(IntakeAlias, hashlib.sha256(alias_token.encode()).hexdigest())
    if alias is None or alias.owner_id != owner:
        fail(404, "NOT_FOUND", "Intake destination not found.")
    return receive(db, alias_token, "gmail", owner + ":" + body["id"], original)


def poll_thread(db, job, http=requests):
    """Bounded hourly polling of the explicitly reviewed thread, never the whole inbox."""
    import re, time
    from backend.app.models.integrations import IntakeAlias
    from backend.app.services.platform.jobs import enqueue

    case = owned_case(db, job.owner_id, job.case_id)
    if case.version != job.case_version:
        fail(409, "VERSION_CONFLICT", "Reply polling requires current case review.")
    body = json.loads(job.payload)
    row = connection(db, job.owner_id, "read", body["connection_generation"])
    alias = db.get(IntakeAlias, body["alias_digest"])
    if alias is None or alias.owner_id != job.owner_id or alias.revoked_at is not None:
        fail(409, "CONNECTOR_UNAVAILABLE", "Reply intake was disconnected.")
    tid = body["thread_id"]
    if not isinstance(tid, str) or not re.fullmatch(r"[a-zA-Z0-9_-]{1,200}", tid):
        raise ValueError("Invalid thread receipt")
    token = access_token(row, http)
    headers = {"Authorization": "Bearer " + token}
    response = http.get(
        "https://gmail.googleapis.com/gmail/v1/users/me/threads/" + tid,
        params={"format": "minimal"},
        headers=headers,
        timeout=30,
        allow_redirects=False,
    )
    response.raise_for_status()
    messages = response.json().get("messages", [])
    if not isinstance(messages, list) or len(messages) > 100:
        fail(413, "THREAD_LIMIT", "Thread exceeds the bounded reply intake limit.")
    seen = set(body["seen_ids"])
    imported = []
    for message in messages:
        mid = message.get("id", "")
        if mid in seen or "SENT" in message.get("labelIds", []):
            continue
        if not isinstance(mid, str) or not re.fullmatch(r"[a-zA-Z0-9_-]{1,150}", mid):
            raise ValueError("Invalid message receipt")
        response = http.get(
            "https://gmail.googleapis.com/gmail/v1/users/me/messages/" + mid,
            params={"format": "raw"},
            headers=headers,
            timeout=30,
            allow_redirects=False,
        )
        response.raise_for_status()
        raw = response.json().get("raw", "")
        if len(raw) > 14 * 1024 * 1024:
            fail(413, "FILE_TOO_LARGE", "Reply exceeds intake limits.")
        original = base64.urlsafe_b64decode(raw + "=" * ((4 - len(raw) % 4) % 4))
        imported.append(
            receive(
                db,
                "",
                "gmail",
                job.owner_id + ":" + mid,
                original,
                alias_override=alias,
            )
        )
        seen.add(mid)
    if not imported and body["round"] < 23:
        enqueue(
            db,
            job.owner_id,
            "gmail_poll",
            {**body, "seen_ids": sorted(seen), "round": body["round"] + 1},
            case.id,
            case.version,
            int(time.time()) + 3600,
        )
    return {
        "intake": imported,
        "scope": "reviewed_thread_only",
        "polling_complete": bool(imported) or body["round"] >= 23,
        "max_rounds": 24,
    }
