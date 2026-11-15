from copy import deepcopy
from types import SimpleNamespace
import json
import requests
import pytest
from backend.app.ai.proposals import StructuredProposalProvider
from backend.app.ai.providers.meta import MetaProvider
from backend.app.services.intelligence.extraction import ProposalEngine, IntelligenceFailure
from backend.app.tests.test_intelligence_contract import request, result


@pytest.mark.parametrize('mode,code', [('timeout','AI_TIMEOUT'),('quota','AI_UNAVAILABLE'),('auth','AI_UNAVAILABLE'),('malformed','AI_INVALID_OUTPUT'),('truncated','AI_INVALID_OUTPUT'),('oversized','AI_INVALID_OUTPUT')])
def test_real_transport_boundary_has_one_attempt_and_safe_stage_error(monkeypatch, mode, code):
    calls=[]
    def post(url,**kwargs):
        calls.append((url,kwargs))
        if mode=='timeout':raise requests.exceptions.Timeout('private evidence or token')
        payload={'choices':[{'message':{'content':'private non-JSON'},'finish_reason':'length' if mode=='truncated' else 'stop'}]}
        return SimpleNamespace(status_code={'quota':429,'auth':401}.get(mode,200),content=b'x'*(1000001 if mode=='oversized' else 1),json=lambda:payload)
    monkeypatch.setattr(requests,'post',post)
    provider=StructuredProposalProvider(MetaProvider(api_key='synthetic-key',base_url='https://provider.invalid/v1',timeout=3))
    with pytest.raises(IntelligenceFailure) as exc:ProposalEngine(provider).extract({**request(),'timeout_seconds':3})
    assert exc.value.code==code
    assert 'private' not in str(exc.value) and 'synthetic-key' not in str(exc.value)
    assert len(calls)==1 and calls[0][1]['timeout']==3
    assert 'source_snapshot' in calls[0][1]['json']['messages'][1]['content']


def test_real_transport_validates_the_multi_candidate_schema_not_a_single_result(monkeypatch):
    raw=result();raw['candidates'].append(deepcopy(raw['candidates'][0]));raw['candidates'][1]['candidate_id']='other';raw['candidates'][1]['terms']['description']='A second reviewed term'
    monkeypatch.setattr(requests,'post',lambda *a,**kw:SimpleNamespace(status_code=200,content=b'valid',json=lambda:{'choices':[{'message':{'content':json.dumps(raw)},'finish_reason':'stop'}]}))
    out=ProposalEngine(StructuredProposalProvider(MetaProvider(api_key='synthetic-key'))).extract(request())
    assert len(out['candidates'])==2
    assert len({c['candidate_id'] for c in out['candidates']})==2


def test_invalid_metadata_is_rejected_before_any_provider_operation():
    class NoCalls:
        def extract_proposals(self,*a,**k):raise AssertionError('must not call')
    invalid=request();invalid['evidence'][0]['communication']={'date':'2026-11-31','precision':'date'}
    with pytest.raises(IntelligenceFailure) as exc:ProposalEngine(NoCalls()).extract(invalid)
    assert exc.value.code=='VALIDATION_ERROR'
