import { api,isMock } from './index';
import { mockApi,mockCaseRow,MOCK_TODAY } from './mock';
import { downloadHttpEvidence } from './http';
import { mapCaseRow } from './mapper';
import { ApiError,type Evidence,type CaseDetail } from './types';
import { emptyCaseExtras,type CaseView,type TimelineItem } from './case-model';
import type { CaptureJob,ReviewFields } from './capture-model';
import { minorUnits,termsFromFields } from './capture-validation';
export type { CaseView } from './case-model';
const message=(value:string)=>{if(!value.trim() || value.trim().length>2000)throw new Error('Add a note in 1–2000 characters.');return value.trim();};
export function caseReference(id:string) {return `BND-${id.slice(-8).toUpperCase()}`;}
export async function loadCase(id:string):Promise<CaseView> {
  const detail=await api.getCase(id);const meta=isMock ? mockApi.getCaseExtras(id) : emptyCaseExtras();const row=isMock ? mockCaseRow(detail) : mapCaseRow(detail);
  const current=detail.commitments.filter(c=>c.status===(detail.case.status==='resolved' ? 'fulfilled' : 'active'));
  const monetary=current.filter(c=>c.amount_minor!==null && c.currency===row.currency);
  const totalMinor=monetary.length ? monetary.reduce((n,c)=>n+c.amount_minor!,0) : null;
  return {detail,meta,row,totalMinor,outstandingMinor:detail.case.status==='resolved' ? totalMinor===null ? null : 0 : row.amountMinor};
}
export function sourceQuotes(detail:CaseDetail,commitmentId:string) {
  const commitment=detail.commitments.find(c=>c.id===commitmentId);
  return detail.extractions.find(e=>e.id===commitment?.extraction_id)?.candidates.find(c=>c.candidate_id===commitment?.candidate_id)?.sources ?? [];
}
export function caseTimeline(view:CaseView):TimelineItem[] {
  const {detail,meta}=view;
  const items:TimelineItem[]=[...detail.evidence.map(e=>({id:`file:${e.id}`,at:e.created_at,title:'Communication added',note:e.filename,evidenceIds:[e.id],kind:'evidence' as const})),...detail.commitments.map(c=>({id:c.id,at:c.reviewed_at,title:c.supersedes_id ? 'Revised promise confirmed' : 'Original promise confirmed',note:c.description,evidenceIds:c.evidence_ids,commitment:c,kind:'promise' as const})),...meta.events.map(e=>({...e,note:e.note,evidenceIds:e.evidenceIds,kind:'event' as const}))];
  if(detail.case.resolved_at && !meta.events.some(e=>e.kind==='resolved'))items.push({id:'resolution',at:detail.case.resolved_at,title:'Fulfilment confirmed by you',note:detail.case.resolution_note ?? '',evidenceIds:[],kind:'event'});
  return items.sort((a,b)=>Date.parse(a.at)-Date.parse(b.at));
}
export async function loadEvidenceFile(evidence:Evidence):Promise<Blob> {
  if(!isMock)return downloadHttpEvidence(evidence);
  // Authorization/case membership mirrors the raw API boundary in the local adapter.
  const detail=await api.getCase(evidence.case_id);
  const stored=detail.evidence.find(e=>e.id===evidence.id);const file=stored && mockApi.getEvidenceFile(stored.id);
  if(!file)throw new ApiError(404,{code:'NOT_FOUND',message:'The original file is unavailable. The linked history is still here.',details:[],request_id:''});
  return file;
}
export async function recordCaseOutcome(view:CaseView,input:{kind:'full'|'partial'|'pending';note:string;amount:string}) {
  const note=message(input.note);
  if(input.kind==='full') {await api.resolve(view.detail.case.id,view.detail.case.version,note);return;}
  if(!isMock)throw new Error('Partial outcomes and check-ins need backend support. Your entries are preserved.');
  const amount=input.kind==='partial' && view.totalMinor!==null ? minorUnits(input.amount) : null;
  await mockApi.recordOutcome(view.detail.case.id,view.detail.case.version,input.kind,note,amount);
}
export async function manageCase(view:CaseView,action:'reopen'|'archive'|'restore'|'delete'|'edit',data:{note?:string;company?:string;title?:string;confirmation?:string}) {
  // GAP: no lifecycle/edit endpoints are present in v1. Local demo only.
  if(!isMock)throw new Error('This action is not supported by the connected backend yet.');
  await mockApi.manageCase(view.detail.case.id,view.detail.case.version,action,data);
}
export async function listEvidence() {
  const {cases}=await api.listCases();const views:CaseView[]=[];let cursor=0;
  await Promise.all(Array.from({length:Math.min(4,cases.length)},async()=>{while(cursor<cases.length){const item=cases[cursor++];views.push(await loadCase(item.id));}}));
  const order=new Map(cases.map((c,i)=>[c.id,i]));return views.sort((a,b)=>order.get(a.detail.case.id)!-order.get(b.detail.case.id)!);
}
export async function reviewCommunication(job:CaptureJob,choices:{field:ReviewFields;action:'new'|'revision';predecessor:string|null}[],reason:string) {
  if(job.state!=='ready' || !job.extractionId)throw new Error('Check the latest draft before confirming.');
  if(!choices.length)throw new Error('Choose at least one promise.');
  const detail=await api.getCase(job.caseId);
  const items=choices.map(({field,action,predecessor})=>{
    const candidate=job.candidates.find(c=>c.candidate_id===field.id);if(!candidate)throw new Error('The selected suggestion is unavailable.');
    const previous=action==='revision' ? detail.commitments.find(c=>c.id===predecessor && c.status==='active') : null;
    if(action==='revision' && !previous)throw new Error('Choose the current promise this message revises.');
    if(action==='revision')message(reason);
    return {candidate_id:field.id,action,supersedes_id:previous?.id ?? null,terms:termsFromFields(field),evidence_ids:[...new Set([...(previous?.evidence_ids ?? []),...candidate.sources.map(s=>s.evidence_id)])]};
  });
  const result=await api.review(job.caseId,job.extractionId,{expected_version:job.version,decision:'approve',items});
  // GAP: decision notes have no HTTP field. Store them only in the local adapter.
  if(isMock && items.some(i=>i.action==='revision'))await mockApi.annotate(job.caseId,result.case_version,'review',reason.trim(),job.evidenceIds);
}
export async function keepCommunication(job:CaptureJob,kind:'update'|'claim',note:string) {
  if(job.state!=='ready')throw new Error('Check the latest case state before saving.');
  const value=message(note.trim() || (kind==='claim' ? 'Company claims fulfilment; receipt has not been confirmed.' : 'Company update retained as evidence.'));let version=job.version;
  if(job.extractionId)version=(await api.review(job.caseId,job.extractionId,{expected_version:version,decision:'reject',items:[]})).case_version;
  if(isMock)await mockApi.annotate(job.caseId,version,kind,value,job.evidenceIds);
  // GAP: HTTP retains the uploaded original/rejected draft, not note or claim metadata.
}
export function communicationSample(view:CaseView,kind:'revision'|'conflict'|'update'|'claim') {
  const amount=view.totalMinor===null ? '' : `INR ${view.totalMinor/100} `;
  const current=view.detail.commitments.find(c=>c.status==='active');
  const subject=current?.kind==='refund' ? `refund ${amount}for the returned order` : current?.kind==='replacement' ? 'deliver the replacement' : current?.kind==='service' ? `credit ${amount}to your account` : 'deliver the delayed parcel';
  return {text:kind==='update' ? 'Your request is still under processing. Thank you for your patience.' : kind==='claim' ? 'Your refund has been processed. Please check your account.' : `We will ${subject} by ${kind==='conflict' ? '2026-11-16' : '2026-11-20'}.`,communicationDate:MOCK_TODAY};
}
