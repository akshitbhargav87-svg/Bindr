"""Signature verification is separate from authorization/routing. No evidence content is executed."""

import base64
import hashlib
import hmac
import json
import time
from backend.app.services.case_state import fail


def verify_svix(raw, headers, secret, now=None):
    try:
        timestamp = headers["svix-timestamp"]
        eid = headers["svix-id"]
        if (
            len(eid) > 200
            or abs((int(time.time()) if now is None else now) - int(timestamp)) > 300
        ):
            raise ValueError()
        key = base64.b64decode(secret.removeprefix("whsec_"), validate=True)
        if len(key) < 32:
            raise ValueError()
        expected = base64.b64encode(
            hmac.new(
                key,
                eid.encode() + b"." + timestamp.encode() + b"." + raw,
                hashlib.sha256,
            ).digest()
        ).decode()
        valid = any(
            part.startswith("v1,") and hmac.compare_digest(part[3:], expected)
            for part in headers["svix-signature"].split()
        )
        if not valid:
            raise ValueError()
        return json.loads(raw)
    except Exception:
        fail(
            403, "INVALID_WEBHOOK_SIGNATURE", "Webhook signature is invalid or expired."
        )


def verify_meta(raw, signature, secret):
    if (
        not secret
        or len(secret) < 32
        or not isinstance(signature, str)
        or not hmac.compare_digest(
            signature,
            "sha256=" + hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest(),
        )
    ):
        fail(403, "INVALID_WEBHOOK_SIGNATURE", "Webhook signature is invalid.")
    try:
        return json.loads(raw)
    except ValueError:
        fail(422, "VALIDATION_ERROR", "Invalid webhook body.")
