import { api,isMock } from './index';
import { loadCase } from './case-service';
import { ApiError,type Draft } from './types';
import { mockApi } from './mock';
import type { CaseView } from './case-model';
import type { ComplaintSelection,ComplaintSession } from './complaint-model';
import { eligibleFacts,validateDraftText,validateSelection } from './complaint-document';
export { buildExportText,evidenceReference,eligibleFacts,exportEvidenceIds,validateDraftText } from './complaint-document';
export function initialSelection(view:CaseView):ComplaintSelection {
  const facts=eligibleFacts(view.detail);return {factIds:facts.map(c=>c.id),evidenceIds:[...new Set(facts.flatMap(c=>c.evidence_ids))],remedy:view.detail.commitments.find(c=>c.status==='active')?.kind==='refund' ? 'Complete the remaining refund and confirm the transaction reference in writing.' : 'Fulfil the outstanding promise and confirm the outcome in writing.'};
}
export function newComplaintSession(view:CaseView):ComplaintSession {return {selection:initialSelection(view),snapshotSelection:null,stage:'setup',snapshot:null,subject:'',body:'',usedEvidenceIds:[],mode:'generated',includeEvidence:true,includeHistory:true,exportConfirmed:false,preparedText:null,delivered:null,error:null,busy:false,needsRefresh:false,dirty:false};}
function openCase(view:CaseView) {
  if(view.meta.archived)throw new Error('Restore this case before preparing a complaint.');
  if(view.detail.case.status==='resolved' || !view.detail.commitments.some(c=>c.status==='active'))throw new Error('A complaint needs an unresolved, confirmed promise.');
}
export async function assertComplaintCurrent(snapshot:CaseView):Promise<CaseView> {
  const current=await loadCase(snapshot.detail.case.id);openCase(current);
  if(current.detail.case.version!==snapshot.detail.case.version)throw new ApiError(409,{code:'VERSION_CONFLICT',message:'The case changed after this draft was prepared. Reload the facts and prepare again; your wording is preserved until you replace it.',details:[],request_id:''});
  return current;
}
function validateResponse(draft:Draft,view:CaseView) {
  if(!draft || typeof draft.subject!=='string' || typeof draft.body!=='string')throw new Error('The draft response was incomplete. Your selected facts are preserved.');
  validateDraftText(draft.subject,draft.body);
  const allowed=new Set(eligibleFacts(view.detail).flatMap(c=>c.evidence_ids));
  if(!Array.isArray(draft.evidence_ids) || !draft.evidence_ids.length || new Set(draft.evidence_ids).size!==draft.evidence_ids.length || draft.evidence_ids.some(id=>!allowed.has(id) || !view.detail.evidence.some(e=>e.id===id)))throw new Error('The draft referenced an unavailable source. Review the case before trying again.');
}
export async function generateComplaint(view:CaseView,selection:ComplaintSelection,failOnce=false):Promise<Draft> {
  openCase(view);validateSelection(view.detail,selection);
  if(failOnce && isMock)throw new ApiError(503,{code:'AI_UNAVAILABLE',message:'The draft could not be prepared. Retry or start from the factual template. Your selections are still here.',details:[],request_id:'demo'});
  let draft:Draft;
  if(isMock) {
    await assertComplaintCurrent(view);
    // GAP: selected facts/evidence are a local extension; no such request fields exist.
    draft=(await mockApi.complaintSelected(view.detail.case.id,view.detail.case.version,selection)).draft;
  } else {
    const all=initialSelection(view);
    if(all.factIds.length!==selection.factIds.length || all.evidenceIds.length!==selection.evidenceIds.length)throw new Error('The connected backend uses the full reviewed record. Keep its facts selected and edit the generated wording.');
    const result=await api.complaint(view.detail.case.id,view.detail.case.version,selection.remedy.trim());
    if(result.case_version!==view.detail.case.version)throw new Error('The draft did not match this case version. Reload the facts before retrying.');
    draft=result.draft;
  }
  validateResponse(draft,view);await assertComplaintCurrent(view);return draft;
}
export function manualComplaint(view:CaseView,selection:ComplaintSelection) {
  openCase(view);validateSelection(view.detail,selection);
  const draft={subject:`Follow-up: ${view.row.title}`.slice(0,200),body:`To ${view.row.company} Customer Support,\n\nI am following up on ${view.row.title}.\n\n[Describe the confirmed promise, original and revised deadlines, and cite the supporting source references.]\n\n[Describe what remains unresolved. Include any receipt you have actually confirmed.]\n\nRequested resolution:\n${selection.remedy.trim()}\n\nPlease confirm the outcome in writing.\n\nRegards,\n[Your name]`,evidence_ids:[...selection.evidenceIds]};
  validateResponse(draft,view);return draft;
}
export async function prepareComplaintExport(session:ComplaintSession) {
  if(!session.snapshot || !session.exportConfirmed)throw new Error('Confirm that you reviewed the final wording and export contents.');
  await assertComplaintCurrent(session.snapshot);
  const {buildExportText}=await import('./complaint-document');return buildExportText(session);
}
