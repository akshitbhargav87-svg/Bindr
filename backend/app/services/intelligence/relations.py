"""Conservative checks on model-suggested predecessor links; never changes case state."""
def check_relation(candidate, request):
    relation=candidate.relation
    if relation.predecessor_id is None:
        return
    previous=next(o for o in request.existing_obligations if o['id']==relation.predecessor_id)
    terms=previous.get('terms',{})
    source_ids={s.evidence_id for s in candidate.sources}
    sources=[s for s in request.evidence if s.evidence_id in source_ids]
    dated=[s.communication.date for s in sources if s.communication.date and s.communication.provenance in {'user_confirmed','message_metadata'}]
    old_date=previous.get('communication',{}).get('date')
    reason=None
    if terms.get('kind') and terms['kind']!=candidate.terms.kind:
        reason='The suggested predecessor concerns a different kind of obligation.'
    elif terms.get('currency') and candidate.terms.currency and terms['currency']!=candidate.terms.currency:
        reason='The suggested predecessor uses a different currency; no conversion or revision was assumed.'
    elif relation.kind in {'revision','cancellation'} and (not old_date or len(dated)!=len(sources)):
        reason='Communication chronology is not confirmed, so a predecessor change remains uncertain.'
    elif relation.kind in {'revision','cancellation'} and any(d<old_date for d in dated):
        reason='The proposed source predates the selected predecessor. Review the chronology.'
    if reason:
        relation.kind='uncertain'
        relation.predecessor_id=None
        relation.explanation=reason
        candidate.warnings.append(reason)
