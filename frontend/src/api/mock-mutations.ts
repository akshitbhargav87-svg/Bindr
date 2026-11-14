import { ApiError, type BindrApi, type CaseDetail, type Extraction, type Terms } from './types';
import { extractMockCandidates } from './mock-extraction';
import { validateFile } from './capture-validation';
function fail(code: string, message: string, status = 422): never {throw new ApiError(status,{code,message,details:[],request_id:crypto.randomUUID()});}
export function createMockApi(seed: CaseDetail[], created: CaseDetail[], today: string) {
  const files = new Map<string,{file:File; text:string; date:string}>();
  const now = () => `${today}T09:00:00Z`;
  const all = () => [...seed,...created];
  const get = (id: string) => all().find(d => d.case.id === id) ?? fail('NOT_FOUND','Case not found.',404);
  const check = (id: string, version: number) => {const d=get(id); if(d.case.status==='resolved') fail('CASE_RESOLVED','This case is resolved.',409); if(d.case.version!==version) fail('VERSION_CONFLICT','This case changed. Reload its latest state before saving.',409); return d;};
  const api: BindrApi & {
    setCommunicationDate(id: string, value: string): void;
    saveManual(id: string, version: number, items: Terms[], evidenceIds: string[]): Promise<void>;
    updateIdentity(id: string, company: string, title: string): void;
    getEvidenceFile(id: string): File | undefined;
  } = {
    listCases: async () => ({cases:structuredClone(all().map(d=>d.case))}),
    getCase: async id => structuredClone(get(id)),
    createCase: async data => {
      if(!data.title.trim() || data.title.trim().length>200 || !data.merchant_name.trim() || data.merchant_name.trim().length>200) fail('VALIDATION_ERROR','Company and case title must be 1–200 characters.');
      const item: CaseDetail={case:{id:crypto.randomUUID(),title:data.title.trim(),merchant_name:data.merchant_name.trim(),status:'open',version:1,resolution_note:null,resolved_at:null,created_at:now()},evidence:[],commitments:[],extractions:[]};
      created.push(item); return {case:structuredClone(item.case)};
    },
    uploadEvidence: async (id,file,version) => {
      const problem=validateFile(file,true);if(problem) fail('VALIDATION_ERROR',problem);
      check(id,version);
      let text='';
      if(file.type==='text/plain') {try{text=new TextDecoder('utf-8',{fatal:true}).decode(await file.arrayBuffer());}catch{fail('UNREADABLE_EVIDENCE','This file is not readable UTF-8 text. Paste the message instead.');}}
      if(text.includes('\u0000')) fail('UNREADABLE_EVIDENCE','This text file cannot be read. Paste the message instead.');
      const hash=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',await file.arrayBuffer()))).map(n=>n.toString(16).padStart(2,'0')).join('');
      const d=check(id,version);const evidenceId=crypto.randomUUID();
      const evidence={id:evidenceId,case_id:id,filename:file.name.split(/[\\/]/).at(-1)!.replace(/[\u0000-\u001f]/g,''),media_type:file.type,size_bytes:file.size,sha256:hash,created_at:now(),download_path:`/api/v1/cases/${id}/evidence/${evidenceId}/content`};
      d.evidence.push(evidence);files.set(evidenceId,{file,text,date:''});d.case.version++;
      return {evidence:structuredClone(evidence),case_version:d.case.version};
    },
    extract: async (id,ids,version) => {
      const d=check(id,version);if(!ids.length || ids.length>10 || new Set(ids).size!==ids.length || ids.some(e=>!d.evidence.some(v=>v.id===e))) fail('VALIDATION_ERROR','Choose 1–10 evidence files from this case.');
      if(ids.some(e=>!files.get(e)?.text)) fail('UNREADABLE_EVIDENCE','File text extraction is not connected in demo mode. Paste the readable message or continue manually.');
      if(ids.reduce((n,e)=>n+files.get(e)!.text.length,0)>50000) fail('VALIDATION_ERROR','Use at most 50,000 characters of source text.');
      let candidates;
      try{candidates=extractMockCandidates(ids.map(e=>({id:e,text:files.get(e)!.text,communicationDate:files.get(e)!.date})));}catch{fail('VALIDATION_ERROR','Clarify the source date or enter the promise manually.');}
      const extraction: Extraction={id:crypto.randomUUID(),case_id:id,evidence_ids:[...ids],status:'pending_review',candidates,reviewed_commitment_ids:[],created_at:now()};
      d.extractions.push(extraction);d.case.version++;return {extraction:structuredClone(extraction),case_version:d.case.version};
    },
    review: async(id,extractionId,payload) => {
      const d=check(id,payload.expected_version);const draft=d.extractions.find(e=>e.id===extractionId) ?? fail('NOT_FOUND','Review draft not found.',404);
      if(draft.status!=='pending_review') fail('DRAFT_CLOSED','This draft has already been reviewed.',409);
      if(payload.decision==='reject') {if(payload.items.length) fail('VALIDATION_ERROR','Rejected drafts cannot create promises.');draft.status='rejected';d.case.version++;return {extraction:structuredClone(draft),commitments:[],case_version:d.case.version};}
      if(!payload.items.length || payload.items.length>10 || new Set(payload.items.map(i=>i.candidate_id)).size!==payload.items.length) fail('VALIDATION_ERROR','Choose 1–10 distinct promises.');
      for(const item of payload.items) {
        if(!draft.candidates.some(c=>c.candidate_id===item.candidate_id) || item.action!=='new' || item.supersedes_id!==null) fail('INVALID_REVISION','This capture supports new promises. Revisions are handled in the case update flow.',409);
        if(!item.evidence_ids.length || !item.evidence_ids.some(e=>draft.evidence_ids.includes(e)) || item.evidence_ids.some(e=>!d.evidence.some(v=>v.id===e))) fail('VALIDATION_ERROR','Each promise needs its source evidence.');
        validateTerms(item.terms);
      }
      const commitments=payload.items.map(item=>({id:crypto.randomUUID(),case_id:id,extraction_id:extractionId,candidate_id:item.candidate_id,...structuredClone(item.terms),status:'active' as const,supersedes_id:null,evidence_ids:[...item.evidence_ids],reviewed_at:now(),created_at:now()}));
      d.commitments.push(...commitments);draft.status='reviewed';draft.reviewed_commitment_ids=commitments.map(c=>c.id);d.case.version++;
      return {extraction:structuredClone(draft),commitments:structuredClone(commitments),case_version:d.case.version};
    },
    // GAP: manual-only saving has no HTTP contract. Explicit local mock extension;
    // no AI extraction/quotation is invented for a user-entered promise.
    saveManual: async(id,version,items,evidenceIds) => {
      const d=check(id,version);items.forEach(validateTerms);
      if(!items.length || evidenceIds.some(e=>!d.evidence.some(v=>v.id===e))) fail('VALIDATION_ERROR','Manual promises need their original evidence.');
      d.commitments.push(...items.map((terms,index)=>({id:crypto.randomUUID(),case_id:id,extraction_id:crypto.randomUUID(),candidate_id:`c${index+1}`,...structuredClone(terms),status:'active' as const,supersedes_id:null,evidence_ids:[...evidenceIds],reviewed_at:now(),created_at:now()})));d.case.version++;
    },
    setCommunicationDate: (id,value) => {const file=files.get(id);if(file) file.date=value;},
    getEvidenceFile: id => files.get(id)?.file,
    // GAP: reviewed case identity edits have no HTTP endpoint. Mock-only local update.
    updateIdentity: (id,company,title) => {const d=get(id);d.case.merchant_name=company;d.case.title=title;},
    resolve: async()=>fail('PHASE_NOT_IMPLEMENTED','Outcome recording arrives in the case workflow.',501),
    complaint: async()=>fail('PHASE_NOT_IMPLEMENTED','Complaint drafting arrives in the complaint workflow.',501),
  };
  return api;
}
function validateTerms(t: Terms) {
  if(!t.description.trim() || t.description.length>2000 || !['refund','replacement','service','other'].includes(t.kind)) fail('VALIDATION_ERROR','Review the promise description and type.');
  if(t.amount_minor!==null && (!Number.isSafeInteger(t.amount_minor) || t.amount_minor<0)) fail('VALIDATION_ERROR','Review the amount.');
  if((t.amount_minor===null)!==(t.currency===null) || (t.kind==='refund' && t.amount_minor===null)) fail('VALIDATION_ERROR','Refunds need an amount and currency.');
  if(t.due_at!==null && !Number.isFinite(Date.parse(t.due_at))) fail('VALIDATION_ERROR','Review the deadline.');
}
