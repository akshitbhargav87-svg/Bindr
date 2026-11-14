from copy import deepcopy
from uuid import uuid4
import pytest
from helpers import candidate, check_error, detail, extract, review, stub_draft, upload, TEXT


def test_invented_candidate_is_rejected(api, case_and_evidence, adapter_module, monkeypatch):
    c, e = case_and_evidence
    d = stub_draft(monkeypatch, adapter_module, api, c['id'], e['id'])
    before = detail(api, c['id'])
    r = review(api, c['id'], d, e['id'], candidate_id='c999')
    assert r.status_code == 422
    assert detail(api, c['id']) == before
    check_error(r, 422, 'VALIDATION_ERROR')


@pytest.mark.parametrize('amount', [-1, -499900])
def test_negative_refund_is_rejected(api, case_and_evidence, adapter_module, monkeypatch, amount):
    c, e = case_and_evidence
    d = stub_draft(monkeypatch, adapter_module, api, c['id'], e['id'])
    before = detail(api, c['id'])
    r = review(api, c['id'], d, e['id'], amount=amount)
    assert r.status_code == 422
    assert detail(api, c['id']) == before
    check_error(r, 422, 'VALIDATION_ERROR')


def test_duplicate_evidence_ids_rejected_before_inference(api, case_and_evidence, adapter_module, monkeypatch):
    c, e = case_and_evidence
    calls = []
    def provider(**kw):
        calls.append(kw)
        return {'schema_version': 1, 'candidates': [candidate(e['id'])]}
    monkeypatch.setattr(adapter_module.ai_adapter, 'extract_commitments', provider)
    before = detail(api, c['id'])
    r = extract(api, c['id'], [e['id'], e['id']])
    assert r.status_code == 422
    assert not calls
    assert detail(api, c['id']) == before
    check_error(r, 422, 'VALIDATION_ERROR')


def malformed(name, eid):
    out = {'schema_version': 1, 'candidates': [candidate(eid)]}
    if name == 'wrong_version': out['schema_version'] = 999
    elif name == 'missing_terms': del out['candidates'][0]['terms']
    elif name == 'unknown_key': out['candidates'][0]['unexpected'] = True
    elif name == 'foreign_source': out['candidates'][0]['sources'][0]['evidence_id'] = str(uuid4())
    elif name == 'fabricated_quote': out['candidates'][0]['sources'][0]['quote'] = 'This was never uploaded.'
    elif name == 'invalid_confidence': out['candidates'][0]['confidence'] = 1.5
    elif name == 'duplicate_candidate': out['candidates'] *= 2
    return out


@pytest.mark.parametrize('name', ['wrong_version', 'missing_terms', 'unknown_key', 'foreign_source', 'fabricated_quote', 'invalid_confidence', 'duplicate_candidate'])
def test_invalid_ai_boundary_output_saves_no_draft(api, case_and_evidence, adapter_module, monkeypatch, name):
    c, e = case_and_evidence
    out = malformed(name, e['id'])
    # Invalid *internal provider/adapter output*, not an invalid browser request: HTTP 502.
    monkeypatch.setattr(adapter_module.ai_adapter, 'extract_commitments', lambda **kw: deepcopy(out))
    before = detail(api, c['id'])
    r = extract(api, c['id'], [e['id']])
    assert r.status_code == 502
    assert detail(api, c['id']) == before
    check_error(r, 502, 'AI_INVALID_OUTPUT')


def test_missing_meta_credentials_http_saves_nothing(api, case_and_evidence, adapter_module, monkeypatch):
    c, e = case_and_evidence
    monkeypatch.setenv('AI_PROVIDER', 'meta')
    settings = getattr(adapter_module, 'settings', None)
    if settings is not None:
        monkeypatch.setattr(settings, 'AI_PROVIDER', 'meta')
        monkeypatch.setattr(settings, 'MODEL_API_KEY', None)
    before = detail(api, c['id'])
    r = extract(api, c['id'], [e['id']])
    assert r.status_code == 503
    assert detail(api, c['id']) == before
    check_error(r, 503, 'AI_UNAVAILABLE')


@pytest.mark.parametrize('failure,status,code', [('AITimeoutError', 504, 'AI_TIMEOUT'), ('AIServiceUnavailableError', 503, 'AI_UNAVAILABLE'), ('AIInvalidOutputError', 502, 'AI_INVALID_OUTPUT')])
def test_provider_errors_have_top_level_envelope(api, case_and_evidence, adapter_module, monkeypatch, failure, status, code):
    c, e = case_and_evidence
    def fail(**kw): raise getattr(adapter_module, failure)('Synthetic failure')
    monkeypatch.setattr(adapter_module.ai_adapter, 'extract_commitments', fail)
    before = detail(api, c['id'])
    r = extract(api, c['id'], [e['id']])
    assert detail(api, c['id']) == before
    check_error(r, status, code)


@pytest.mark.parametrize('decision', ['approve', 'reject'])
def test_review_gate_and_closed_draft(api, case_and_evidence, adapter_module, monkeypatch, decision):
    c, e = case_and_evidence
    d = stub_draft(monkeypatch, adapter_module, api, c['id'], e['id'])
    assert d['status'] == 'pending_review'
    assert detail(api, c['id'])['commitments'] == []
    r = review(api, c['id'], d, e['id'], decision=decision)
    assert r.status_code == 200
    assert r.json()['extraction']['status'] == ('reviewed' if decision == 'approve' else 'rejected')
    saved = detail(api, c['id'])
    assert len(saved['commitments']) == (1 if decision == 'approve' else 0)
    if decision == 'approve':
        assert saved['commitments'][0]['evidence_ids'] == [e['id']]
        assert saved['commitments'][0]['amount_minor'] == 499900
    repeated = review(api, c['id'], d, e['id'], decision=decision)
    assert repeated.status_code == 409
    assert detail(api, c['id']) == saved
    check_error(repeated, 409, 'DRAFT_CLOSED')


def test_revision_preserves_original_evidence_and_history(api, case_and_evidence, adapter_module, monkeypatch):
    c, e1 = case_and_evidence
    d1 = stub_draft(monkeypatch, adapter_module, api, c['id'], e1['id'])
    first = review(api, c['id'], d1, e1['id'])
    assert first.status_code == 200
    original = first.json()['commitments'][0]
    e2, _ = upload(api, c['id'], 'extension.txt', b'The same refund deadline is extended.', 'text/plain')
    original_bytes = api.get(e1['download_path']).content
    d2 = stub_draft(monkeypatch, adapter_module, api, c['id'], e2['id'])
    r = review(api, c['id'], d2, e2['id'], predecessor=original['id'], evidence_ids=[e1['id'], e2['id']])
    assert r.status_code == 200
    revised = r.json()['commitments'][0]
    assert revised['id'] != original['id'] and revised['supersedes_id'] == original['id']
    assert set(revised['evidence_ids']) == {e1['id'], e2['id']}
    state = detail(api, c['id'])
    assert len(state['commitments']) == 2
    old = next(k for k in state['commitments'] if k['id'] == original['id'])
    assert old['status'] == 'superseded'
    assert {k: v for k, v in old.items() if k != 'status'} == {k: v for k, v in original.items() if k != 'status'}
    assert next(e for e in state['evidence'] if e['id'] == e1['id']) == e1
    assert api.get(e1['download_path']).content == original_bytes == TEXT.encode()
    assert {x['id']: x['status'] for x in state['extractions']} == {d1['id']: 'reviewed', d2['id']: 'reviewed'}
