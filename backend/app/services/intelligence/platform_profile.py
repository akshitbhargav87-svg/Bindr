"""Compatibility with Track A's published ba2e389 data-only intelligence profile."""
from hashlib import sha256
from .contracts import ProposalRequest
from .questions import answer_case


def extraction_request(request):
    context = request['context']
    evidence=[]
    for source in request['evidence']:
        pages=source.get('pages') or []
        segments=[{'text':p['text'],'page':p['page_number']} for p in pages if p.get('text','').strip()]
        if not segments:
            segments=[{'text':source['text']}]
        evidence.append({'evidence_id':source['evidence_id'],'segments':segments,
                         'communication':source.get('communication') or {}})
    operation=context['operation_id']
    return ProposalRequest.model_validate({'schema_version':2,'case_id':request['case_id'],
        'request_id':'op-'+sha256(operation.encode()).hexdigest()[:24],
        'timeout_seconds':context.get('timeout_seconds',60),'evidence':evidence,
        'existing_obligations':request.get('existing_obligations',[])}).model_dump()


def extraction_response(proposal, request):
    sources={s['evidence_id']:s for s in request['evidence']}
    candidates=[]
    for c in proposal['candidates']:
        refs=[]
        for ref in c['sources']:
            refs.append({'evidence_id':ref['evidence_id'],'quote':ref['quote'],
                         'page':ref.get('page'),'message_id':ref.get('message_id'),
                         'start_seconds':ref['start_ms']/1000 if ref.get('start_ms') is not None else None,
                         'end_seconds':ref['end_ms']/1000 if ref.get('end_ms') is not None else None})
        t=c['temporal'];condition=c['condition'];communication=sources[refs[0]['evidence_id']].get('communication')
        candidates.append({**c,'sources':refs,
            'temporal':{'original_wording':t['wording'],'anchor':communication,
                        'duration':{'wording':t['duration']} if t['duration'] else None,
                        'range':{'wording':t['range']} if t['range'] else None,
                        'parse_status':'invalid' if t['parse_status']=='invalid' else 'conditional' if condition['trigger'] else 'parsed' if t['parse_status'] in {'explicit','needs_calculation'} else 'unknown'},
            'condition':{'text':condition['trigger'],'fulfilled':None if condition['trigger'] else None}})
    if len(candidates)>30:
        # A's reviewed schema supports 30; never silently discard further candidates.
        raise ValueError('Platform review limit is 30 candidates. Split this intake explicitly.')
    operation=request['context']['operation_id']
    return {**proposal,'proposal_id':'p-'+sha256((proposal['proposal_id']+operation).encode()).hexdigest()[:32], 'candidates':candidates}


def answer_request(request):
    snapshot=request['snapshot'];case_id=snapshot['case_id']
    mapping={s['citation_id']:s for s in snapshot['sources']}
    if len(mapping)!=len(snapshot['sources']):
        raise ValueError('Duplicate authorized citation identity.')
    converted={'id':case_id,'version':snapshot['version'],'sources':[]}
    for source in snapshot['sources']:
        converted['sources'].append({'case_id':case_id,'evidence_id':source['citation_id'],
            'origin':'company_statement','segments':[{'text':source['text'],'page':source.get('page')}]})
    result=answer_case(converted,request['question'],snapshot['version'])
    return {'status':'insufficient_evidence' if result['abstention'] else 'answered',
            'answer':result['abstention'] or result['answer'],
            'citations':[{'citation_id':c['evidence_id'],'quote':c['quote']} for c in result['citations']]}
