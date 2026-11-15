"""Real local v1 HTTP/SQL retests with explicitly offline inference, not live AI."""
import json
from pathlib import Path
import pytest

FIXTURES=json.loads((Path(__file__).resolve().parents[3]/'tests/contracts/intelligence/canonical-inputs.json').read_text(encoding='utf-8'))


@pytest.mark.parametrize('selected', [[0,1,2,3],[0,2]],ids=['all-four','subset-two'])
def test_airtel_batch_proposals_review_and_sql_reload_preserve_each_fact(client,selected):
    fixture=FIXTURES[2]
    c=client.post('/api/v1/cases',json={'title':'Airtel canonical local retest','merchant_name':'Airtel'}).json()['case']
    cid=c['id']
    upload=client.post(f'/api/v1/cases/{cid}/evidence',data={'expected_version':1},files={'file':('airtel.txt',fixture['text'].encode('utf-8'),'text/plain')})
    assert upload.status_code==201
    eid=upload.json()['evidence']['id'];version=upload.json()['case_version']
    extraction=client.post(f'/api/v1/cases/{cid}/extractions',json={'expected_version':version,'evidence_ids':[eid]})
    assert extraction.status_code==201,extraction.text
    draft=extraction.json()['extraction'];candidates=draft['candidates']
    assert len(candidates)==4
    # Explicit reviewer-selected instants. Calendar arithmetic remains A's responsibility.
    deadlines=['2026-11-17T18:29:59Z','2026-11-16T18:29:59Z','2026-11-19T18:29:59Z','2026-11-15T18:29:59Z']
    items=[]
    for i in selected:
        terms={**candidates[i]['terms'],'description':candidates[i]['sources'][0]['quote'],'due_at':deadlines[i]}
        items.append({'candidate_id':candidates[i]['candidate_id'],'action':'new','supersedes_id':None,'terms':terms,'evidence_ids':[eid]})
    body={'expected_version':extraction.json()['case_version'],'decision':'approve','items':items}
    response=client.post(f"/api/v1/cases/{cid}/extractions/{draft['id']}/review",json=body)
    assert response.status_code==200,response.text
    saved=client.get(f'/api/v1/cases/{cid}').json()
    assert len(saved['commitments'])==len(selected)
    saved_by_description={c['description']:c for c in saved['commitments']}
    for i in selected:
        row=saved_by_description[candidates[i]['sources'][0]['quote']]
        assert row['amount_minor']==[79900,None,20000,None][i]
        assert row['due_at']==deadlines[i]
        assert row['evidence_ids']==[eid]
    replay=client.post(f"/api/v1/cases/{cid}/extractions/{draft['id']}/review",json=body)
    assert replay.status_code==409
    assert len(client.get(f'/api/v1/cases/{cid}').json()['commitments'])==len(selected)


def test_original_xss_bytes_survive_upload_and_reload_without_html_transformation(client):
    fixture=FIXTURES[9]
    c=client.post('/api/v1/cases',json={'title':'Stored source retest','merchant_name':'Test Company'}).json()['case'];cid=c['id']
    raw=fixture['text'].encode('utf-8')
    upload=client.post(f'/api/v1/cases/{cid}/evidence',data={'expected_version':1},files={'file':('source.txt',raw,'text/plain')})
    assert upload.status_code==201
    eid=upload.json()['evidence']['id']
    original=client.get(f'/api/v1/cases/{cid}/evidence/{eid}/content')
    assert original.status_code==200 and original.content==raw
    assert b'<script>' in original.content and b'onerror=' in original.content
    # Browser execution assertions are separate; SQL/HTTP fidelity alone is not XSS acceptance.
