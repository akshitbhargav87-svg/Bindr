from copy import deepcopy
from uuid import UUID

TEXT = 'We will refund INR 4999.00 for order DEMO-42.'


def check_error(response, status, code):
    assert response.status_code == status
    body = response.json()
    assert set(body) == {'error'}, 'Contract requires top-level error, without FastAPI detail wrapper'
    error = body['error']
    assert set(error) == {'code', 'message', 'details', 'request_id'}
    assert error['code'] == code
    assert isinstance(error['message'], str) and error['message']
    UUID(error['request_id'])
    assert isinstance(error['details'], list)
    for detail in error['details']:
        assert set(detail) == {'field', 'message'}
        assert all(isinstance(value, str) for value in detail.values())


def detail(client, cid):
    r = client.get(f'/api/v1/cases/{cid}')
    assert r.status_code == 200
    return r.json()


def new_case(client):
    r = client.post('/api/v1/cases', json={'title': 'Synthetic regression', 'merchant_name': 'Demo Shop'})
    assert r.status_code == 201
    return r.json()['case']


def upload(client, cid, name, content, mime):
    version = detail(client, cid)['case']['version']
    r = client.post(f'/api/v1/cases/{cid}/evidence', files={'file': (name, content, mime)}, data={'expected_version': str(version)})
    assert r.status_code == 201
    return r.json()['evidence'], r.json()['case_version']


def extract(client, cid, ids):
    return client.post(f'/api/v1/cases/{cid}/extractions', json={'evidence_ids': ids, 'expected_version': detail(client, cid)['case']['version']})


def candidate(eid, quote=TEXT):
    return {'candidate_id': 'c1', 'terms': {'kind': 'refund', 'description': 'Refund order DEMO-42', 'amount_minor': 499900, 'currency': 'INR', 'due_at': None},
            'sources': [{'evidence_id': eid, 'quote': quote}], 'confidence': 0.9, 'warnings': [],
            'revision': {'relation': 'new', 'supersedes_id': None, 'reason': 'Synthetic test candidate'}}


def stub_draft(monkeypatch, module, client, cid, eid):
    # Inject at AI boundary so review validation is tested independently of provider mapping.
    source = client.get(f'/api/v1/cases/{cid}/evidence/{eid}/content')
    assert source.status_code == 200
    output = {'schema_version': 1, 'candidates': [candidate(eid, quote=source.content.decode('utf-8'))]}
    monkeypatch.setattr(module.ai_adapter, 'extract_commitments', lambda **kw: deepcopy(output))
    r = extract(client, cid, [eid])
    assert r.status_code == 201
    return r.json()['extraction']


def review(client, cid, draft, eid, *, decision='approve', candidate_id='c1', amount=499900, predecessor=None, evidence_ids=None):
    item = {'candidate_id': candidate_id, 'action': 'revision' if predecessor else 'new', 'supersedes_id': predecessor,
            'terms': {'kind': 'refund', 'description': 'Human reviewed refund', 'amount_minor': amount, 'currency': 'INR', 'due_at': None},
            'evidence_ids': evidence_ids or [eid]}
    return client.post(f"/api/v1/cases/{cid}/extractions/{draft['id']}/review", json={
        'expected_version': detail(client, cid)['case']['version'], 'decision': decision,
        'items': [] if decision == 'reject' else [item]})
