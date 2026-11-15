"""Optional RFC 3161 SHA-256 timestamp, verified by OpenSSL against an owner-pinned CA.

Only a digest and request nonce leave Bindr. A receipt does not prove authorship/truth.
"""

import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from urllib.parse import urlparse
import requests
from backend.app.services.case_state import fail


def configuration():
    url = os.getenv("TSA_URL", "")
    ca = os.getenv("TSA_CA_FILE", "")
    pin = os.getenv("TSA_CA_SHA256", "")
    parsed = urlparse(url)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or not ca
        or not Path(ca).is_file()
        or not shutil.which("openssl")
    ):
        fail(
            503,
            "PROVIDER_NOT_CONFIGURED",
            "A reviewed HTTPS timestamp authority and pinned CA file/OpenSSL are required.",
        )
    if not pin or hashlib.sha256(Path(ca).read_bytes()).hexdigest() != pin:
        fail(
            503, "PROVIDER_NOT_CONFIGURED", "Timestamp trust anchor pin does not match."
        )
    return url, ca


def openssl(*args):
    result = subprocess.run(
        ["openssl", *args], capture_output=True, timeout=15, check=False
    )
    if result.returncode:
        raise ValueError("Timestamp verification failed")
    return result.stdout


def verify(content, receipt, ca):
    with tempfile.TemporaryDirectory(prefix="bindr-ts-verify-") as directory:
        reply = Path(directory) / "response.tsr"
        reply.write_bytes(receipt)
        openssl(
            "ts",
            "-verify",
            "-digest",
            hashlib.sha256(content).hexdigest(),
            "-in",
            str(reply),
            "-CAfile",
            str(ca),
        )
    return True


def issue(content, http=requests):
    url, ca = configuration()
    with tempfile.TemporaryDirectory(prefix="bindr-ts-") as directory:
        query = Path(directory) / "request.tsq"
        reply = Path(directory) / "response.tsr"
        openssl(
            "ts",
            "-query",
            "-digest",
            hashlib.sha256(content).hexdigest(),
            "-sha256",
            "-cert",
            "-out",
            str(query),
        )
        headers = {"Content-Type": "application/timestamp-query"}
        authorization = os.getenv("TSA_AUTHORIZATION")
        if authorization:
            headers["Authorization"] = authorization
        response = http.post(
            url,
            data=query.read_bytes(),
            headers=headers,
            timeout=30,
            allow_redirects=False,
            stream=True,
        )
        from backend.app.services.platform.inbound import bounded_bytes

        receipt = bounded_bytes(response, 1024 * 1024)
        reply.write_bytes(receipt)
        openssl(
            "ts", "-verify", "-queryfile", str(query), "-in", str(reply), "-CAfile", ca
        )
    return receipt
