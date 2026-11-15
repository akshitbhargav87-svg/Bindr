/** Track A ba2e389 wire profile -> B's presentation models. No fixture fallbacks. */
import {V2Client,operation,type Operation,type CaseSnapshot,type Proposal,type V2Citation,type V2Terms} from './v2';
type Data=Record<string,any>;
const record=(v:unknown):Data=>{if(!v || typeof v!=='object' || Array.isArray(v))throw new Error('Invalid platform response.');return v as Data;};
const communication=(date:string|null=null)=>({date,time:null,timezone:'Asia/Kolkata',precision:date ? 'date' : 'unknown',provenance:'user_confirmed',original_wording:null});
function citation(v:Data):V2Citation{return {evidence_id:v.evidence_id,quote:v.quote,page:v.page ?? null,message_id:v.message_id ?? null,start_ms:v.start_seconds==null ? null : v.start_seconds*1000,end_ms:v.end_seconds==null ? null : v.end_seconds*1000};}
export function platformProposal(value:unknown):Proposal {
  const p=record(value);return {...p,candidates:p.candidates.map((c:Data)=>({...c,sources:c.sources.map(citation),
    temporal:{wording:c.temporal.original_wording,anchor:c.temporal.anchor?.date ?? null,duration:c.temporal.duration?.wording ?? null,range:c.temporal.range?.wording ?? null,parse_status:c.temporal.parse_status},
    condition:{trigger:c.condition.text ?? null,status:c.condition.text ? c.condition.fulfilled===true ? 'confirmed' : 'unknown' : 'not_applicable'}}))} as Proposal;
}
export function platformSnapshot(value:unknown):CaseSnapshot {
  const p=record(value),events=p.events,caseValue=record(p.case);
  const capabilities=Object.entries(record(p.capabilities)).filter(([,available])=>available===true).map(([name])=>name==='export' ? 'exports' : name);
  // These routes are implemented by the pinned platform profile; external delivery remains disabled.
  capabilities.push('reviews','questions','calendar','lifecycle','delete');
  const totals=record(p.projection.money_by_currency);
  return {id:caseValue.id,version:p.version,capabilities,events,evidence:p.evidence,legacy_commitments:p.legacy_commitments,
    title:caseValue.title,merchant_name:caseValue.merchant_name,
    obligations:p.obligations.map((o:Data)=>({...o,deadline_proposal:o.deadline,sources:o.sources.map(citation),
      outcomes:events.filter((e:Data)=>e.payload?.allocations?.some((a:Data)=>a.root_id===o.root_id)),
      balance:o.outstanding_minor===null ? [] : [{currency:o.terms.currency,amount_minor:o.outstanding_minor}]})),
    projection:{...p.projection,money_by_currency:Object.entries(totals).map(([currency,v])=>({currency,amount_minor:record(v).outstanding_minor}))}} as CaseSnapshot;
}
function platformJob(value:unknown){const envelope=record(value),j=record(envelope.job ?? envelope);return {...j,export_id:envelope.export_id,status:j.state,resource_id:j.resource?.export_id ?? j.resource?.proposal_id,version:j.case_version};}
function explicitDate(day:{date:string;timezone:string}){return {anchor:communication(),anchor_confirmed:false,conditional:false,expression:'User reviewed date override',unit:'explicit_date',minimum:0,maximum:0,explicit_date:day.date,calendar_id:'weekend_only',calendar_version:'1'};}
export function platformBody(path:string,body:unknown,method:string):unknown {
  if(body===undefined || body instanceof FormData)return body;const b=record(body);
  if(path.endsWith('/reviews'))return {expected_version:b.expected_version,proposal_id:b.proposal_id,decisions:b.decisions.map((d:Data)=>({candidate_id:d.candidate_id,action:!d.selected ? 'reject' : d.action ?? 'confirm',edited_terms:d.terms,predecessor_id:d.predecessor_ids[0] ?? null,...(d.deadline_override ? {deadline:explicitDate(d.deadline_override),deadline_override_reason:d.reason} : {})}))};
  if(path.endsWith('/outcomes'))return {...b,allocations:b.allocations.map(({currency:unused,...a}:Data)=>a)};
  if(path.endsWith('/manual-promises'))return {expected_version:b.expected_version,terms:b.terms,origin:'user_attested',sources:[],confirmed:true};
  if(path.startsWith('/capture-drafts')){const capture={text:b.text,communication:communication(b.metadata.communicationDate || null),evidence_ids:b.source_references};return method==='POST' ? {capture} : {expected_version:b.expected_version,capture};}
  if(path.endsWith('/exports')){const {selected_evidence,...rest}=b;return {...rest,source_ids:selected_evidence ?? b.source_ids ?? []};}
  if(method==='DELETE' && /^\/cases\/[^/]+$/.test(path))return {...b,confirmation:'DELETE'};
  return body;
}
function normalize(path:string,method:string,value:unknown):unknown {
  const v=record(value);
  if(method==='GET' && /^\/cases\/[^/]+$/.test(path))return platformSnapshot(v);
  if(path.endsWith('/extractions'))return {...v,proposal:platformProposal(v.proposal)};
  if(path.startsWith('/jobs/') || path.endsWith('/exports') || method==='DELETE')return platformJob(v);
  if(path.startsWith('/capture-drafts')){const d=record(v.draft);return {id:d.id,version:d.version,text:d.capture.text,metadata:{company:'',title:'',communicationDate:d.capture.communication.date ?? ''},source_references:d.capture.evidence_ids};}
  if(path.endsWith('/questions'))return {version:v.version,answer:v.status==='answered' ? v.answer : null,abstention:v.status==='insufficient_evidence' ? v.answer : null,citations:v.citations.map((c:Data)=>{const [evidence_id,,page]=c.citation_id.split(':');return {evidence_id,quote:c.quote,page:Number(page)};})};
  return v;
}
export class PlatformClient extends V2Client {
  private wires=new WeakMap<Operation,Operation>();
  override async request<T>(path:string,decode:(value:unknown)=>T,options:Parameters<V2Client['request']>[2]={}):Promise<T>{
    const method=options?.method ?? 'GET',body=platformBody(path,options?.body,method),original=options?.operation;
    let wire:Operation|undefined;
    if(original){
      if(original.payload!==(options?.fingerprint ?? JSON.stringify(options?.body)))throw new Error('This operation belongs to changed input. Reconcile it before retrying.');
      wire=this.wires.get(original);if(!wire){wire={...operation(body),key:original.key,payload:options?.fingerprint ?? JSON.stringify(body)};this.wires.set(original,wire);}
    }
    try{return await super.request(path,v=>decode(normalize(path,method,v)),{...options,body,operation:wire});}
    finally{if(original && wire){original.state=wire.state;original.account_id=wire.account_id;original.scope=wire.scope;}}
  }
  async download(path:string){
    // Original private downloads require current tab account headers and reject switches.
    const {accountContext,accountHeaders,assertAccountContext,sessionEnded}=await import('./account-context');
    const owner=accountContext();if(!owner.id)throw new Error('Sign in before downloading private data.');
    if(!/^\/cases\/[^/]+\/calendar\.ics$|^\/exports\/[^/]+\?download=true$/.test(path))throw new Error('Invalid private download path.');
    const response=await fetch('/api/v2'+path,{credentials:'include',cache:'no-store',redirect:'error',headers:accountHeaders()});assertAccountContext(owner);
    if(!response.ok){if(response.status===401)sessionEnded();throw new Error('Private download unavailable. Check its job and sign-in state.');}
    const blob=await response.blob();assertAccountContext(owner);return blob;
  }
}
export function mutationResult(value:unknown){const v=record(value);if(!Number.isSafeInteger(v.case_version) || v.case_version<1)throw new Error('Invalid mutation case version.');return v as {case_version:number};}
