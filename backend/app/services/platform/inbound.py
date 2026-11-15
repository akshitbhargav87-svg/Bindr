"""Configured provider adapters. Live provider setup/acceptance is still separate from these tests."""

import hashlib
import hmac
import json
import os
import time
import uuid
from urllib.parse import urlparse
from email.utils import parseaddr
import requests
from backend.app.models.integrations import IntakeAlias, ProviderLink, Intake
from backend.app.services.platform.connectors import receive
from backend.app.services.case_state import fail


def bounded_bytes(response, limit=10 * 1024 * 1024):
    response.raise_for_status()
    chunks = []
    size = 0
    try:
        for chunk in response.iter_content(65536):
            size += len(chunk)
            if size > limit:
                fail(413, "FILE_TOO_LARGE", "Provider source exceeds intake limits.")
            chunks.append(chunk)
    finally:
        response.close()
    return b"".join(chunks)


def resend(db, payload, http=requests):
    if not isinstance(payload, dict) or not isinstance(payload.get("data"), dict):
        fail(422, "VALIDATION_ERROR", "Invalid inbound event schema.")
    if payload.get("type") != "email.received":
        return {"accepted": False, "reason": "unsupported_event"}
    key = os.getenv("RESEND_API_KEY")
    domain = os.getenv("INBOUND_EMAIL_DOMAIN")
    hosts = os.getenv("RESEND_RAW_HOSTS", "").split(",")
    if not key or not domain or not any(hosts):
        fail(
            503,
            "PROVIDER_NOT_CONFIGURED",
            "Inbound email requires a verified receiving domain and raw-download host allowlist.",
        )
    data = payload.get("data", {})
    try:
        eid = str(uuid.UUID(data["email_id"]))
    except (KeyError, ValueError, TypeError):
        fail(422, "VALIDATION_ERROR", "Invalid receiving event.")
    destinations = []
    addresses = data.get("to", [])
    if (
        not isinstance(addresses, list)
        or len(addresses) > 20
        or any(not isinstance(a, str) for a in addresses)
    ):
        fail(422, "VALIDATION_ERROR", "Invalid intake recipients.")
    for address in addresses:
        _, parsed = parseaddr(address)
        local, sep, host = parsed.rpartition("@")
        if sep and host.lower() == domain.lower() and len(local) >= 20:
            alias = db.get(IntakeAlias, hashlib.sha256(local.encode()).hexdigest())
            if alias and alias.revoked_at is None:
                destinations.append((local, alias))
    if len(destinations) != 1:
        fail(
            422,
            "UNMATCHED_INTAKE",
            "A single active intake destination is required; message needs quarantine review.",
        )
    token, alias = destinations[0]
    if alias.case_id:
        from backend.app.services.platform.workflow import owned_case

        owned_case(db, alias.owner_id, alias.case_id)
    response = http.get(
        "https://api.resend.com/emails/receiving/" + eid,
        headers={"Authorization": "Bearer " + key},
        timeout=20,
        allow_redirects=False,
    )
    details = json.loads(bounded_bytes(response, 2 * 1024 * 1024))
    url = (details.get("raw") or {}).get("download_url", "")
    parsed = urlparse(url)
    if (
        parsed.scheme != "https"
        or parsed.hostname not in hosts
        or parsed.port not in (None, 443)
        or parsed.username
        or parsed.password
    ):
        fail(
            502, "UNSAFE_PROVIDER_RESOURCE", "Raw email download host is not approved."
        )
    # The signed URL goes only to the allowlisted provider host, without our API credential.
    raw = bounded_bytes(http.get(url, timeout=30, allow_redirects=False, stream=True))
    return receive(db, token, "resend", eid, raw)


def whatsapp(db, payload, raw):
    if (
        not isinstance(payload, dict)
        or not isinstance(payload.get("entry"), list)
        or len(payload["entry"]) > 10
    ):
        fail(422, "VALIDATION_ERROR", "Invalid WhatsApp event schema.")
    phone_id = os.getenv("WHATSAPP_PHONE_NUMBER_ID")
    secret = os.getenv("WHATSAPP_LINK_SECRET", "")
    if not phone_id or len(secret) < 32:
        fail(
            503,
            "PROVIDER_NOT_CONFIGURED",
            "WhatsApp Business linking is not configured.",
        )
    accepted = []
    for entry in payload.get("entry", []):
        if (
            not isinstance(entry, dict)
            or not isinstance(entry.get("changes"), list)
            or len(entry["changes"]) > 10
        ):
            fail(422, "VALIDATION_ERROR", "Invalid WhatsApp change schema.")
        for change in entry.get("changes", []):
            if not isinstance(change, dict) or not isinstance(
                change.get("value"), dict
            ):
                fail(422, "VALIDATION_ERROR", "Invalid WhatsApp change schema.")
            value = change.get("value", {})
            if not isinstance(value.get("metadata", {}), dict):
                fail(422, "VALIDATION_ERROR", "Invalid WhatsApp metadata.")
            if value.get("metadata", {}).get("phone_number_id") != phone_id:
                continue
            messages = value.get("messages", [])
            if not isinstance(messages, list) or len(messages) > 10:
                fail(422, "VALIDATION_ERROR", "Invalid WhatsApp message list.")
            for message in messages:
                if not isinstance(message, dict):
                    fail(422, "VALIDATION_ERROR", "Invalid WhatsApp message schema.")
                sender = message.get("from", "")
                if (
                    not isinstance(sender, str)
                    or not sender.isdigit()
                    or not 6 <= len(sender) <= 20
                ):
                    fail(422, "VALIDATION_ERROR", "Invalid linked sender.")
                digest = hmac.new(
                    secret.encode(), sender.encode(), hashlib.sha256
                ).hexdigest()
                if not isinstance(message.get("text", {}), dict):
                    fail(422, "VALIDATION_ERROR", "Invalid WhatsApp text.")
                text = message.get("text", {}).get("body", "")
                if not isinstance(text, str) or len(text) > 50000:
                    fail(422, "VALIDATION_ERROR", "Invalid WhatsApp text.")
                if text.startswith("BINDR "):
                    token = text[6:].strip()
                    alias = db.get(
                        IntakeAlias, hashlib.sha256(token.encode()).hexdigest()
                    )
                    if alias is None or alias.revoked_at is not None:
                        fail(404, "NOT_FOUND", "Pairing destination not found.")
                    # Pairing consumes the alias for this sender; the token remains inaccessible
                    # to anyone without the verified webhook/account session.
                    existing = db.get(ProviderLink, ("whatsapp", digest))
                    if existing and existing.owner_id != alias.owner_id:
                        fail(
                            409,
                            "LINK_CONFLICT",
                            "Disconnect the current account link before pairing again.",
                        )
                    if existing:
                        existing.alias_digest = alias.digest
                    else:
                        db.add(
                            ProviderLink(
                                provider="whatsapp",
                                remote_digest=digest,
                                owner_id=alias.owner_id,
                                alias_digest=alias.digest,
                            )
                        )
                    from backend.app.services.platform.credentials import seal
                    from backend.app.models.integrations import Connection

                    if os.getenv("CONNECTOR_ENCRYPTION_KEY"):
                        connection = (
                            db.query(Connection)
                            .filter_by(owner_id=alias.owner_id, provider="whatsapp")
                            .first()
                        )
                        if connection is None:
                            connection = Connection(
                                owner_id=alias.owner_id,
                                provider="whatsapp",
                                generation=1,
                            )
                            db.add(connection)
                        else:
                            connection.generation += 1
                        connection.state = "connected"
                        connection.scopes = '["receive"]'
                        connection.credential = seal(
                            alias.owner_id, "whatsapp", {"phone": sender}
                        )
                    accepted.append({"state": "linked"})
                    continue
                link = db.get(ProviderLink, ("whatsapp", digest))
                alias = db.get(IntakeAlias, link.alias_digest) if link else None
                if alias is None or alias.revoked_at is not None:
                    fail(
                        404,
                        "NOT_FOUND",
                        "Sender is not linked to an active intake destination.",
                    )
                # receive() accepts a token, whereas only a digest is retained here. Route the
                # verified link using an ephemeral token/digest pair, never expose case access.
                import secrets

                ephemeral = secrets.token_urlsafe(32)
                temporary = IntakeAlias(
                    digest=hashlib.sha256(ephemeral.encode()).hexdigest(),
                    owner_id=alias.owner_id,
                    case_id=alias.case_id,
                )
                db.add(temporary)
                db.flush()
                try:
                    # A webhook batch may contain several accounts. Preserve only this
                    # sender's derived record, never another account's raw envelope.
                    from backend.app.services.platform.operations import canonical

                    isolated = canonical(
                        {
                            "provider": "whatsapp",
                            "message": message,
                            "transport_signature_verified": True,
                            "original_media_included": False,
                        }
                    ).encode()
                    result = receive(
                        db, ephemeral, "whatsapp", message.get("id", ""), isolated
                    )
                    item = db.get(Intake, result["intake_id"])
                    if message.get("type") != "text":
                        item.state = "manual_attachment_required"
                        result["state"] = item.state
                    accepted.append(result)
                finally:
                    db.delete(temporary)
    return {"items": accepted, "personal_inbox_access": False}
