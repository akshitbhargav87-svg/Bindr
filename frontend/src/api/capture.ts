import { api, isMock } from './index';
import { mockApi, MOCK_TODAY } from './mock';
import { ApiError, type Candidate, type Terms } from './types';
import type { CaptureInput, CaptureJob, ReviewFields, Scenario } from './capture-model';
import { dayInIndia, termsFromFields, validateFile } from './capture-validation';
export { validateFile } from './capture-validation';

export function sampleOptions() {return [
  ['standard','Clear refund promise'], ['multiple','Several promises'], ['vague','“Soon” without a date'], ['date-review','Date needs clarification'],
  ['no-promise','No promise found'], ['duplicate','Possible duplicate'], ['ai-error','Extraction unavailable'], ['save-error','Save fails once'],
] as [Scenario,string][];}
export function captureSample(scenario: Scenario) {
  const text = scenario === 'multiple' ? 'We will refund INR 3299 for your returned order within 3 business days.\n\nWe will deliver the replacement cable by 2026-11-20.'
    : scenario === 'vague' ? 'We confirm we will refund INR 3299 for your returned order soon.'
    : scenario === 'date-review' ? 'We will refund INR 3299 for your returned order by 04/05. Thank you for your patience.'
    : scenario === 'no-promise' ? 'Thank you for contacting Meadow Audio. Your support request is being reviewed.'
    : scenario === 'duplicate' ? 'We will refund INR 4999 for the returned headphones within 5 business days.'
    : 'We will refund INR 3299 for your returned order within 3 business days.';
  return {company:scenario === 'duplicate' ? 'NovaMart' : 'Meadow Audio', title:scenario === 'duplicate' ? 'Refund for returned headphones' : 'Refund for returned order', text, communicationDate:scenario === 'duplicate' ? '2026-11-02' : MOCK_TODAY};
}
export function reviewFields(candidates: Candidate[]): ReviewFields[] {
  return candidates.map(c=>({id:c.candidate_id,selected:true,kind:c.terms.kind,description:c.terms.description,amount:c.terms.amount_minor===null ? '' : String(c.terms.amount_minor/100),deadline:c.terms.due_at ? dayInIndia(c.terms.due_at) : '',originalDueAt:c.terms.due_at,quote:c.sources[0]?.quote ?? null,warnings:[...c.warnings],explanation:c.terms.due_at ? 'Review the date against the source. Edited date-only deadlines end at 23:59 in Asia/Kolkata.' : 'Choose a confirmed date, or leave it unset. A missing date never means overdue.'}));
}
export function manualFields(): ReviewFields[] {return [{id:'manual',selected:true,kind:'refund',description:'',amount:'',deadline:'',originalDueAt:null,quote:null,warnings:[],explanation:'Entered by you. Choose a confirmed date or leave it unset.'}];}
export function deadlineSummary(field: ReviewFields): string {
  if(!field.deadline)return 'This will be saved as Needs a date.';
  if(field.originalDueAt && dayInIndia(field.originalDueAt)===field.deadline) {
    const stamp=new Intl.DateTimeFormat('en-IN',{timeZone:'Asia/Kolkata',day:'numeric',month:'short',year:'numeric',hour:'2-digit',minute:'2-digit',hourCycle:'h23'}).format(new Date(field.originalDueAt));
    return `Deadline: ${stamp} (Asia/Kolkata). The extracted time is preserved.`;
  }
  return `Chosen date: ${field.deadline}. Date-only deadlines end at 23:59 in Asia/Kolkata.`;
}
export function supportingFragment(field: ReviewFields, kind:'amount'|'deadline'):string | null {
  if(!field.quote)return null;
  const match=kind==='amount' ? field.quote.match(/(?:₹|INR\s*)[\d,]+(?:\.\d{1,2})?/i) : field.quote.match(/within\s+\d+(?:\s*[-–]\s*\d+)?\s*(?:business\s+)?days?|by\s+[^.]+|soon|shortly/i);
  return match?.[0] ?? null;
}
export function captureError(cause: unknown): string {
  return cause instanceof Error ? cause.message : 'That request could not be completed. Your input is still here.';
}
type Update = (job: CaptureJob, progress: string) => void;
export async function prepareCapture(input: CaptureInput, prior: CaptureJob | null, update: Update, simulateFailure = false, manualOnly = false): Promise<CaptureJob> {
  if(!input.company.trim() || input.company.trim().length>200 || !input.title.trim() || input.title.trim().length>200) throw new Error('Enter a company and case title, up to 200 characters each.');
  if(!input.sources.length || input.sources.length>10) throw new Error('Choose between 1 and 10 source files or paste a message.');
  for(const source of input.sources) {const problem=validateFile(source.file,isMock);if(problem) throw new Error(problem);}
  if(prior?.state==='needs-reconciliation') throw new Error('Check the latest case state before retrying this request.');
  let job=prior?.caseId ? structuredClone(prior) : null;
  try {
    if(!job) {
      update({caseId:'',version:0,evidenceIds:[],uploadedKeys:[],extractionId:null,candidates:[],duplicateId:null,state:'ready'},'Preparing the case');
      const result=await api.createCase({title:input.title.trim(),merchant_name:input.company.trim()});
      job={caseId:result.case.id,version:result.case.version,evidenceIds:[],uploadedKeys:[],extractionId:null,candidates:[],duplicateId:null,state:'ready'};
      update({...job},'Keeping the original evidence');
    }
    // An explicit re-analysis must not recover an older draft after a lost response.
    if(job.extractionId)job.ignoredExtractionIds=[...(job.ignoredExtractionIds ?? []),job.extractionId];
    job.extractionId=null;job.candidates=[];delete job.reviewEvidenceIds;
    for(const [index,source] of input.sources.entries()) {
      let id=job.evidenceIds[job.uploadedKeys.indexOf(source.key)];
      if(!id) {
        const hash=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',await source.file.arrayBuffer()))).map(n=>n.toString(16).padStart(2,'0')).join('');
        job.pendingUpload={key:source.key,filename:source.file.name.split(/[\\/]/).at(-1)!.replace(/[\u0000-\u001f]/g,''),sha256:hash};
        update({...job},`Keeping source ${index+1} of ${input.sources.length}`);
        const result=await api.uploadEvidence(job.caseId,source.file,job.version);
        id=result.evidence.id;job.version=result.case_version;job.uploadedKeys.push(source.key);job.evidenceIds.push(id);
        delete job.pendingUpload;
        update(structuredClone(job),'Original evidence kept');
      }
      // GAP: communication date is unsupported by the upload contract. Mock metadata only.
      if(isMock) mockApi.setCommunicationDate(id,source.communicationDate);
    }
    const currentIds=input.sources.map(s=>job!.evidenceIds[job!.uploadedKeys.indexOf(s.key)]);
    job.reviewEvidenceIds=currentIds;
    if(manualOnly) {update(structuredClone(job),'Ready for manual entry');return job;}
    if(simulateFailure) throw new ApiError(503,{code:'AI_UNAVAILABLE',message:'Extraction is unavailable right now. Retry or enter the promise manually.',details:[],request_id:'demo'});
    update({...job},'Finding the promise and its supporting words');
    const result=await api.extract(job.caseId,currentIds,job.version);
    job.version=result.case_version;job.extractionId=result.extraction.id;job.candidates=result.extraction.candidates;
    // GAP: no duplicate-detection endpoint. Local mock suggestion never merges cases.
    if(isMock) {
      const {cases}=await api.listCases();
      job.duplicateId=cases.find(c=>c.id!==job!.caseId && c.merchant_name.toLowerCase()===input.company.trim().toLowerCase() && c.title.toLowerCase()===input.title.trim().toLowerCase())?.id ?? null;
    }
    update(structuredClone(job),'Ready for your review');return job;
  } catch(cause) {
    if(!(cause instanceof ApiError) || cause.status===409) {
      job ??= {caseId:'',version:0,evidenceIds:[],uploadedKeys:[],extractionId:null,candidates:[],duplicateId:null,state:'ready'};
      job.state='needs-reconciliation';update(structuredClone(job),'Check the latest state before retrying');
    }
    throw cause;
  }
}
export async function reconcileCapture(job: CaptureJob): Promise<CaptureJob> {
  if(!job.caseId) throw new Error('The create request result could not be verified. Do not repeat it automatically; check the backend case list with the team before starting again.');
  const detail=await api.getCase(job.caseId);
  const reconciled=structuredClone(job);
  if(job.pendingUpload) {
    const matches=detail.evidence.filter(e=>!job.evidenceIds.includes(e.id) && e.sha256===job.pendingUpload!.sha256 && e.filename===job.pendingUpload!.filename);
    if(matches.length>1)throw new Error('Several matching uploads exist. Check the case with the team before retrying; the original file is preserved in this tab.');
    if(matches.length===1) {reconciled.evidenceIds.push(matches[0].id);reconciled.uploadedKeys.push(job.pendingUpload.key);}
    delete reconciled.pendingUpload;
  }
  const expected=job.reviewEvidenceIds ?? reconciled.evidenceIds;
  const matching=detail.extractions.find(e=>e.id===job.extractionId) ?? detail.extractions.filter(e=>!job.ignoredExtractionIds?.includes(e.id) && e.evidence_ids.length===expected.length && e.evidence_ids.every(id=>expected.includes(id))).at(-1);
  if(matching && matching.status!=='pending_review') throw new Error('This draft has already been reviewed. Open the current case instead of saving it again.');
  return {...reconciled,version:detail.case.version,extractionId:matching?.id ?? job.extractionId,candidates:matching?.candidates ?? job.candidates,state:'ready'};
}
export async function confirmCapture(job: CaptureJob, fields: ReviewFields[], manual: boolean, simulateFailure = false, identity?: {company:string;title:string}): Promise<void> {
  if(job.state!=='ready') throw new Error('Reload the latest case state before confirming.');
  const chosen=fields.filter(f=>f.selected);
  if(!chosen.length) throw new Error('Select at least one promise to track.');
  const terms: Terms[]=chosen.map(termsFromFields);
  if(identity && (!identity.company.trim() || identity.company.trim().length>200 || !identity.title.trim() || identity.title.trim().length>200)) throw new Error('Review the company and case title (1–200 characters each).');
  if(simulateFailure) throw new ApiError(503,{code:'DEMO_SAVE_FAILURE',message:'The promise could not be saved. Your reviewed values are preserved. Try again.',details:[],request_id:'demo'});
  if(manual) {
    // GAP: manual-only HTTP creation does not exist. Never invent a request shape.
    if(!isMock) throw new Error('This backend cannot save a manual-only promise yet. Your values are kept here; retry extraction to use the supported review flow.');
    await mockApi.saveManual(job.caseId,job.version,terms,job.evidenceIds);
    if(identity)mockApi.updateIdentity(job.caseId,identity.company.trim(),identity.title.trim());return;
  }
  if(!job.extractionId) throw new Error('No extraction draft is available.');
  await api.review(job.caseId,job.extractionId,{expected_version:job.version,decision:'approve',items:chosen.map((f,i)=>({candidate_id:f.id,action:'new',supersedes_id:null,terms:terms[i],evidence_ids:job.candidates.find(c=>c.candidate_id===f.id)!.sources.map(s=>s.evidence_id)}))});
  if(isMock && identity)mockApi.updateIdentity(job.caseId,identity.company.trim(),identity.title.trim());
}
export async function retainEvidence(job: CaptureJob) {
  if(!job.extractionId) throw new Error('No extraction draft is available.');
  await api.review(job.caseId,job.extractionId,{expected_version:job.version,decision:'reject',items:[]});
}
