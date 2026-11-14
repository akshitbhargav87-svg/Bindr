"""Release acceptance: real FastAPI/DB/storage with explicit deterministic AI."""
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.core.auth import create_authenticated_session
from backend.app.services.ai_adapter import ai_adapter


def test_anonymous_bootstrap_is_private_and_persistent(anonymous_client):
    a = anonymous_client.post('/api/v1/auth/session', json={})
    assert a.status_code == 201
    user = a.json()['user_id']
    assert user != 'demo-user'
    csrf = a.json()['csrf_token']
    anonymous_client.headers['X-CSRF-Token'] = csrf
    created = anonymous_client.post('/api/v1/cases', json={'title': 'Private refund', 'merchant_name': 'Shop'})
    assert created.status_code == 201
    assert anonymous_client.get('/api/v1/auth/session').json()['user_id'] == user
    assert anonymous_client.post('/api/v1/auth/session', json={}).json()['user_id'] == user
    assert anonymous_client.post('/api/v1/auth/session', json={'user_id': 'demo-user'}).status_code == 422
    anonymous_client.cookies.clear()
    new = anonymous_client.post('/api/v1/auth/session', json={})
    assert new.json()['user_id'] != user
    assert anonymous_client.get('/api/v1/cases').json()['cases'] == []


def test_full_release_flow(client, secondary_client, monkeypatch):
    # Only the AI response is deterministic; endpoint validation, storage and writes are real.
    def extract(case_id, evidence, **kwargs):
        text = evidence[0]['file_bytes'].decode('utf-8')
        evidence[0]['text'] = text
        return {'schema_version': 1, 'candidates': [{'candidate_id': 'c1', 'terms': {'kind': 'refund',
            'description': 'Refund for returned headphones', 'amount_minor': 499900, 'currency': 'INR',
            'due_at': '2026-11-09T18:29:59Z'}, 'sources': [{'evidence_id': evidence[0]['evidence_id'], 'quote': text}],
            'confidence': .8, 'warnings': [], 'revision': {'relation': 'new', 'supersedes_id': None, 'reason': 'Source promise'}}]}
    monkeypatch.setattr(ai_adapter, 'extract_commitments', extract)
    case = client.post('/api/v1/cases', json={'title': 'Headphones refund', 'merchant_name': 'Shop'}).json()['case']
    cid = case['id']
    ev = client.post(f'/api/v1/cases/{cid}/evidence', files={'file': ('promise.txt', b'We will refund INR 4999.', 'text/plain')}, data={'expected_version': 1})
    assert ev.status_code == 201
    evidence = ev.json()['evidence']
    assert secondary_client.get(f'/api/v1/cases/{cid}').status_code == 404
    assert secondary_client.get(evidence['download_path']).status_code == 404
    assert client.get(evidence['download_path']).content == b'We will refund INR 4999.'
    ext = client.post(f'/api/v1/cases/{cid}/extractions', json={'evidence_ids': [evidence['id']], 'expected_version': 2})
    assert ext.status_code == 201, ext.text
    assert client.get(f'/api/v1/cases/{cid}').json()['commitments'] == []
    extraction = ext.json()['extraction']
    item = {'candidate_id': 'c1', 'action': 'new', 'supersedes_id': None, 'terms': extraction['candidates'][0]['terms'], 'evidence_ids': [evidence['id']]}
    review = client.post(f'/api/v1/cases/{cid}/extractions/{extraction["id"]}/review', json={'expected_version': 3, 'decision': 'approve', 'items': [item]})
    assert review.status_code == 200, review.text
    original = review.json()['commitments'][0]
    assert client.get(f'/api/v1/cases/{cid}').json()['case']['status'] == 'overdue'
    # Stale writes cannot mutate the record.
    stale = client.post(f'/api/v1/cases/{cid}/resolve', json={'expected_version': 3, 'resolution_note': 'Received'})
    assert stale.status_code == 409
    # A second communication is reviewed as a revision, retaining original evidence.
    upload = client.post(f'/api/v1/cases/{cid}/evidence', files={'file': ('revision.txt', b'We will refund INR 4999 on 12 November.', 'text/plain')}, data={'expected_version': 4})
    eid2 = upload.json()['evidence']['id']
    ext2 = client.post(f'/api/v1/cases/{cid}/extractions', json={'evidence_ids': [eid2], 'expected_version': 5}).json()['extraction']
    item.update(action='revision', supersedes_id=original['id'], evidence_ids=[eid2])
    item['terms']['due_at'] = '2026-11-12T18:29:59Z'
    revised = client.post(f'/api/v1/cases/{cid}/extractions/{ext2["id"]}/review', json={'expected_version': 6, 'decision': 'approve', 'items': [item]})
    assert revised.status_code == 200, revised.text
    assert set(revised.json()['commitments'][0]['evidence_ids']) == {evidence['id'], eid2}
    draft = client.post(f'/api/v1/cases/{cid}/complaint-draft', json={'expected_version': 7, 'requested_remedy': 'Please refund the promised amount.'})
    assert draft.status_code == 200
    assert draft.json()['case_version'] == 7
    assert '4999.00' in draft.json()['draft']['body']
    done = client.post(f'/api/v1/cases/{cid}/resolve', json={'expected_version': 7, 'resolution_note': 'Received full refund'})
    assert done.status_code == 200
    detail = client.get(f'/api/v1/cases/{cid}').json()
    assert detail['case']['status'] == 'resolved'
    assert {c['status'] for c in detail['commitments']} == {'superseded', 'fulfilled'}
    assert client.post(f'/api/v1/cases/{cid}/extractions', json={'expected_version': 8, 'evidence_ids': [eid2]}).status_code == 409
