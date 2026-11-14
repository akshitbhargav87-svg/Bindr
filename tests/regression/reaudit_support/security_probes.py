"""Run explicitly; supplementary security probes do not change the original 28 cases."""
import secrets
from uuid import uuid4
import pytest
from helpers import check_error


@pytest.fixture
def private_file(db_session, modules):
    from backend.app.models.case import Case
    from backend.app.models.evidence import Evidence
    c = Case(id=str(uuid4()), title='Synthetic security audit', merchant_name='Demo')
    db_session.add(c)
    eid = str(uuid4())
    key, digest, size = modules[3].storage_service.save_file(b'SYNTHETIC PRIVATE CONTENT', eid)
    path = f'/api/v1/cases/{c.id}/evidence/{eid}/content'
    db_session.add(Evidence(id=eid, case_id=c.id, filename='private.txt', media_type='text/plain', size_bytes=size, sha256=digest, storage_key=key, download_path=path))
    db_session.commit()
    return c.id, path


@pytest.mark.parametrize('transport', ['cookie', 'bearer'])
def test_unregistered_random_credentials_denied(raw_client, private_file, transport):
    token = secrets.token_urlsafe(32)  # Never registered, persisted, signed or printed.
    if transport == 'cookie':
        raw_client.cookies.set('pk_session', token)
        r = raw_client.get(private_file[1])
    else:
        r = raw_client.get(private_file[1], headers={'Authorization': 'Bearer ' + token})
    assert r.status_code == 401, 'Unregistered random credentials must not authorize evidence access'
    check_error(r, 401, 'UNAUTHENTICATED')


@pytest.mark.parametrize('method', ['GET', 'POST'])
def test_anonymous_case_routes_denied(raw_client, method):
    kwargs = {'json': {'title': 'Synthetic anonymous case', 'merchant_name': 'Demo'}} if method == 'POST' else {}
    r = raw_client.request(method, '/api/v1/cases', **kwargs)
    assert r.status_code == 401, 'Domain case routes require authentication'
    check_error(r, 401, 'UNAUTHENTICATED')


def test_case_ownership_is_represented(modules):
    from backend.app.models.case import Case
    assert 'owner_id' in Case.__table__.columns, 'Contract cases.owner_id is absent; per-user case ownership cannot be enforced'


def test_anonymous_direct_commitment_creation_denied(raw_client, private_file):
    cid, _ = private_file
    r = raw_client.post(f'/api/v1/cases/{cid}/commitments', json={'kind': 'refund', 'description': 'Synthetic direct commitment', 'amount_minor': 10000, 'currency': 'INR'})
    assert r.status_code == 401, 'Alternate commitment route must not bypass authentication/review'
    check_error(r, 401, 'UNAUTHENTICATED')
