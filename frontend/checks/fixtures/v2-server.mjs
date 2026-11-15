/** TEST ONLY. Synthetic profile for the frozen parallel contract; never a production backend. */
import http from 'node:http';
import {createHash} from 'node:crypto';
const copy=v=>structuredClone(v);
export function fixtureHandler({versionedExtraction=false}={}){
  let sequence=0;const cases=new Map(),operations=new Map(),drafts=new Map(),jobs=new Map(),evidence=new Map();
  const error=(status,code)=>Response.json({error:{code,message:code,details:[],request_id:'fixture-request'}},{status});
  const project=c=>copy(c.snapshot);
  return async request=>{
    const url=new URL(request.url),path=url.pathname.replace(/^\/api\/v2/,''),method=request.method;
    const owner=request.headers.get('X-Fixture-Owner'),expected=request.headers.get('X-Bindr-Account');
    if(!owner || owner!==expected)return error(401,'ACCOUNT_CHANGED');
    const parts=path.split('/').filter(Boolean),write=method!=='GET';
    let body={};
    if(write){
      if(!request.headers.get('X-CSRF-Token'))return error(403,'CSRF_FAILED');
      try{
        if((request.headers.get('Content-Type') ?? '').startsWith('multipart/form-data')){
          const form=await request.formData(),file=form.get('file');
          body={expected_version:Number(form.get('expected_version')),communication:JSON.parse(form.get('communication')),synthetic_bytes:Buffer.from(await file.arrayBuffer()).toString('base64'),filename:file.name};
        }else body=await request.json();
      }catch{return error(422,'INVALID_JSON');}
    }
    const c=parts[0]==='cases' && parts[1] ? cases.get(parts[1]) : null;
    if(parts[0]==='cases' && parts[1] && (!c || c.owner!==owner || c.deleted))return error(404,'NOT_FOUND');
    if(parts[0]==='capture-drafts' && parts[1] && drafts.get(parts[1])?.owner!==owner)return error(404,'NOT_FOUND');
    if(parts[0]==='jobs' && jobs.get(parts[1])?.owner!==owner)return error(404,'NOT_FOUND');
    const key=request.headers.get('Idempotency-Key'),scope=[owner,method,path,key].join(':'),payload=JSON.stringify(body);
    if(write){
      if(!key)return error(422,'OPERATION_KEY_REQUIRED');
      const previous=operations.get(scope);
      if(previous)return previous.payload===payload ? Response.json(copy(previous.result)) : error(409,'IDEMPOTENCY_CONFLICT');
      if(c && body.expected_version!==c.snapshot.version)return error(409,'VERSION_CONFLICT');
    }
    let result;
    if(path==='/cases' && method==='POST'){
      const id='case-'+ ++sequence;
      const snapshot={id,version:1,obligations:[],events:[],projection:{status:'review_required',money_by_currency:[],as_of:'2026-11-15T10:00:00Z',timezone:'Asia/Kolkata'},capabilities:['outcomes','reviews','exports','calendar','lifecycle','delete','questions']};
      cases.set(id,{owner,snapshot,proposal:null,deleted:false});result=project(cases.get(id));
    }else if(c && parts.length===2 && method==='GET')result=project(c);
    else if(c && parts[2]==='evidence' && method==='POST'){
      const digest=createHash('sha256').update(body.synthetic_bytes ?? '').digest('hex');
      const existing=evidence.get(parts[1]+':'+digest);
      if(existing)result={evidence:existing,duplicate_of:existing.id,case_version:c.snapshot.version};
      else{const ev={id:'evidence-'+ ++sequence,sha256:digest};evidence.set(parts[1]+':'+digest,ev);c.snapshot.version++;result={evidence:ev,duplicate_of:null,case_version:c.snapshot.version};}
    }else if(c && parts[2]==='extractions' && method==='POST'){
      c.proposal={schema_version:2,proposal_id:'proposal-'+ ++sequence,candidates:[{candidate_id:'refund-500',terms:{kind:'refund',description:'Refund ₹500',amount_minor:50000,currency:'INR',due_at:null},sources:[{evidence_id:'source-1',quote:'We will refund ₹500.'}],temporal:{wording:null,anchor:null,duration:null,range:null,parse_status:'unknown'},relation:{kind:'new',predecessor_id:null,explanation:'Synthetic fixture'},condition:{trigger:null,status:'not_applicable'},warnings:[]}],document_warnings:['Synthetic fixture; no model inference.']};result=c.proposal;
      if(versionedExtraction){c.snapshot.version++;result={proposal:c.proposal,case_version:c.snapshot.version};}
    }else if(c && parts[2]==='reviews' && method==='POST'){
      if(!c.proposal || body.proposal_id!==c.proposal.proposal_id)return error(409,'PROPOSAL_CLOSED');
      const decisions=body.decisions.filter(d=>d.selected);
      if(!decisions.length || decisions.some(d=>!c.proposal.candidates.some(p=>p.candidate_id===d.candidate_id)))return error(422,'INVALID_REVIEW');
      for(const d of decisions)c.snapshot.obligations.push({id:'obligation-'+ ++sequence,terms:copy(d.terms),semantic_status:'active',deadline_proposal:null,outcomes:[],balance:d.terms.amount_minor===null ? [] : [{currency:d.terms.currency,amount_minor:d.terms.amount_minor}]});
      c.proposal=null;c.snapshot.version++;c.snapshot.projection.status='active';c.snapshot.projection.money_by_currency=copy(c.snapshot.obligations[0]?.balance ?? []);result=project(c);
    }else if(c && parts[2]==='outcomes' && method==='POST'){
      for(const allocation of body.allocations){
        const obligation=c.snapshot.obligations.find(o=>o.id===allocation.obligation_id);
        if(!obligation)return error(422,'INVALID_ALLOCATION');
        if(['partial','full'].includes(body.kind)){
          const balance=obligation.balance.find(b=>b.currency===allocation.currency);
          if(!balance || !Number.isSafeInteger(allocation.amount_minor) || allocation.amount_minor<=0 || allocation.amount_minor>balance.amount_minor)return error(422,'INVALID_ALLOCATION');
          balance.amount_minor-=allocation.amount_minor;
          if(body.kind==='full' && balance.amount_minor===0)obligation.semantic_status='fulfilled';
        }else if(allocation.amount_minor!==null)return error(422,'CLAIM_IS_NOT_RECEIPT');
        obligation.outcomes.push({id:'outcome-'+ ++sequence,...copy(body)});
      }
      c.snapshot.version++;c.snapshot.projection.money_by_currency=copy(c.snapshot.obligations[0]?.balance ?? []);result=project(c);
    }else if(c && parts[2]==='lifecycle' && method==='POST'){
      if(body.action==='reopen')c.snapshot.obligations.forEach(o=>o.semantic_status='active');
      c.snapshot.events.push({action:body.action,reason:body.reason});c.snapshot.version++;result=project(c);
    }else if(c && parts.length===2 && method==='DELETE'){
      c.deleted=true;const id='job-'+ ++sequence;const j={id,status:'queued',stage:'cleanup',retryable:true,request_id:'fixture-delete',owner};jobs.set(id,j);result={...j};
    }else if(parts[0]==='jobs' && method==='GET'){const {owner:unused,...j}=jobs.get(parts[1]);result=j;}
    else if(path==='/capture-drafts' && method==='POST'){const id='draft-'+ ++sequence;const d={owner,id,version:1,...copy(body)};drafts.set(id,d);const {owner:unused,...publicDraft}=d;result=publicDraft;}
    else if(parts[0]==='capture-drafts' && method==='GET'){const {owner:unused,...d}=drafts.get(parts[1]);result=d;}
    else if(parts[0]==='capture-drafts' && method==='PUT'){const d=drafts.get(parts[1]);if(body.expected_version!==d.version)return error(409,'VERSION_CONFLICT');Object.assign(d,copy(body),{version:d.version+1});const {owner:unused,...publicDraft}=d;result=publicDraft;}
    else if(path==='/deadline-preview' && method==='POST'){
      if(body.expression==='November 31, 2026')result={earliest:null,latest:null,warnings:['Invalid date'],status:'invalid'};
      else if(body.communication?.date==='2026-12-28' && body.expression==='five calendar days')result={earliest:{date:'2027-01-02',timezone:'Asia/Kolkata',precision:'date'},latest:{date:'2027-01-02',timezone:'Asia/Kolkata',precision:'date'},warnings:[],explanation:'Synthetic golden response; A owns calendar arithmetic.'};
      else result={earliest:null,latest:null,status:'anchor_missing',warnings:['Confirm the communication anchor.']};
    }else return error(501,'FIXTURE_CAPABILITY_UNAVAILABLE');
    if(write)operations.set(scope,{payload,result:copy(result)});
    return Response.json(result);
  };
}
export async function serveFixture(options={}){
  const handler=fixtureHandler(options);const server=http.createServer(async(req,res)=>{
    try{const chunks=[];for await(const chunk of req)chunks.push(chunk);const response=await handler(new Request('http://localhost'+req.url,{method:req.method,headers:req.headers,body:['GET','HEAD'].includes(req.method) ? undefined : Buffer.concat(chunks)}));res.writeHead(response.status,Object.fromEntries(response.headers));res.end(Buffer.from(await response.arrayBuffer()));}catch{res.writeHead(500);res.end('{}');}
  });await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
  return {base:`http://127.0.0.1:${server.address().port}/api/v2`,close:()=>new Promise(resolve=>server.close(resolve))};
}
