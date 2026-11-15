"""Dedicated-key authenticated encryption. Fail closed; never derive custody keys from auth secrets."""

import base64
import json
import os
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


def cipher():
    try:
        key = base64.b64decode(os.environ["CONNECTOR_ENCRYPTION_KEY"], validate=True)
        if len(key) != 32:
            raise ValueError()
        return AESGCM(key)
    except (KeyError, ValueError):
        raise RuntimeError(
            "A dedicated 32-byte connector encryption key is required"
        ) from None


def seal(owner, provider, value):
    nonce = os.urandom(12)
    ciphertext = cipher().encrypt(
        nonce,
        json.dumps(value, separators=(",", ":")).encode(),
        (owner + ":" + provider).encode(),
    )
    return base64.b64encode(nonce + ciphertext).decode()


def open_credential(owner, provider, token):
    data = base64.b64decode(token, validate=True)
    return json.loads(
        cipher().decrypt(data[:12], data[12:], (owner + ":" + provider).encode())
    )
