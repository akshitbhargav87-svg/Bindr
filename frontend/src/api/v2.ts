/** Contract v1 transport for /api/v2. Fixtures are injected by tests, never imported here. */
import {accountContext,accountHeaders,assertAccountContext,sessionEnded} from './account-context';
import {ApiError} from './types';
import {validDay} from './capture-validation';

export interface Money {currency:string;amount_minor:number}
export interface V2Terms {kind:'refund'|'replacement'|'service'|'other';description:string;amount_minor:number|null;currency:string|null;due_at:string|null}
export interface V2Citation {evidence_id:string;quote:string;page?:number|null;message_id?:string|null;start_ms?:number|null;end_ms?:number|null}
export interface ProposalCandidate {candidate_id:string;terms:V2Terms;sources:V2Citation[];temporal:{wording:string|null;anchor:string|null;duration:string|null;range:string|null;parse_status:string};relation:{kind:string;predecessor_id:string|null;explanation:string};condition:{trigger:string|null;status:string};warnings:string[]}
export interface Proposal {schema_version:2;proposal_id:string;candidates:ProposalCandidate[];document_warnings:string[]}
export interface ReviewDecision {candidate_id:string;selected:boolean;terms:V2Terms;predecessor_ids:string[];action?:'confirm'|'cancel'|'corroborate';deadline_override?:{date:string;timezone:string;precision:'date'};reason?:string}
export interface ReviewDraft {selected:Record<string,boolean>;edits:Record<string,V2Terms>;amounts:Record<string,string>;predecessors:Record<string,string>;dates:Record<string,string>;reasons:Record<string,string>}
export interface Obligation {id:string;terms:V2Terms;semantic_status:string;deadline_proposal:unknown;outcomes:unknown[];balance:Money[]}
export interface CaseSnapshot {id:string;version:number;obligations:Obligation[];events:unknown[];evidence?:{id:string;filename:string}[];legacy_commitments?:unknown[];title?:string;merchant_name?:string;projection:{status:string;money_by_currency:Money[];as_of:string;timezone:string};capabilities:string[]}
export interface Job {id:string;status:'queued'|'running'|'review_required'|'succeeded'|'failed'|'cancelled';stage:string;retryable:boolean;request_id:string;error?:{code:string;message:string}|null;resource_id?:string;version?:number}
export interface CaseAnswer {answer:string|null;citations:V2Citation[];abstention:string|null;version:number}
export function caseAnswer(v:unknown):CaseAnswer {const a=object(v);if((a.answer!==null && typeof a.answer!=='string') || (a.abstention!==null && typeof a.abstention!=='string') || !Number.isSafeInteger(a.version) || !Array.isArray(a.citations))throw new Error('Invalid grounded answer.');for(const value of a.citations){const c=object(value);if(typeof c.evidence_id!=='string' || typeof c.quote!=='string' || !c.quote.trim())throw new Error('Invalid answer citation.');}if(!a.abstention && (!a.answer || !a.citations.length))throw new Error('An answer requires grounded citations or an explicit abstention.');return a as unknown as CaseAnswer;}
export interface Communication {date:string|null;time:string|null;timezone:string;precision:'unknown'|'date'|'timestamp';provenance:'user_confirmed'|'message_metadata'|'extracted';original_wording:string|null}
export interface Operation {key:string;payload:string;state:'ready'|'pending'|'uncertain'|'succeeded';result?:unknown;account_id?:string;scope?:string}
export function operation(payload:unknown):Operation {return {key:crypto.randomUUID(),payload:JSON.stringify(payload),state:'ready'};}
const object=(v:unknown):Record<string,unknown>=>{if(!v || typeof v!=='object' || Array.isArray(v))throw new Error('Invalid v2 response.');return v as Record<string,unknown>;};
function money(v:unknown):Money {const x=object(v);if(typeof x.currency!=='string' || !/^[A-Z]{3}$/.test(x.currency) || !Number.isSafeInteger(x.amount_minor) || (x.amount_minor as number)<0)throw new Error('Invalid authoritative money.');return x as unknown as Money;}
export function snapshot(v:unknown):CaseSnapshot {
  const x=object(v),p=object(x.projection);
  if(typeof x.id!=='string' || !Number.isSafeInteger(x.version) || (x.version as number)<1 || !Array.isArray(x.obligations) || !Array.isArray(x.events) || !Array.isArray(x.capabilities) || !x.capabilities.every(v=>typeof v==='string') || typeof p.status!=='string' || typeof p.as_of!=='string' || !Number.isFinite(Date.parse(p.as_of)) || !/(Z|[+-]\d\d:\d\d)$/.test(p.as_of) || typeof p.timezone!=='string' || !Array.isArray(p.money_by_currency))throw new Error('Invalid case snapshot.');
  p.money_by_currency.forEach(money);
  const ids=new Set();
  x.obligations.forEach(v=>{const o=object(v);if(typeof o.id!=='string' || ids.has(o.id) || typeof o.semantic_status!=='string' || !Array.isArray(o.balance) || !Array.isArray(o.outcomes))throw new Error('Invalid obligation.');ids.add(o.id);validateTerms(o.terms);o.balance.forEach(money);});
  return x as unknown as CaseSnapshot;
}
export function createdCase(v:unknown):{id:string;version:number}{const envelope=object(v),c=envelope.case ? object(envelope.case) : envelope;if(typeof c.id!=='string' || !Number.isSafeInteger(c.version) || (c.version as number)<1)throw new Error('The created case could not be verified. Keep this operation key.');return c as unknown as {id:string;version:number};}
export function validateTerms(v:unknown):V2Terms {
  const t=object(v);
  if(!['refund','replacement','service','other'].includes(String(t.kind)) || typeof t.description!=='string' || !t.description.trim() || t.description.length>2000)throw new Error('Review the promise terms.');
  if(t.amount_minor!==null){money({amount_minor:t.amount_minor,currency:t.currency});}else if(t.currency!==null)throw new Error('Pair amount and currency.');
  if(t.due_at!==null && (typeof t.due_at!=='string' || !/(Z|[+-]\d\d:\d\d)$/.test(t.due_at) || !Number.isFinite(Date.parse(t.due_at)) || !validDay(t.due_at.slice(0,10))))throw new Error('Review the proposed date.');
  return t as unknown as V2Terms;
}
export function proposal(v:unknown):Proposal {const p=object(v);if(p.schema_version!==2 || typeof p.proposal_id!=='string' || !Array.isArray(p.candidates) || p.candidates.length>50 || !Array.isArray(p.document_warnings) || !p.document_warnings.every(w=>typeof w==='string'))throw new Error('Invalid proposal.');const ids=new Set();for(const value of p.candidates){const c=object(value),temporal=object(c.temporal),relation=object(c.relation),condition=object(c.condition);if(typeof c.candidate_id!=='string' || ids.has(c.candidate_id) || !Array.isArray(c.sources) || !c.sources.length || !Array.isArray(c.warnings) || !c.warnings.every(w=>typeof w==='string') || typeof temporal.parse_status!=='string' || typeof relation.kind!=='string' || typeof relation.explanation!=='string' || typeof condition.status!=='string')throw new Error('Invalid candidate.');ids.add(c.candidate_id);validateTerms(c.terms);for(const value of c.sources){const s=object(value);if(typeof s.evidence_id!=='string' || typeof s.quote!=='string' || !s.quote)throw new Error('Invalid citation.');}}return p as unknown as Proposal;}
export function job(v:unknown):Job {const j=object(v);if(typeof j.id!=='string' || !['queued','running','review_required','succeeded','failed','cancelled'].includes(String(j.status)) || typeof j.stage!=='string' || typeof j.retryable!=='boolean' || typeof j.request_id!=='string')throw new Error('Invalid job.');return j as unknown as Job;}
export function extractionResponse(v:unknown):{proposal:Proposal|null;job:Job|null;case_version:number|null}{
  const r=object(v);
  const version=r.case_version;
  if(version!==undefined && (!Number.isSafeInteger(version) || (version as number)<1))throw new Error('Invalid extraction case version.');
  const proposalValue=r.schema_version===2 ? r : r.proposal;
  return {proposal:proposalValue ? proposal(proposalValue) : null,job:proposalValue ? null : job(r.job ?? r),case_version:version===undefined ? null : version as number};
}

export class V2Client {
  constructor(private base='/api/v2',private transport:typeof fetch=fetch){}
  async request<T>(path:string,decode:(value:unknown)=>T,options:{method?:string;body?:unknown;operation?:Operation;fingerprint?:string}={}):Promise<T> {
    const owner=accountContext();if(!owner.id)throw new Error('Sign in before opening private records.');
    if(!path.startsWith('/') || path.startsWith('//') || /[?#]/.test(path))throw new Error('Invalid API path.');
    const method=options.method ?? 'GET',write=method!=='GET';
    const op=options.operation;
    if(write && !op)throw new Error('A stable operation key is required.');
    if(op?.account_id && op.account_id!==owner.id)throw new Error('This operation belongs to a different account.');
    const scope=method+' '+path;
    if(op?.scope && op.scope!==scope)throw new Error('This operation belongs to a different action or case.');
    if(op)op.account_id=owner.id;
    if(op)op.scope=scope;
    if(options.body instanceof FormData && !options.fingerprint)throw new Error('Multipart operations require an original-byte fingerprint.');
    if(op && op.payload!==(options.fingerprint ?? JSON.stringify(options.body)))throw new Error('This operation key belongs to different content. Start a new operation.');
    if(op?.state==='pending')throw new Error('This operation is already running.');
    if(op?.state==='succeeded')return decode(op.result);
    const headers:Record<string,string>={...accountHeaders()};
    if(write){
      const cookies=document.cookie.split(/;\s*/);
      const cookie=['__Host-bindr_csrf','bindr_csrf','pk_csrf'].map(name=>cookies.find(v=>v.startsWith(name+'='))).find(Boolean);
      if(!cookie)throw new Error('Reload your authenticated workspace to restore its session token.');
      headers['X-CSRF-Token']=decodeURIComponent(cookie.slice(cookie.indexOf('=')+1));
      headers['Idempotency-Key']=op!.key;
      if(!(options.body instanceof FormData))headers['Content-Type']='application/json';
    }
    if(op)op.state='pending';
    const abort=new AbortController(),timer=setTimeout(()=>abort.abort(),45000);
    try {
      const response=await this.transport(this.base+path,{method,credentials:'include',cache:'no-store',redirect:'error',headers,signal:abort.signal,body:write ? options.body instanceof FormData ? options.body : JSON.stringify(options.body) : undefined});
      assertAccountContext(owner);
      // An expired session must clear identity even when a proxy returns HTML.
      if(response.status===401){sessionEnded();throw new ApiError(401,{code:'AUTH_REQUIRED',message:'Please sign in again. Your capture remains in this tab.',details:[],request_id:''});}
      const data=await response.json();assertAccountContext(owner);
      if(!response.ok){if(response.status===401)sessionEnded();const envelope=object(data).error;const e=object(envelope);if(typeof e.code!=='string' || typeof e.message!=='string' || !Array.isArray(e.details) || typeof e.request_id!=='string')throw new Error('The server could not complete this operation.');throw new ApiError(response.status,e as unknown as ConstructorParameters<typeof ApiError>[1]);}
      const value=decode(data);if(op){op.result=data;op.state='succeeded';}return value;
    }catch(e){if(op)op.state='uncertain';throw e;}finally{clearTimeout(timer);}
  }
  case(id:string){return this.request(`/cases/${encodeURIComponent(id)}`,snapshot);}
  job(id:string){return this.request(`/jobs/${encodeURIComponent(id)}`,job);}
  mutate<T>(path:string,body:unknown,op:Operation,decode:(value:unknown)=>T){return this.request(path,decode,{method:'POST',body,operation:op});}
}

export async function prepareEvidenceUpload(file:File,expected_version:number,communication:Communication,previous?:Operation){
  if(!file.size || file.size>10*1024*1024)throw new Error('Choose a nonempty original up to 10 MiB.');
  if(communication.date!==null && !validDay(communication.date))throw new Error('Review the communication date.');
  const sha256=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',await file.arrayBuffer()))).map(v=>v.toString(16).padStart(2,'0')).join('');
  const fingerprint=JSON.stringify({filename:file.name,size:file.size,sha256,expected_version,communication});
  const op=previous ?? {key:crypto.randomUUID(),payload:fingerprint,state:'ready' as const};
  if(op.payload!==fingerprint)throw new Error('The original or metadata changed. Review the previous upload before starting another operation.');
  const body=new FormData();body.append('file',file);body.append('expected_version',String(expected_version));body.append('communication',JSON.stringify(communication));
  return {body,fingerprint,operation:op};
}
export function uploadResult(v:unknown){const r=object(v),e=object(r.evidence);if(typeof e.id!=='string' || !Number.isSafeInteger(r.case_version) || (r.duplicate_of!==null && r.duplicate_of!==undefined && typeof r.duplicate_of!=='string'))throw new Error('The upload response could not be verified. Keep this operation key for reconciliation.');return r as unknown as {evidence:{id:string};case_version:number;duplicate_of:string|null};}

/** Opaque capture data only; server authorization/version checks remain mandatory. */
export class DraftAutosave {
  private queued:Promise<unknown>=Promise.resolve();
  constructor(private client:V2Client,private accountId:string){}
  save(id:string|null,body:unknown,op:Operation){
    const save=async()=>{if(accountContext().id!==this.accountId)throw new Error('Sign in to the same account before restoring this draft.');return this.client.request(id ? `/capture-drafts/${encodeURIComponent(id)}` : '/capture-drafts',object,{method:id ? 'PUT' : 'POST',body,operation:op});};
    const next=this.queued.then(save,save);this.queued=next.catch(()=>{});return next;
  }
}
