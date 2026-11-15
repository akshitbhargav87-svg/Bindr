"""Opt-in generic reminders; external dispatch disabled until owner configuration/acceptance."""

import json
import os
import re
import requests
from backend.app.models.account import Account
from backend.app.models.jobs import NotificationPreferences
from backend.app.models.devices import PushDevice
from backend.app.services.platform.accounts import ensure_active
from backend.app.services.platform.reminders import deliver_prompt
from backend.app.services.platform.credentials import open_credential
from backend.app.services.case_state import fail


def capabilities():
    enabled = os.getenv("NOTIFICATION_DELIVERY_ENABLED") == "true"
    return {
        "in_app": "available",
        "email": (
            "configured_not_live_verified"
            if enabled
            and os.getenv("RESEND_API_KEY")
            and os.getenv("NOTIFICATION_FROM")
            else "not_configured"
        ),
        "push": (
            "configured_not_live_verified"
            if enabled and os.getenv("FCM_DELIVERY_ENABLED") == "true"
            else "not_configured"
        ),
        "whatsapp": (
            "configured_not_live_verified"
            if enabled
            and all(
                os.getenv(k)
                for k in [
                    "WHATSAPP_ACCESS_TOKEN",
                    "WHATSAPP_GRAPH_VERSION",
                    "WHATSAPP_PHONE_NUMBER_ID",
                    "WHATSAPP_REMINDER_TEMPLATE",
                    "WHATSAPP_TEMPLATE_LANGUAGE",
                ]
            )
            else "not_configured"
        ),
    }


def dispatch(db, job, http=requests, push_sender=None):
    ensure_active(db, job.owner_id)
    context = deliver_prompt(db, job)
    payload = json.loads(job.payload)
    channel = payload["channel"]
    prefs = db.get(NotificationPreferences, job.owner_id)
    if not prefs or not json.loads(prefs.payload).get(channel):
        fail(409, "OBSOLETE_JOB", "Channel permission was withdrawn.")
    if os.getenv("NOTIFICATION_DELIVERY_ENABLED") != "true":
        fail(503, "PROVIDER_NOT_CONFIGURED", "External reminder delivery is disabled.")
    account = db.get(Account, job.owner_id)
    if account is None:
        fail(404, "NOT_FOUND", "Account no longer available.")
    # Fixed, generic content. No case title, evidence, payment amount, or third-party URL
    # appears on a lock screen/email without the user's authenticated case session.
    title = "Bindr reminder"
    text = "A confirmed deadline needs your review. Open Bindr to check the latest case details."
    if channel == "email":
        key = os.getenv("RESEND_API_KEY")
        sender = os.getenv("NOTIFICATION_FROM", "")
        if not key or "@" not in sender or "\n" in sender or "\r" in sender:
            fail(
                503,
                "PROVIDER_NOT_CONFIGURED",
                "A verified reminder email sender is required.",
            )
        response = http.post(
            "https://api.resend.com/emails",
            headers={"Authorization": "Bearer " + key, "Idempotency-Key": job.id},
            json={
                "from": sender,
                "to": [account.email],
                "subject": title,
                "text": text,
            },
            timeout=30,
            allow_redirects=False,
        )
        response.raise_for_status()
        receipt = response.json()
        if not receipt.get("id"):
            raise ValueError("Missing delivery receipt")
        return {
            "channel": "email",
            "provider_receipt": receipt["id"],
            "status": "accepted_by_provider_not_recipient_delivery",
            "case_version": job.case_version,
        }
    if channel == "push":
        if os.getenv("FCM_DELIVERY_ENABLED") != "true":
            fail(503, "PROVIDER_NOT_CONFIGURED", "Push delivery is disabled.")
        # One job per device is required; a multi-device send with uncertain partial
        # completion must never be retried as a group.
        device = (
            db.query(PushDevice)
            .filter_by(id=payload.get("device_id"), owner_id=job.owner_id, active=1)
            .first()
        )
        if device is None:
            fail(409, "OBSOLETE_JOB", "Push device is no longer registered.")
        token = open_credential(job.owner_id, "fcm", device.credential)["token"]
        if push_sender is None:
            from firebase_admin import messaging
            from backend.app.services.identity import get_identity_provider

            receipt = messaging.send(
                messaging.Message(
                    notification=messaging.Notification(title=title, body=text),
                    token=token,
                ),
                app=get_identity_provider().app,
            )
        else:
            receipt = push_sender(token, title, text)
        return {
            "channel": "push",
            "provider_receipt": receipt,
            "status": "accepted_by_provider_not_device_display",
            "case_version": job.case_version,
        }
    if channel == "whatsapp":
        from backend.app.models.integrations import Connection

        row = (
            db.query(Connection)
            .filter_by(owner_id=job.owner_id, provider="whatsapp", state="connected")
            .first()
        )
        version = os.getenv("WHATSAPP_GRAPH_VERSION", "")
        phone_id = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")
        token = os.getenv("WHATSAPP_ACCESS_TOKEN", "")
        template = os.getenv("WHATSAPP_REMINDER_TEMPLATE", "")
        language = os.getenv("WHATSAPP_TEMPLATE_LANGUAGE", "")
        if (
            row is None
            or not row.credential
            or not re.fullmatch(r"v[0-9]+\.[0-9]+", version)
            or not phone_id.isdigit()
            or not token
            or not re.fullmatch(r"[a-z0-9_]{1,100}", template)
            or not re.fullmatch(r"[a-z]{2}(?:_[A-Z]{2})?", language)
        ):
            fail(
                503,
                "PROVIDER_NOT_CONFIGURED",
                "A linked account and approved WhatsApp Business reminder template are required.",
            )
        phone = open_credential(job.owner_id, "whatsapp", row.credential)["phone"]
        response = http.post(
            "https://graph.facebook.com/" + version + "/" + phone_id + "/messages",
            headers={"Authorization": "Bearer " + token},
            json={
                "messaging_product": "whatsapp",
                "to": phone,
                "type": "template",
                "template": {"name": template, "language": {"code": language}},
            },
            timeout=30,
            allow_redirects=False,
        )
        response.raise_for_status()
        messages = response.json().get("messages", [])
        if not messages or not messages[0].get("id"):
            raise ValueError("Missing provider receipt")
        return {
            "channel": "whatsapp",
            "provider_receipt": messages[0]["id"],
            "status": "accepted_by_provider_not_delivery",
            "case_version": job.case_version,
        }
    fail(
        503,
        "PROVIDER_NOT_CONFIGURED",
        "This notification channel has no accepted configured transport.",
    )
