"""Synthetic local CA / stubbed transports; never real provider delivery acceptance."""

import base64
import hashlib
import json
import subprocess
import pytest
from pathlib import Path
from backend.app.services.platform.timestamps import issue, verify
from backend.app.services.platform.operations import canonical
from backend.app.models.account import Account
from backend.app.models.jobs import Job, NotificationPreferences
from backend.app.models.case import Case
from backend.app.models.workflow import Obligation
from backend.app.services.platform.notifications import dispatch


def test_rfc3161_checks_chain_nonce_and_digest(tmp_path, monkeypatch):
    def run(*args):
        subprocess.run(
            ["openssl", *args],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=15,
        )

    ca = tmp_path / "ca.pem"
    cakey = tmp_path / "ca.key"
    tsa = tmp_path / "tsa.pem"
    tsakey = tmp_path / "tsa.key"
    csr = tmp_path / "tsa.csr"
    run(
        "req",
        "-x509",
        "-newkey",
        "rsa:2048",
        "-nodes",
        "-keyout",
        str(cakey),
        "-out",
        str(ca),
        "-subj",
        "/CN=Bindr synthetic test CA",
        "-days",
        "2",
        "-addext",
        "basicConstraints=critical,CA:TRUE",
    )
    run(
        "req",
        "-newkey",
        "rsa:2048",
        "-nodes",
        "-keyout",
        str(tsakey),
        "-out",
        str(csr),
        "-subj",
        "/CN=Bindr synthetic test TSA",
    )
    extensions = tmp_path / "extensions"
    extensions.write_text(
        "basicConstraints=critical,CA:FALSE\nkeyUsage=critical,digitalSignature\nextendedKeyUsage=critical,timeStamping\n"
    )
    run(
        "x509",
        "-req",
        "-in",
        str(csr),
        "-CA",
        str(ca),
        "-CAkey",
        str(cakey),
        "-CAcreateserial",
        "-out",
        str(tsa),
        "-days",
        "2",
        "-extfile",
        str(extensions),
    )
    serial = tmp_path / "serial"
    serial.write_text("01")
    config = tmp_path / "tsa.cnf"
    config.write_text(
        f"""[tsa]
default_tsa=config
[config]
serial={serial.as_posix()}
signer_cert={tsa.as_posix()}
certs={ca.as_posix()}
signer_key={tsakey.as_posix()}
signer_digest=sha256
default_policy=1.2.3.4.1
digests=sha256
accuracy=secs:1
ordering=yes
tsa_name=yes
ess_cert_id_chain=yes
ess_cert_id_alg=sha256
"""
    )
    monkeypatch.setenv("TSA_URL", "https://synthetic-tsa.example.test")
    monkeypatch.setenv("TSA_CA_FILE", str(ca))
    monkeypatch.setenv("TSA_CA_SHA256", hashlib.sha256(ca.read_bytes()).hexdigest())

    class HTTP:
        @staticmethod
        def post(url, **kwargs):
            assert (
                url == "https://synthetic-tsa.example.test"
                and kwargs["allow_redirects"] is False
            )
            query = tmp_path / "request.tsq"
            query.write_bytes(kwargs["data"])
            reply = tmp_path / "response.tsr"
            run(
                "ts",
                "-reply",
                "-config",
                str(config),
                "-queryfile",
                str(query),
                "-out",
                str(reply),
            )

            class Response:
                def raise_for_status(self):
                    pass

                def iter_content(self, size):
                    yield reply.read_bytes()

                def close(self):
                    pass

            return Response()

    content = b"Synthetic immutable snapshot"
    receipt = issue(content, HTTP)
    assert verify(content, receipt, ca) is True
    with pytest.raises(ValueError):
        verify(content + b" altered", receipt, ca)
    with pytest.raises(ValueError):
        verify(content, b"forged receipt", ca)


def test_notification_opt_in_and_activation_gate_and_generic_payload(
    db_session, monkeypatch
):
    owner = "synthetic-account"
    case = Case(
        id="case",
        owner_id=owner,
        title="PRIVATE TITLE",
        merchant_name="Example",
        version=2,
    )
    db_session.add(
        Account(
            id=owner,
            provider_uid="synthetic",
            email="synthetic@example.test",
            created_at=1,
        )
    )
    db_session.add(case)
    db_session.flush()
    db_session.add(
        Obligation(
            id="promise",
            root_id="promise",
            case_id="case",
            state="active",
            origin="user_attested",
            sources="[]",
            terms=canonical(
                {
                    "kind": "refund",
                    "description": "PRIVATE SOURCE",
                    "amount_minor": 50000,
                    "currency": "INR",
                    "due_at": "2099-12-01T00:00:00Z",
                }
            ),
        )
    )
    prefs = NotificationPreferences(
        owner_id=owner,
        version=1,
        payload=canonical({"email": True, "in_app": False, "days_before": [0]}),
    )
    db_session.add(prefs)
    job = Job(
        owner_id=owner,
        kind="notification",
        case_id="case",
        case_version=2,
        run_at=1,
        payload=canonical(
            {"obligation_id": "promise", "preferences_version": 1, "channel": "email"}
        ),
    )
    db_session.add(job)
    db_session.flush()
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc:
        dispatch(db_session, job)
    assert exc.value.status_code == 503
    monkeypatch.setenv("NOTIFICATION_DELIVERY_ENABLED", "true")
    monkeypatch.setenv("RESEND_API_KEY", "synthetic-only-key")
    monkeypatch.setenv("NOTIFICATION_FROM", "verified@example.test")

    class HTTP:
        calls = 0

        @classmethod
        def post(cls, url, **kwargs):
            cls.calls += 1
            assert url == "https://api.resend.com/emails"
            assert kwargs["json"]["to"] == ["synthetic@example.test"]
            assert "PRIVATE" not in json.dumps(kwargs["json"])
            assert kwargs["headers"]["Idempotency-Key"] == job.id

            class Response:
                def raise_for_status(self):
                    pass

                def json(self):
                    return {"id": "synthetic-provider-receipt"}

            return Response()

    assert (
        dispatch(db_session, job, HTTP)["status"]
        == "accepted_by_provider_not_recipient_delivery"
    )
    prefs.payload = canonical({"email": False})
    db_session.flush()
    with pytest.raises(HTTPException):
        dispatch(db_session, job, HTTP)
    assert HTTP.calls == 1
