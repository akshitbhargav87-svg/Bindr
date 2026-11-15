"""Fresh local seam retests. Provider fixtures are not live semantic acceptance."""
from copy import deepcopy
from pathlib import Path
import json
import pytest
from backend.app.services.ai_adapter import AIModuleAdapter
from backend.app.services.intelligence.extraction import IntelligenceFailure, ProposalEngine
from backend.app.ai.providers.base import AITimeoutError, AIResponseParsingError


def candidate(quote="We will refund ₹500 by November 18, 2026.", eid="e1", cid="provider-id"):
    return {"candidate_id": cid, "terms": {"kind": "refund", "description": "Refund ₹500", "amount_minor": 50000, "currency": "INR", "due_at": None},
            "sources": [{"evidence_id": eid, "quote": quote}],
            "temporal": {"wording": None, "anchor": None, "duration": None, "range": None, "parse_status": "unknown"},
            "relation": {"kind": "new", "predecessor_id": None, "explanation": "Source-backed proposal"},
            "condition": {"trigger": None, "status": "not_applicable"}, "warnings": []}


def request(text="We will refund ₹500 by November 18, 2026."):
    return {"case_id": "case-1", "request_id": "request-1", "evidence": [{"evidence_id": "e1", "segments": [{"text": text}]}]}


def result(c=None):
    return {"schema_version": 2, "proposal_id": "untrusted-provider-id", "candidates": [c or candidate()], "document_warnings": []}


class FixtureProvider:
    def __init__(self, value):
        self.value, self.calls = value, 0

    def extract_proposals(self, request, timeout):
        self.calls += 1
        if isinstance(self.value, Exception):
            raise self.value
        return deepcopy(self.value)


def test_four_airtel_obligations_keep_individual_sources_and_stable_ids():
    lines = ["Your ₹799 recharge refund will be completed by November 17, 2026.",
             "Your broadband connection will be restored by November 16, 2026.",
             "A ₹200 goodwill credit will be added to your account by November 19, 2026.",
             "Our technician will visit your home on November 15, 2026."]
    candidates = []
    for i, line in enumerate(lines):
        c = candidate(line, cid=str(i))
        c["terms"].update(description=line, kind="refund" if i == 0 else "service", amount_minor=[79900, None, 20000, None][i], currency="INR" if i in (0, 2) else None)
        c["temporal"].update(wording=line, parse_status="explicit")
        candidates.append(c)
    raw = {**result(), "candidates": candidates}
    provider = FixtureProvider(raw)
    adapter = AIModuleAdapter()
    first = adapter.extract_proposals_v2(request("\n".join(lines)), provider=provider)
    assert len(first["candidates"]) == 4
    assert len({c["candidate_id"] for c in first["candidates"]}) == 4
    assert [c["sources"][0]["quote"] for c in first["candidates"]] == lines
    for c in raw["candidates"]:
        c["candidate_id"] = "random-" + c["candidate_id"]
    assert adapter.extract_proposals_v2(request("\n".join(lines)), provider=FixtureProvider(raw)) == first
    assert provider.calls == 1


@pytest.mark.parametrize("mutation", ["amount_bool", "foreign_source", "foreign_predecessor", "wrong_quote", "page", "extra", "naive", "missing", "duplicate"])
def test_strict_validation_rejects_corrupted_or_foreign_output(mutation):
    raw = result()
    c = raw["candidates"][0]
    if mutation == "amount_bool": c["terms"]["amount_minor"] = True
    if mutation == "foreign_source": c["sources"][0]["evidence_id"] = "other-account"
    if mutation == "foreign_predecessor": c["relation"]["predecessor_id"] = "other-case"
    if mutation == "wrong_quote": c["sources"][0]["quote"] = "Invented"
    if mutation == "page": c["sources"][0]["page"] = 9
    if mutation == "extra": c["confirm_automatically"] = True
    if mutation == "naive": c["terms"]["due_at"] = "2026-11-18T12:00:00"
    if mutation == "missing": del c["terms"]["due_at"]
    if mutation == "duplicate": raw["candidates"].append(deepcopy(c))
    with pytest.raises(IntelligenceFailure) as e:
        ProposalEngine(FixtureProvider(raw)).extract(request())
    assert e.value.code == "AI_INVALID_OUTPUT"


@pytest.mark.parametrize("error,code", [(AITimeoutError("PRIVATE KEY"), "AI_TIMEOUT"),
                                      (AIResponseParsingError("private source"), "AI_INVALID_OUTPUT"),
                                      (RuntimeError("secret token"), "AI_UNAVAILABLE")])
def test_typed_stage_failures_no_automatic_retries_or_private_diagnostics(error, code, caplog):
    diagnostics = []
    provider = FixtureProvider(error)
    with pytest.raises(IntelligenceFailure) as exc:
        ProposalEngine(provider).extract(request(), diagnostics)
    assert exc.value.code == code
    assert exc.value.request_id == "request-1"
    assert provider.calls == 1
    assert {"input", "provider"} == {d["stage"] for d in diagnostics}
    assert all(set(d) == {"stage", "request_id", "duration_ms"} for d in diagnostics)
    assert "PRIVATE" not in caplog.text and "secret" not in str(exc.value)


def test_conditional_unknown_and_impossible_date_never_become_fixed_deadlines():
    quote = "If delivery is confirmed, we will initiate a refund within 48 hours."
    c = candidate(quote)
    c["terms"].update(amount_minor=None, currency=None)
    c["condition"] = {"trigger": "If delivery is confirmed", "status": "confirmed"}
    c["terms"]["due_at"] = "2026-11-20T12:00:00Z"
    c["temporal"]["parse_status"] = "explicit"
    out = ProposalEngine(FixtureProvider(result(c))).extract(request(quote))["candidates"][0]
    assert out["condition"]["status"] == "unknown" and out["terms"]["due_at"] is None
    quote = "The refund will arrive by November 31, 2026."
    c = candidate(quote)
    c["terms"].update(amount_minor=None, currency=None)
    c["temporal"].update(wording="November 31, 2026", parse_status="explicit")
    c["terms"]["due_at"] = "2026-12-01T00:00:00Z"
    out = ProposalEngine(FixtureProvider(result(c))).extract(request(quote))["candidates"][0]
    assert out["terms"]["due_at"] is None and out["temporal"]["parse_status"] == "invalid"
    assert any("Impossible" in w for w in out["warnings"])


def test_v1_batch_bridge_extracts_all_numbered_obligations_without_changing_contract(monkeypatch):
    from backend.app.core.config import settings
    monkeypatch.setattr(settings, "AI_PROVIDER", "mock")
    text = "\n".join(["1. Your ₹799 recharge refund will be completed by November 17, 2026.",
                     "2. Your broadband connection will be restored by November 16, 2026.",
                     "3. A ₹200 goodwill credit will be added to your account by November 19, 2026.",
                     "4. Our technician will visit your home on November 15, 2026."])
    output = AIModuleAdapter().extract_commitments("case-1", [{"evidence_id": "e1", "text": text}])
    assert output["schema_version"] == 1 and len(output["candidates"]) == 4
    assert [c["terms"]["amount_minor"] for c in output["candidates"]] == [79900, None, 20000, None]
    assert all(c["sources"][0]["quote"] in text for c in output["candidates"])


def test_all_canonical_fixtures_are_explicit_source_inputs_not_invented_historical_outputs():
    fixtures = json.loads((Path(__file__).resolve().parents[3] / "tests/contracts/intelligence/canonical-inputs.json").resolve().read_text(encoding="utf-8"))
    assert {str(i) for i in range(1, 11)} | {"1B"} == {f["id"] for f in fixtures}
    assert "તમારું" in fixtures[5]["text"]
    assert "newly authored" in fixtures[-1]["provenance"]


@pytest.mark.parametrize('text,wording', [('आपकी ₹999 की रिफंड 20 नवंबर 2026 तक जमा होगी।','20 नवंबर 2026'),
                                       ('તમારું ₹999 રિફંડ 20 નવેમ્બર 2026 સુધીમાં મળી જશે.','20 નવેમ્બર 2026'),
                                       ('Aapka ₹999 refund 20 November 2026 tak aa jayega.','20 November 2026')],ids=['Hindi','Gujarati','Hinglish'])
def test_script_and_segment_citations_preserved_without_claiming_native_semantic_evaluation(text,wording):
    c=candidate(text);c['terms'].update(amount_minor=99900,currency='INR');c['temporal'].update(wording=wording,parse_status='explicit');c['sources'][0].update(page=2)
    req=request(text);req['evidence'][0]['segments'][0]['page']=2
    out=ProposalEngine(FixtureProvider(result(c))).extract(req)['candidates'][0]
    assert out['sources'][0]['quote']==text and out['sources'][0]['page']==2
    assert out['temporal']['wording']==wording
