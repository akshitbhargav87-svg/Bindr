import { ApiError, type BindrApi, type CaseDetail, type Extraction, type Terms } from './types';
import { extractMockCandidates } from './mock-extraction';
import { validateFile } from './capture-validation';
import { emptyCaseExtras, type CaseExtras, type CaseEvent } from './case-model';
import { prepareSeedEvidence } from './seed-evidence';
function fail(code: string, message: string, status = 422): never {throw new ApiError(status,{code,message,details:[],request_id:crypto.randomUUID()});}
export function createMockApi(seed: CaseDetail[], created: CaseDetail[], today: string) {
  const files = new Map<string,{file:File; text:string; date:string}>();
  const extras=new Map<string,CaseExtras>();const deleted=new Set<string>();
  const ready=prepareSeedEvidence(seed,(id,file,text,date)=>files.set(id,{file,text,date}));
  const metadata=(id:string)=>{let value=extras.get(id);if(!value){value=emptyCaseExtras();extras.set(id,value);}return value;};
  let tick=0;
  // Ordered deterministic events within the fixed demo day; never use the browser clock.
  const now = () => new Date(Date.parse(`${today}T09:00:00Z`)+tick++).toISOString();
  const all = () => [...seed,...created].filter(d=>!deleted.has(d.case.id));
  const get = (id: string) => all().find(d => d.case.id === id) ?? fail('NOT_FOUND','Case not found.',404);
  const versioned=(id:string,version:number)=>{const d=get(id);if(d.case.version!==version)fail('VERSION_CONFLICT','This case changed. Reload its latest state before saving.',409);return d;};
  const check = (id: string, version: number) => {const d=versioned(id,version); if(d.case.status==='resolved') fail('CASE_RESOLVED','This case is resolved.',409);if(metadata(id).archived)fail('CASE_ARCHIVED','Restore this case before making changes.',409);return d;};
  const event=(id:string,kind:CaseEvent['kind'],title:string,note:string,evidenceIds:string[]=[],amountMinor:number|null=null,at=now())=>metadata(id).events.push({id:crypto.randomUUID(),kind,title,note,at,evidenceIds:[...evidenceIds],amountMinor});
  const total=(d:CaseDetail)=>{const values=d.commitments.filter(c=>c.status==='active' && c.currency==='INR' && c.amount_minor!==null);return values.length ? values.reduce((n,c)=>n+c.amount_minor!,0) : null;};
  const noteText=(note:string)=>{if(!note.trim() || note.trim().length>2000)fail('VALIDATION_ERROR','Add a note in 1–2000 characters.');return note.trim();};
  const api: BindrApi & {
    setCommunicationDate(id: string, value: string): void;
    saveManual(id: string, version: number, items: Terms[], evidenceIds: string[]): Promise<void>;
    updateIdentity(id: string, company: string, title: string): void;
    getEvidenceFile(id: string): File | undefined;
    getCaseExtras(id:string):CaseExtras;
    recordOutcome(id:string,version:number,kind:'partial'|'pending',note:string,amountMinor:number|null):Promise<void>;
    manageCase(id:string,version:number,action:'reopen'|'archive'|'restore'|'delete'|'edit',data:{note?:string;company?:string;title?:string;confirmation?:string}):Promise<void>;
    annotate(id:string,version:number,kind:'claim'|'update'|'review',note:string,evidenceIds:string[]):Promise<number>;
  } = {
    listCases: async () => {await ready;return {cases:structuredClone(all().map(d=>d.case))};},
    getCase: async id => {await ready;return structuredClone(get(id));},
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
      for(const candidate of candidates) {
        const active=d.commitments.filter(c=>c.status==='active' && c.kind===candidate.terms.kind);
        if(active.length)candidate.revision={relation:'uncertain',supersedes_id:null,reason:'A current promise of this type exists. Confirm whether this is a revision or a separate promise.'};
      }
      const extraction: Extraction={id:crypto.randomUUID(),case_id:id,evidence_ids:[...ids],status:'pending_review',candidates,reviewed_commitment_ids:[],created_at:now()};
      d.extractions.push(extraction);d.case.version++;return {extraction:structuredClone(extraction),case_version:d.case.version};
    },
    review: async(id,extractionId,payload) => {
      const d=check(id,payload.expected_version);const draft=d.extractions.find(e=>e.id===extractionId) ?? fail('NOT_FOUND','Review draft not found.',404);
      if(draft.status!=='pending_review') fail('DRAFT_CLOSED','This draft has already been reviewed.',409);
      if(payload.decision==='reject') {if(payload.items.length) fail('VALIDATION_ERROR','Rejected drafts cannot create promises.');draft.status='rejected';d.case.version++;return {extraction:structuredClone(draft),commitments:[],case_version:d.case.version};}
      if(!payload.items.length || payload.items.length>10 || new Set(payload.items.map(i=>i.candidate_id)).size!==payload.items.length) fail('VALIDATION_ERROR','Choose 1–10 distinct promises.');
      for(const item of payload.items) {
        if(!draft.candidates.some(c=>c.candidate_id===item.candidate_id))fail('VALIDATION_ERROR','Choose a suggestion from this draft.');
        if(item.action==='new' && item.supersedes_id!==null)fail('INVALID_REVISION','A new promise cannot replace another promise.',409);
        if(item.action==='revision') {
          const predecessor=d.commitments.find(c=>c.id===item.supersedes_id && c.status==='active');
          if(!predecessor || !predecessor.evidence_ids.every(e=>item.evidence_ids.includes(e)) || payload.items.filter(i=>i.action==='revision' && i.supersedes_id===item.supersedes_id).length>1)fail('INVALID_REVISION','Choose one current promise and preserve all its original evidence links.',409);
        } else if(item.action!=='new')fail('INVALID_REVISION','Choose new or revision.',409);
        if(!item.evidence_ids.length || !item.evidence_ids.some(e=>draft.evidence_ids.includes(e)) || item.evidence_ids.some(e=>!d.evidence.some(v=>v.id===e))) fail('VALIDATION_ERROR','Each promise needs its source evidence.');
        validateTerms(item.terms);
      }
      const replaced=new Set(payload.items.filter(i=>i.action==='revision').map(i=>i.supersedes_id));
      const newTotal=[...d.commitments.filter(c=>c.status==='active' && !replaced.has(c.id)),...payload.items.map(i=>i.terms)].filter(c=>c.currency==='INR' && c.amount_minor!==null).reduce((n,c)=>n+c.amount_minor!,0);
      if(newTotal<metadata(id).receivedMinor)fail('VALIDATION_ERROR','The revised total cannot be below receipts already confirmed. Review the outcome first.');
      const reviewedAt=now();
      const commitments=payload.items.map(item=>({id:crypto.randomUUID(),case_id:id,extraction_id:extractionId,candidate_id:item.candidate_id,...structuredClone(item.terms),status:'active' as const,supersedes_id:item.supersedes_id,evidence_ids:[...item.evidence_ids],reviewed_at:reviewedAt,created_at:reviewedAt}));
      d.commitments.filter(c=>replaced.has(c.id)).forEach(c=>{c.status='superseded';});
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
    getCaseExtras: id => {get(id);return structuredClone(metadata(id));},
    // GAP: reviewed case identity edits have no HTTP endpoint. Mock-only local update.
    updateIdentity: (id,company,title) => {const d=get(id);d.case.merchant_name=company;d.case.title=title;},
    resolve: async(id,version,note) => {
      const d=check(id,version);const value=noteText(note);const active=d.commitments.filter(c=>c.status==='active');
      if(!active.length)fail('NO_ACTIVE_COMMITMENT','There is no current promise to resolve.',409);
      metadata(id).receivedMinor=total(d) ?? 0;metadata(id).partiallyFulfilled=false;
      active.forEach(c=>{c.status='fulfilled';});d.case.status='resolved';d.case.resolution_note=value;d.case.resolved_at=now();d.case.version++;
      event(id,'resolved','Fulfilment confirmed by you',value,[],null,d.case.resolved_at);return {case:structuredClone(d.case)};
    },
    // GAP: extended lifecycle/outcomes are local-only until backend contracts exist.
    recordOutcome: async(id,version,kind,note,amountMinor)=>{
      const d=check(id,version);const value=noteText(note);const meta=metadata(id);const sum=total(d);
      if(!d.commitments.some(c=>c.status==='active'))fail('NO_ACTIVE_COMMITMENT','Confirm a promise before recording an outcome.',409);
      if(kind==='partial') {
        if(sum!==null && (amountMinor===null || !Number.isSafeInteger(amountMinor) || amountMinor<=0 || amountMinor>=sum-meta.receivedMinor))fail('VALIDATION_ERROR','A partial receipt must be positive and below the outstanding amount. Use full fulfilment for the full amount.');
        if(sum===null && amountMinor!==null)fail('VALIDATION_ERROR','Use a description for a non-monetary partial outcome.');
        meta.receivedMinor+=amountMinor ?? 0;meta.partiallyFulfilled=true;
      }
      event(id,kind,kind==='partial' ? 'Partial fulfilment confirmed by you' : 'Still waiting',value,[],kind==='partial' ? amountMinor : null);d.case.version++;
    },
    manageCase: async(id,version,action,data)=>{
      const d=versioned(id,version);const meta=metadata(id);
      if(action==='delete') {
        if(data.confirmation!==id)fail('VALIDATION_ERROR','Enter the exact case ID to delete it.');
        deleted.add(id);for(const e of d.evidence)files.delete(e.id);extras.delete(id);return;
      }
      if(action==='reopen') {
        if(d.case.status!=='resolved' || meta.archived)fail('VALIDATION_ERROR','Restore a resolved case before reopening it.');
        const reason=noteText(data.note ?? '');
        if(d.case.resolved_at && !meta.events.some(e=>e.kind==='resolved' && e.at===d.case.resolved_at))meta.events.push({id:crypto.randomUUID(),kind:'resolved',title:'Fulfilment confirmed by you',note:d.case.resolution_note ?? '',at:d.case.resolved_at,evidenceIds:[],amountMinor:null});
        d.case.status='open';d.case.resolved_at=null;d.case.resolution_note=null;
        d.commitments.filter(c=>c.status==='fulfilled').forEach(c=>{c.status='active';});meta.receivedMinor=0;meta.partiallyFulfilled=false;
        event(id,'reopened','Case reopened',reason);
      } else if(action==='archive') {
        if(meta.archived)fail('VERSION_CONFLICT','This case is already archived.',409);
        meta.archived=true;event(id,'archived','Case archived','Evidence and promise history retained.');
      } else if(action==='restore') {
        if(!meta.archived)fail('VERSION_CONFLICT','This case is already restored.',409);
        meta.archived=false;event(id,'restored','Case restored','Returned to your cases.');
      } else {
        if(meta.archived)fail('CASE_ARCHIVED','Restore this case before editing.',409);
        const company=data.company?.trim(),title=data.title?.trim();if(!company || company.length>200 || !title || title.length>200)fail('VALIDATION_ERROR','Company and title must contain 1–200 characters.');
        const reason=noteText(data.note ?? '');const before=`${d.case.merchant_name} · ${d.case.title}`;
        d.case.merchant_name=company;d.case.title=title;event(id,'edited','Case details corrected',`${reason}\nPreviously: ${before}`);
      }
      d.case.version++;
    },
    annotate: async(id,version,kind,note,evidenceIds)=>{
      const d=check(id,version);const value=noteText(note);if(!evidenceIds.length || evidenceIds.some(e=>!d.evidence.some(v=>v.id===e)))fail('VALIDATION_ERROR','Choose evidence from this case.');
      event(id,kind,kind==='claim' ? 'Company claims fulfilment · receipt unconfirmed' : kind==='review' ? 'Your revision decision' : 'Company update recorded',value,evidenceIds);d.case.version++;return d.case.version;
    },
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
