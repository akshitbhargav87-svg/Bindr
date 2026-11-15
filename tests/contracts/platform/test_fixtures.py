"""Checks protect provenance and user-visible financial/privacy semantics in exchanged fixtures."""

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def test_canonical_pack_is_preserved_and_1b_is_labeled_authored():
    manifest = json.loads(
        (Path(__file__).with_name("canonical_inputs.json")).read_text()
    )
    source = ROOT / manifest["source"]
    assert hashlib.sha256(source.read_bytes()).hexdigest() == manifest["source_sha256"]
    assert len(manifest["fixtures"]) == 10
    assert len({f["id"] for f in manifest["fixtures"]}) == 10
    assert "separately authored" in manifest["authored_revision_1b"]["source"]


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
