from helpers import check_error


def test_anonymous_download_denied(raw_client, db_session, modules):
    # Seed synthetic private bytes directly so a missing login bootstrap cannot hide this defect.
    from backend.app.models.case import Case
    from backend.app.models.evidence import Evidence
    from uuid import uuid4
    c = Case(id=str(uuid4()), title='Private synthetic case', merchant_name='Demo')
    db_session.add(c)
    eid = str(uuid4())
    key, digest, size = modules[3].storage_service.save_file(b'PRIVATE SYNTHETIC EVIDENCE', eid)
    path = f'/api/v1/cases/{c.id}/evidence/{eid}/content'
    e = Evidence(id=eid, case_id=c.id, filename='private.txt', media_type='text/plain', size_bytes=size, sha256=digest, storage_key=key, download_path=path)
    db_session.add(e)
    db_session.commit()
    raw_client.cookies.clear()
    r = raw_client.get(path)
    assert r.status_code == 401, 'Anonymous private evidence access must require authentication'
    assert b'PRIVATE SYNTHETIC EVIDENCE' not in r.content
    check_error(r, 401, 'UNAUTHENTICATED')
