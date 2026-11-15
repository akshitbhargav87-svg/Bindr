import pytest
from backend.app.tests.test_intelligence_contract import candidate, request, result, FixtureProvider
from backend.app.services.intelligence.extraction import ProposalEngine, IntelligenceFailure


@pytest.mark.parametrize('reason',['unrelated_kind','unknown_chronology','older_message','different_currency'])
def test_predecessor_suggestions_fail_conservatively_without_automatic_history_changes(reason):
    req=request();req['evidence'][0]['communication']={'date':'2026-11-14','precision':'date','provenance':'user_confirmed'}
    req['existing_obligations']=[{'id':'previous','case_id':'case-1','terms':{'kind':'refund','currency':'INR'},'communication':{'date':'2026-11-10','precision':'date','provenance':'user_confirmed'}}]
    c=candidate();c['relation']={'kind':'revision','predecessor_id':'previous','explanation':'Provider suggestion'}
    if reason=='unrelated_kind':req['existing_obligations'][0]['terms']['kind']='service'
    if reason=='unknown_chronology':del req['existing_obligations'][0]['communication']
    if reason=='older_message':req['existing_obligations'][0]['communication']['date']='2026-11-20'
    if reason=='different_currency':req['existing_obligations'][0]['terms']['currency']='USD'
    out=ProposalEngine(FixtureProvider(result(c))).extract(req)['candidates'][0]
    assert out['relation']['kind']=='uncertain' and out['relation']['predecessor_id'] is None
    assert req['existing_obligations'][0]['id']=='previous'


def test_known_chronology_keeps_a_review_only_revision_suggestion():
    req=request();req['evidence'][0]['communication']={'date':'2026-11-14','precision':'date','provenance':'user_confirmed'}
    req['existing_obligations']=[{'id':'previous','communication':{'date':'2026-11-10','precision':'date','provenance':'user_confirmed'}}]
    c=candidate();c['relation']={'kind':'revision','predecessor_id':'previous','explanation':'Source-linked suggestion, requires review'}
    out=ProposalEngine(FixtureProvider(result(c))).extract(req)
    assert out['candidates'][0]['relation']['kind']=='revision'
    assert 'confirmed' not in out and 'writes' not in out


def test_foreign_case_context_is_rejected_before_provider_use():
    req=request();req['existing_obligations']=[{'id':'foreign','case_id':'another-case'}]
    with pytest.raises(IntelligenceFailure) as exc:ProposalEngine(FixtureProvider(result())).extract(req)
    assert exc.value.code=='VALIDATION_ERROR'
