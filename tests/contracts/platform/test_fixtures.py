"""Checks protect provenance and user-visible financial/privacy semantics in exchanged fixtures."""

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def canonical_pack_sha256(raw: bytes) -> str:
    """Hash the historically archived CRLF text identically on Linux/Windows.

    The frozen QA manifest was computed from the original CRLF file. Git
    normalizes that Markdown file to LF when checking it out on Linux. Only
    the transport newline convention may change: other content must still
    match the pinned digest, and unsupported bare CR characters are rejected.
    """
    lf = raw.replace(b"\r\n", b"\n")
    if b"\r" in lf:
        raise ValueError("The canonical QA source contains unsupported carriage returns")
    return hashlib.sha256(lf.replace(b"\n", b"\r\n")).hexdigest()


def test_canonical_pack_is_preserved_and_1b_is_labeled_authored():
    manifest = json.loads(
        (Path(__file__).with_name("canonical_inputs.json")).read_text()
    )
    source = ROOT / manifest["source"]
    assert canonical_pack_sha256(source.read_bytes()) == manifest["source_sha256"]
    assert len(manifest["fixtures"]) == 10
    assert len({f["id"] for f in manifest["fixtures"]}) == 10
    assert "separately authored" in manifest["authored_revision_1b"]["source"]


def test_canonical_pack_line_endings_are_portable_without_changing_the_fixture():
    source = (ROOT / "docs/EXTREME_TEST_PACK.md").read_bytes()
    lf = source.replace(b"\r\n", b"\n")
    crlf = lf.replace(b"\n", b"\r\n")
    assert canonical_pack_sha256(lf) == canonical_pack_sha256(crlf)
    assert canonical_pack_sha256(source) == "1ddcff5ad8d159a53a216d7c6945ab2660cba2b7c864f1e0c96e1782c44d147c"


def test_canonical_pack_digest_still_rejects_content_changes():
    source = (ROOT / "docs/EXTREME_TEST_PACK.md").read_bytes()
    assert b"Contradictory deadlines" in source
    changed = source.replace(b"Contradictory deadlines", b"Contradictory statements", 1)
    assert canonical_pack_sha256(source) != canonical_pack_sha256(changed)


def test_exchanged_http_examples_preserve_partial_balance_and_top_level_errors():
    examples = json.loads(Path(__file__).with_name("http_examples.json").read_text())[
        "operations"
    ]
    replay = [
        e
        for e in examples
        if e["method"] == "POST" and e["path"] == "/api/v2/cases" and e["status"] == 201
    ]
    assert replay[0]["response"] == replay[1]["response"]
    errors = [e["response"] for e in examples if e["status"] >= 400]
    assert errors and all(set(e) == {"error"} for e in errors)
    detail = next(
        e["response"]
        for e in examples
        if e["method"] == "GET" and e["status"] == 200 and "/cases/" in e["path"]
    )
    assert detail["projection"]["money_by_currency"]["INR"] == {
        "promised_minor": 50000,
        "received_minor": 20000,
        "outstanding_minor": 30000,
    }
    assert detail["projection"]["status"] != "resolved"
    assert all("cookie" not in e and "headers" not in e for e in examples)
