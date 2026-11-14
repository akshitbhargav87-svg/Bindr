import type { CaseDetail,Draft,Commitment } from './types';
import type { CaseExtras } from './case-model';
import type { ComplaintSelection,ComplaintSession } from './complaint-model';
import { date,money } from '../lib/format';
export const eligibleFacts=(detail:CaseDetail)=>detail.commitments.filter(c=>c.status==='active' || c.status==='superseded');
export function evidenceReference(detail:CaseDetail,id:string) {const index=detail.evidence.findIndex(e=>e.id===id);return index<0 ? 'Missing source' : `E-${String(index+1).padStart(2,'0')}`;}
export function validateSelection(detail:CaseDetail,selection:ComplaintSelection) {
  if(!selection.remedy.trim() || selection.remedy.trim().length>2000)throw new Error('Describe the requested resolution in 1–2000 characters.');
  const eligible=eligibleFacts(detail);const facts=eligible.filter(c=>selection.factIds.includes(c.id));
  if(!facts.length || !facts.some(c=>c.status==='active'))throw new Error('Include at least one current, confirmed promise.');
  if(new Set(selection.factIds).size!==selection.factIds.length || facts.length!==selection.factIds.length)throw new Error('Choose confirmed facts from this case.');
  const allowed=new Set(eligible.flatMap(c=>c.evidence_ids));
  if(!selection.evidenceIds.length || new Set(selection.evidenceIds).size!==selection.evidenceIds.length || selection.evidenceIds.some(id=>!allowed.has(id) || !detail.evidence.some(e=>e.id===id)))throw new Error('Choose linked evidence from the reviewed promises.');
  for(const fact of facts) {
    if(fact.supersedes_id && !selection.factIds.includes(fact.supersedes_id))throw new Error('Keep the earlier promise with its revision so the history stays complete.');
    if(!fact.evidence_ids.length || !fact.evidence_ids.every(id=>selection.evidenceIds.includes(id)))throw new Error('Include the original sources linked to each selected promise.');
  }
  return facts;
}
function factLine(detail:CaseDetail,c:Commitment) {
  const amount=c.amount_minor===null ? '' : `; amount ${money(c.amount_minor,c.currency ?? 'INR')}`;
  const deadline=c.due_at ? `; confirmed deadline ${date(c.due_at)} (Asia/Kolkata)` : '; no confirmed deadline';
  return `${c.supersedes_id ? 'Revised' : 'Original'} promise, confirmed ${date(c.reviewed_at)}: ${c.description}${amount}${deadline}. ${c.evidence_ids.map(id=>`[${evidenceReference(detail,id)}]`).join(' ')}`;
}
/** Deterministic local template. Uses reviewed facts; never calls a provider or sends a complaint. */
export function buildComplaintDocument(detail:CaseDetail,meta:CaseExtras,selection:ComplaintSelection):Draft {
  const facts=validateSelection(detail,selection).sort((a,b)=>Date.parse(a.reviewed_at)-Date.parse(b.reviewed_at));
  const history=facts.map(c=>{
    const candidate=detail.extractions.find(e=>e.id===c.extraction_id)?.candidates.find(v=>v.candidate_id===c.candidate_id);
    const quotes=candidate?.sources.filter(s=>selection.evidenceIds.includes(s.evidence_id)).map(s=>`[${evidenceReference(detail,s.evidence_id)}] “${s.quote}”`) ?? [];
    return [factLine(detail,c),...quotes].join('\n');
  }).join('\n\n');
  const allActiveSelected=detail.commitments.filter(c=>c.status==='active').every(c=>selection.factIds.includes(c.id));
  const monetary=facts.filter(c=>c.status==='active' && c.currency==='INR' && c.amount_minor!==null);
  const sum=monetary.reduce((n,c)=>n+c.amount_minor!,0);
  const outcome=meta.partiallyFulfilled ? meta.receivedMinor>0 && allActiveSelected ? `I have confirmed receipt of ${money(meta.receivedMinor)} against the confirmed total of ${money(sum)}. The remaining ${money(Math.max(0,sum-meta.receivedMinor))} is still outstanding.` : 'I have recorded partial fulfilment on this case. The remaining issue is described above.' : 'I have not confirmed fulfilment of the current promise.';
  return {subject:`Follow-up: ${detail.case.title}`.slice(0,200),body:`To ${detail.case.merchant_name} Customer Support,\n\nI am following up on ${detail.case.title}.\n\n${history}\n\n${outcome}\n\nRequested resolution:\n${selection.remedy.trim()}\n\nPlease confirm the outcome in writing.\n\nRegards,\n[Your name]`,evidence_ids:[...selection.evidenceIds]};
}
export function validateDraftText(subject:string,body:string) {
  if(!subject.trim() || subject.trim().length>200)throw new Error('Keep the subject between 1 and 200 characters.');
  if(!body.trim() || body.trim().length>10000)throw new Error('Keep the draft between 1 and 10,000 characters.');
}
export function exportEvidenceIds(session:ComplaintSession):string[] {
  const selection=session.snapshotSelection ?? session.selection;
  const facts=session.snapshot && session.includeHistory ? eligibleFacts(session.snapshot.detail).filter(c=>selection.factIds.includes(c.id)) : [];
  return [...new Set([...session.usedEvidenceIds,...facts.flatMap(c=>c.evidence_ids)])];
}
export function buildExportText(session:ComplaintSession):string {
  if(!session.snapshot)throw new Error('Prepare a draft before exporting.');
  validateDraftText(session.subject,session.body);
  const detail=session.snapshot.detail;
  const parts=[`Subject: ${session.subject.trim()}`,session.body];
  const selection=session.snapshotSelection ?? session.selection;
  if(session.includeHistory)parts.push(`Confirmed promise history\n${eligibleFacts(detail).filter(c=>selection.factIds.includes(c.id)).map(c=>factLine(detail,c)).join('\n\n')}`);
  if(session.includeEvidence)parts.push(`Evidence index (original files are not attached)\n${exportEvidenceIds(session).map(id=>{const e=detail.evidence.find(v=>v.id===id);if(!e)throw new Error('A referenced source is missing. Review the latest case first.');return `[${evidenceReference(detail,id)}] ${e.filename} · Added ${date(e.created_at)}`;}).join('\n')}`);
  return parts.join('\n\n');
}
