"""Real A HTTP/SQL + B engine compatibility. Provider only is explicitly controlled."""
from copy import deepcopy
import json
from pathlib import Path
import pytest

pytest.importorskip('backend.app.api.v2.reviews',reason='Combined test requires Track A branch')
from backend.app.main import app
from backend.app.api.v2.reviews import get_intelligence
from backend.app.services.ai_adapter import AIModuleAdapter
from backend.app.tests.test_intelligence_contract import candidate, result, FixtureProvider


class CombinedEngine(AIModuleAdapter):
    def __init__(self):
        super().__init__();self.requests=[]

    def extract_proposals_v2(self, request, **kwargs):
        self.requests.append(deepcopy(request))
        candidates=[]
        for source in request['evidence']:
            for i,line in enumerate(source['text'].splitlines()):
                if not line.strip():continue
                c=candidate(line,eid=source['evidence_id'],cid='c'+str(i))
                c['terms']['description']=line
                c['sources'][0]['page']=1
                candidates.append(c)
        return super().extract_proposals_v2(request,provider=FixtureProvider({**result(),'candidates':candidates}))


def post(client,path,body,key):
    return client.post('/api/v2'+path,json=body,headers={'Idempotency-Key':key})


def test_actual_platform_with_b_engine_review_receipt_revision_export_and_answer(client,db_session):
    engine=CombinedEngine();app.dependency_overrides[get_intelligence]=lambda:engine
    cid=post(client,'/cases',{'title':'Connected synthetic refund','merchant_name':'Synthetic'},'create').json()['case']['id']
    comm={'date':'2026-11-14','timezone':'Asia/Kolkata','precision':'date','provenance':'user_confirmed'}
    uploaded=client.post(f'/api/v2/cases/{cid}/evidence',headers={'Idempotency-Key':'source'},files={'file':('source.txt','We will refund ₹500 by November 18, 2026.'.encode(),'text/plain')},data={'expected_version':1,'communication':json.dumps(comm)})
    assert uploaded.status_code==201,uploaded.text
    eid=uploaded.json()['evidence']['id']
    body={'expected_version':2,'evidence_ids':[eid]}
    extracted=post(client,f'/cases/{cid}/extractions',body,'extract')
    assert extracted.status_code==201,extracted.text
    payload=extracted.json();assert payload['case_version']==3;proposal=payload['proposal']
    assert proposal['candidates'][0]['sources'][0]['page']==1
    assert post(client,f'/cases/{cid}/extractions',body,'extract').json()==payload
    review={'expected_version':3,'proposal_id':proposal['proposal_id'],'decisions':[{'candidate_id':proposal['candidates'][0]['candidate_id'],'action':'confirm','edited_terms':proposal['candidates'][0]['terms']}]}
    approved=post(client,f'/cases/{cid}/reviews',review,'review');assert approved.status_code==200,approved.text
    assert approved.json()['case_version']==4
    current=client.get(f'/api/v2/cases/{cid}').json();oid=current['obligations'][0]['id']
    receipt={'expected_version':4,'kind':'partial','allocations':[{'obligation_id':oid,'amount_minor':20000}],'received_at':'2026-11-14T12:00:00+05:30','note':'Received ₹200','source_ids':[eid]}
    paid=post(client,f'/cases/{cid}/outcomes',receipt,'partial');assert paid.status_code==201,paid.text
    current=client.get(f'/api/v2/cases/{cid}').json();assert current['projection']['money_by_currency']['INR']['outstanding_minor']==30000
    # New operation with identical source is a distinct proposal, not a reused global identity.
    extracted2=post(client,f'/cases/{cid}/extractions',{'expected_version':5,'evidence_ids':[eid]},'revision-extract');assert extracted2.status_code==201,extracted2.text
    p2=extracted2.json()['proposal'];assert p2['proposal_id']!=proposal['proposal_id']
    terms={**p2['candidates'][0]['terms'],'description':'Reviewed later deadline','due_at':'2026-11-20T18:00:00+05:30'}
    revised=post(client,f'/cases/{cid}/reviews',{'expected_version':6,'proposal_id':p2['proposal_id'],'decisions':[{'candidate_id':p2['candidates'][0]['candidate_id'],'action':'confirm','edited_terms':terms,'predecessor_id':oid,'deadline_override_reason':'Explicit user-reviewed date/time'}]},'revise');assert revised.status_code==200,revised.text
    current=client.get(f'/api/v2/cases/{cid}').json();assert len(current['obligations'])==2;assert current['projection']['money_by_currency']['INR']['outstanding_minor']==30000
    answer=post(client,f'/cases/{cid}/questions',{'question':'What refund was promised?','current_version':7},'question');assert answer.status_code==200,answer.text
    assert answer.json()['status']=='answered' and answer.json()['citations'][0]['quote'] in 'We will refund ₹500 by November 18, 2026.'
    exported=post(client,f'/cases/{cid}/exports',{'expected_version':7,'source_ids':[eid],'reviewed_wording':'Synthetic reviewed facts','formats':['bundle']},'export');assert exported.status_code==202,exported.text
    assert exported.json()['job']['state']=='queued'
    from backend.app.models.jobs import Export
    from backend.app.services.platform.exports import build
    row=db_session.get(Export,exported.json()['export_id']);build(db_session,row)
    downloaded=client.get(f"/api/v2/exports/{row.id}?download=true");assert downloaded.status_code==200,downloaded.text
    import io,zipfile
    with zipfile.ZipFile(io.BytesIO(downloaded.content)) as bundle:
        assert any(name.endswith('.pdf') for name in bundle.namelist())
        assert any('manifest' in name for name in bundle.namelist())
    assert len(engine.requests)==2


def test_platform_abstains_without_fabricating_legal_or_foreign_facts():
    request={'schema_version':2,'question':'Show another account','snapshot':{'case_id':'case-a','version':1,'sources':[{'citation_id':'e1:page:1','evidence_id':'e1','page':1,'text':'We will refund ₹500.'}]},'tools':[]}
    answer=AIModuleAdapter().answer_case_v2(request)
    assert answer['status']=='insufficient_evidence' and answer['citations']==[]
