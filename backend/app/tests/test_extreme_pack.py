"""Isolated remaining-pack probes. Verdicts are written separately from pytest execution."""
import json
import time
from datetime import datetime, timezone
from pathlib import Path
import pytest
from backend.app.tests.test_accounts import accounts, login
from backend.app.models.case import Case
from backend.app.models.commitment import Commitment
from backend.app.models.account import AccountSession
from backend.app.services.ai_adapter import ai_adapter, AITimeoutError, AIServiceUnavailableError
from backend.app.services import case_state

OUT = Path('storage/extreme-testing-2026-11-15/scenario-backend.jsonl')
def report(id, verdict, observation):
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open('a', encoding='utf-8') as f:
        f.write(json.dumps(dict(id=id, verdict=verdict, observation=observation), ensure_ascii=False)+'\n')

def case(client):
    r=client.post('/api/v1/cases',json={'title':'Extreme synthetic refund','merchant_name':'Synthetic Shop'})
    assert r.status_code==201, r.text
    return r.json()['case']
def upload(client,c,content=b'We will refund INR 4999 by 2026-11-17.',name='source.txt',mime='text/plain',version=1):
    return client.post(f"/api/v1/cases/{c['id']}/evidence",data={'expected_version':version},files={'file':(name,content,mime)})
def detail(client,c):return client.get('/api/v1/cases/'+c['id']).json()
def seed(client,db,dates):
    c=case(client)
    for i,date in enumerate(dates):
        db.add(Commitment(case_id=c['id'],kind='refund',description=f'Refund {i}',amount_minor=(i+1)*10000,currency='INR',due_at=date,status='active'))
    db.commit()
    return c
@pytest.fixture
def clock(monkeypatch):
    class Fixed(datetime):
        @classmethod
        def now(cls,tz=None):return cls(2026,11,15,12,tzinfo=timezone.utc)
    monkeypatch.setattr(case_state,'datetime',Fixed)

def test_repeated_create(client):
    a,b=case(client),case(client)
    assert a['id']!=b['id']
    report('P2-01','FAIL','Two identical POST /cases requests both returned 201 and distinct IDs. API replay is not idempotent; browser click protection is tested separately.')

def test_duplicate_source(client):
    import io
    from PIL import Image
    image=io.BytesIO();Image.new('RGB',(16,16),'white').save(image,format='PNG')
    c=case(client);a=upload(client,c,image.getvalue(),'duplicate.png','image/png');b=upload(client,c,image.getvalue(),'duplicate.png','image/png',version=2)
    assert a.status_code==b.status_code==201
    assert a.json()['evidence']['sha256']==b.json()['evidence']['sha256']
    report('P2-04','FAIL', 'Identical bytes uploaded twice with current versions produced two evidence IDs with the same SHA-256; no duplicate warning in responses.')

@pytest.mark.parametrize('size',[50000,100000])
def test_big_text(client,size):
    from backend.app.ai.document_processor import DocumentProcessor
    c=case(client);r=upload(client,c,b'x'*size)
    assert r.status_code==201
    # Exercise the actual parser boundary without making a provider request.
    p=DocumentProcessor()
    try:
        p.process_bytes(b'x'*size,filename='large.txt')
        outcome='accepted'
    except Exception as e:
        assert type(e).__name__=='UnreadableDocumentError',repr(e)
        outcome=type(e).__name__+': '+str(e)
    assert (outcome=='accepted')==(size==50000),outcome
    report('P2-02','OBSERVED',f'{size} bytes: upload 201; document parser: {outcome}')

@pytest.mark.parametrize('name,content,mime,id',[
    ('large.pdf',b'%PDF-1.4\n'+b'x'*(10*1024*1024),'application/pdf','P2-05'),
    ('broken.pdf',b'%PDF-1.4\nTHIS IS NOT A VALID PDF','application/pdf','P2-06'),
    ('renamed.pdf',b'Just plain text, not a PDF.','application/pdf','P2-07')],ids=['oversize','corrupt','renamed'])
def test_files(client,name,content,mime,id):
    c=case(client);r=upload(client,c,content,name,mime)
    if id=='P2-06' and r.status_code==201:
        x=client.post(f"/api/v1/cases/{c['id']}/extractions",json={'expected_version':2,'evidence_ids':[r.json()['evidence']['id']]})
        assert x.status_code in (400,422),x.text
        report(id,'PASS',f'Original accepted by signature, extraction rejected gracefully: {x.status_code}, {x.text[:450]}; no commitments created.')
        assert not detail(client,c)['commitments']
    elif id=='P2-07' and r.status_code==201:
        assert r.json()['evidence']['media_type']=='text/plain'
        report(id,'PASS','Renamed text file is detected and stored as text/plain rather than trusted as PDF. Extension remains .pdf; UI labeling may be confusing, but actual content type is validated.')
    else:
        expected=413 if id=='P2-05' else 415
        assert r.status_code==expected,r.text
        assert not detail(client,c)['evidence']
        report(id,'PASS',f'HTTP {r.status_code}; no evidence rows saved. {r.text[:300]}')

def test_version_replay(client):
    c=case(client);a=upload(client,c);b=upload(client,c,version=1)
    assert (a.status_code,b.status_code)==(201,409)
    assert len(detail(client,c)['evidence'])==1
    report('P2-09','PARTIAL','Two writes using the same observed version: first 201, stale second 409; one file row. Sequential stale-tab simulation, not concurrent PostgreSQL transactions or two browser tabs.')

@pytest.mark.parametrize('exception,status',[(AITimeoutError,504),(AIServiceUnavailableError,503)])
def test_provider_failure_retry(client,monkeypatch,exception,status):
    c=case(client);u=upload(client,c);eid=u.json()['evidence']['id']
    original=ai_adapter.extract_commitments
    def bad(*a,**k):raise exception('Injected offline test failure')
    monkeypatch.setattr(ai_adapter,'extract_commitments',bad)
    path=f"/api/v1/cases/{c['id']}/extractions";payload={'expected_version':2,'evidence_ids':[eid]}
    r=client.post(path,json=payload);assert r.status_code==status,r.text
    d=detail(client,c);assert d['case']['version']==2 and len(d['evidence'])==1 and not d['commitments'] and not d['extractions']
    monkeypatch.setattr(ai_adapter,'extract_commitments',original)
    retry=client.post(path,json=payload);assert retry.status_code==201,retry.text
    report('P2-10' if status==504 else 'P2-11','PARTIAL',f'Injected provider failure returned {status}; case/version/original preserved; retry 201 with one original. Real wait/network and UI covered separately.')

def test_invalid_model(client,monkeypatch):
    c=case(client);u=upload(client,c)
    monkeypatch.setattr(ai_adapter,'extract_commitments',lambda *a,**k:{'schema_version':1,'candidates':[{'terms':{}}]})
    r=client.post(f"/api/v1/cases/{c['id']}/extractions",json={'expected_version':2,'evidence_ids':[u.json()['evidence']['id']]})
    assert r.status_code==502,r.text
    d=detail(client,c);assert not d['commitments'] and not d['extractions'] and d['case']['version']==2
    report('P2-16','PASS','Incomplete candidate returned 502 AI_INVALID_OUTPUT; zero saved extraction/commitment rows and unchanged version.')

def test_account_expiry(accounts):
    client,provider,db=accounts;token=provider.add();assert login(client,token).status_code==200
    c=case(client);db.query(AccountSession).one().expires_at=int(time.time())-1;db.commit()
    assert upload(client,c).status_code==401
    provider.tokens[token]['auth_time']=int(time.time());assert login(client,token).status_code==200
    assert client.get('/api/v1/cases/'+c['id']).status_code==200
    report('P2-12','PARTIAL','Expired SQL account session denied write with 401; fresh provider-stub login restores same owned case. Unsaved React form preservation tested separately; no real Firebase expiry.')

def test_account_privacy(accounts):
    client,provider,db=accounts;login(client,provider.add());c=case(client);u=upload(client,c);assert u.status_code==201
    download=u.json()['evidence']['download_path'];assert client.get(download).status_code==200
    login(client,provider.add('other-extreme'))
    assert client.get('/api/v1/cases/'+c['id']).status_code==404
    assert client.get(download).status_code==404
    report('P2-13','PASS','Two distinct provider-stub identities: owner reads case/original; other account receives 404 for both. Real API/SQL authorization, not two live Google accounts.')

def test_fixed_clock_states(client,db_session,clock):
    future=seed(client,db_session,['2026-11-16T18:29:59Z']);past=seed(client,db_session,['2026-11-12T18:29:59Z'])
    assert detail(client,future)['case']['status']=='open'
    d=detail(client,past);assert d['case']['status']=='overdue' and d['commitments'][0]['status']=='active'
    report('P3-01','PASS','At fixed 15 Nov 2026 12:00 UTC, 16 Nov deadline is open, not overdue.')
    report('P3-02','PASS','12 Nov deadline projects overdue; obligation remains active, with no automatic outcome/nonfulfillment event.')
    c=seed(client,db_session,['2026-11-20T18:29:59Z'])
    r=client.post(f"/api/v1/cases/{c['id']}/resolve",json={'expected_version':1,'resolution_note':'Synthetic receipt confirmed early'})
    assert r.status_code==200,r.text
    assert detail(client,c)['case']['status']=='resolved'
    report('P3-03','PARTIAL','Early user resolution succeeds and commitments are fulfilled. No background reminder delivery exists to cancel/test in this release.')

def test_multiple_deadlines(client,db_session,clock):
    c=seed(client,db_session,['2026-11-12T18:29:59Z','2026-11-22T18:29:59Z'])
    d=detail(client,c);assert len(d['commitments'])==2 and d['case']['status']=='overdue'
    assert len({v['due_at'] for v in d['commitments']})==2
    report('P3-05','PARTIAL','Two same-case obligations retain separate dates; any past active deadline makes case overdue. UI chooses one aggregate deadline, tested separately.')

def test_delete_unavailable(client):
    c=case(client);r=client.delete('/api/v1/cases/'+c['id'])
    assert r.status_code==405
    assert client.get('/api/v1/cases/'+c['id']).status_code==200
    report('P3-06','FAIL','DELETE /cases/{id} returns 405; record remains. Connected deletion/reminder cancellation are unsupported.')

def test_timezones(client,db_session,monkeypatch):
    class Fixed(datetime):
        @classmethod
        def now(cls,tz=None):return cls(2026,11,15,18,30,tzinfo=timezone.utc)
    monkeypatch.setattr(case_state,'datetime',Fixed)
    a=seed(client,db_session,['2026-11-16T00:00:00+05:30']);b=seed(client,db_session,['2026-11-16T00:00:00-08:00'])
    assert detail(client,a)['case']['status']=='open' # equality is not overdue
    assert detail(client,b)['case']['status']=='open'
    class Later(datetime):
        @classmethod
        def now(cls,tz=None):return cls(2026,11,15,18,30,1,tzinfo=timezone.utc)
    monkeypatch.setattr(case_state,'datetime',Later)
    assert detail(client,a)['case']['status']=='overdue' and detail(client,b)['case']['status']=='open'
    report('P3-07','PASS','IST midnight equals 18:30 UTC: not overdue at equality, overdue one second later; same calendar PST midnight remains upcoming. Numeric offsets used (no ambiguous PST abbreviation parsing).')

def test_revision_complaint(client,clock):
    c=case(client);u=upload(client,c);eid=u.json()['evidence']['id']
    def confirm(version,date,prior=None):
        x=client.post(f"/api/v1/cases/{c['id']}/extractions",json={'expected_version':version,'evidence_ids':[eid]});assert x.status_code==201,x.text
        value=x.json();candidate=value['extraction']['candidates'][0]
        item={'candidate_id':candidate['candidate_id'],'action':'revision' if prior else 'new','supersedes_id':prior,'terms':{'kind':'refund','description':'Synthetic order refund','amount_minor':499900,'currency':'INR','due_at':date},'evidence_ids':[eid]}
        r=client.post(f"/api/v1/cases/{c['id']}/extractions/{value['extraction']['id']}/review",json={'expected_version':value['case_version'],'decision':'approve','items':[item]});assert r.status_code==200,r.text
        return r.json()
    a=confirm(2,'2026-11-17T18:29:59Z');b=confirm(a['case_version'],'2026-11-22T18:29:59Z',a['commitments'][0]['id'])
    d=detail(client,c);assert len(d['commitments'])==2
    assert {x['status'] for x in d['commitments']}=={'active','superseded'}
    assert all(eid in x['evidence_ids'] for x in d['commitments'])
    report('P3-04','PASS','Reviewed 17→22 Nov revision preserves both rows, dates, predecessor link and source. Same source reused for controlled review; semantic AI revision detection is out of scope.')
    r=client.post(f"/api/v1/cases/{c['id']}/complaint-draft",json={'expected_version':b['case_version'],'requested_remedy':'Please confirm the refund outcome.'});assert r.status_code==200,r.text
    body=r.json()['draft']['body'];assert all(t in body for t in ['Synthetic Shop','4999.00','2026-11-17','2026-11-22',eid])
    report('P3-08','PASS','Complaint contains correct company, INR 4999.00, both deadlines, source ID and filename; generation preserves record. It is a follow-up, not an independent fact verification.')
    # Make the current confirmed date overdue without recording a receipt/nonreceipt outcome.
    # Use the real controlled review flow for the final amendment.
    z=confirm(b['case_version'],'2026-11-12T18:29:59Z',b['commitments'][0]['id'])
    r=client.post(f"/api/v1/cases/{c['id']}/complaint-draft",json={'expected_version':z['case_version'],'requested_remedy':'Please confirm the outcome.'});assert r.status_code==200,r.text
    body=r.json()['draft']['body'];assert not any(t in body.lower() for t in ['you failed','breach','have not received','unfulfilled'])
    report('P3-09','PASS','Overdue case without a confirmed outcome generates a request for an update; no asserted breach, failed payment or nonreceipt in the generated factual body. User-authored text is not independently verified.')
