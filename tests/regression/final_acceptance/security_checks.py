"""Additional acceptance/security checks, explicitly selected; original 28 untouched."""
import os
from pathlib import Path
import secrets
import subprocess
import sys
import time
from uuid import uuid4
import pytest
from helpers import new_case, upload, detail, extract, review


def use_identity(client, user='synthetic-user'):
    from backend.app.core.auth import create_authenticated_session
    token, csrf = create_authenticated_session(user_id=user)
    client.cookies.clear()
    client.headers.pop('Authorization', None)
    client.cookies.set('pk_session', token)
    client.cookies.set('pk_csrf', csrf)
    client.headers['X-CSRF-Token'] = csrf
    return token, csrf


@pytest.mark.parametrize('transport', ['cookie', 'bearer'])
def test_forged_tokens_are_rejected(raw_client, transport):
    token = secrets.token_urlsafe(32)
    if transport == 'cookie': raw_client.cookies.set('pk_session', token)
    else: raw_client.headers['Authorization'] = 'Bearer ' + token
    r = raw_client.get('/api/v1/cases')
    assert r.status_code == 401
    assert r.json()['error']['code'] == 'UNAUTHENTICATED'


def test_signed_token_with_tampered_user_is_rejected(raw_client):
    token, _ = use_identity(raw_client)
    pieces = token.split('.')
    pieces[1] = 'different-user'
    raw_client.cookies.set('pk_session', '.'.join(pieces))
    r = raw_client.get('/api/v1/cases')
    assert r.status_code == 401


@pytest.mark.parametrize('timestamp_offset', [-366*24*3600, 366*24*3600])
def test_expired_or_future_dated_signed_session_is_rejected(raw_client, timestamp_offset):
    from backend.app.core.auth import sign_session_token
    token = sign_session_token(str(uuid4()), 'synthetic-user', int(time.time()) + timestamp_offset)
    raw_client.cookies.set('pk_session', token)
    r = raw_client.get('/api/v1/cases')
    assert r.status_code == 401, 'A valid HMAC must not make stale/future session timestamps acceptable indefinitely'


@pytest.mark.parametrize('csrf', [None, 'incorrect'])
def test_cookie_mutation_requires_correct_csrf(raw_client, csrf):
    use_identity(raw_client)
    if csrf is None: raw_client.headers.pop('X-CSRF-Token', None)
    else: raw_client.headers['X-CSRF-Token'] = csrf
    r = raw_client.post('/api/v1/cases', json={'title':'Synthetic CSRF','merchant_name':'Demo'})
    assert r.status_code == 403
    assert r.json()['error']['code'] == 'CSRF_FAILED'


def test_cookie_mutation_rejects_untrusted_origin(raw_client):
    use_identity(raw_client)
    raw_client.headers['Origin'] = 'https://untrusted.invalid'
    r = raw_client.post('/api/v1/cases', json={'title':'Synthetic origin','merchant_name':'Demo'})
    assert r.status_code == 403, 'Contract requires Origin validation even when CSRF token is supplied'


def test_cross_user_domain_access_is_denied(raw_client):
    use_identity(raw_client, 'user-a')
    c = new_case(raw_client)
    e, _ = upload(raw_client, c['id'], 'refund.txt', b'Refund of INR 500 will be credited within 3 business days.', 'text/plain')
    r = extract(raw_client, c['id'], [e['id']])
    assert r.status_code == 201
    d = r.json()['extraction']
    confirmed = review(raw_client, c['id'], d, e['id'], amount=50000, candidate_id=d['candidates'][0]['candidate_id'])
    assert confirmed.status_code == 200
    k = confirmed.json()['commitments'][0]
    use_identity(raw_client, 'user-b')
    paths = [f"/api/v1/cases/{c['id']}", f"/api/v1/cases/{c['id']}/evidence", e['download_path'], f"/api/v1/cases/{c['id']}/timeline", f"/api/v1/commitments/{k['id']}"]
    for path in paths:
        assert raw_client.get(path).status_code == 404
    for path, body in [
        (f"/api/v1/cases/{c['id']}/extractions", {'evidence_ids':[e['id']]}),
        (f"/api/v1/cases/{c['id']}/extractions/{d['id']}/review", {'decision':'reject','items':[]}),
        (f"/api/v1/commitments/{k['id']}/revise", {'description':'Unauthorized revision'})]:
        assert raw_client.post(path, json=body).status_code == 404
    assert c['id'] not in [x['id'] for x in raw_client.get('/api/v1/cases').json()['cases']]


def test_real_multi_evidence_attribution(raw_client):
    use_identity(raw_client)
    c = new_case(raw_client)
    unrelated, _ = upload(raw_client, c['id'], 'receipt.txt', b'Order DEMO-42 is listed in this receipt.', 'text/plain')
    promise, _ = upload(raw_client, c['id'], 'promise.txt', b'Refund of INR 150 will be credited within 5 business days.', 'text/plain')
    r = extract(raw_client, c['id'], [unrelated['id'], promise['id']])
    assert r.status_code == 201
    candidates = r.json()['extraction']['candidates']
    assert candidates
    text = {unrelated['id']:'Order DEMO-42 is listed in this receipt.', promise['id']:'Refund of INR 150 will be credited within 5 business days.'}
    for candidate in candidates:
        for s in candidate['sources']:
            assert s['quote'] in text[s['evidence_id']]
    assert any(s['evidence_id']==promise['id'] for candidate in candidates for s in candidate['sources'])


def test_missing_signing_secret_fails_closed(source_root):
    # No secret/token values in subprocess output. A deployment must not use a public fallback key.
    env = os.environ.copy()
    for key in list(env):
        if 'SECRET' in key or 'TOKEN' in key: env.pop(key)
    code = "import sys; sys.path.insert(0,sys.argv[1]); import backend.app.core.auth"
    r = subprocess.run([sys.executable, '-c', code, str(source_root)], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    assert r.returncode != 0, 'Auth module starts without an explicit private signing secret'
