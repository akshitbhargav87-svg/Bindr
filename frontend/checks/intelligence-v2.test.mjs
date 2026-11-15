import test from 'node:test';
import assert from 'node:assert/strict';
import {build} from 'esbuild';
import {serveFixture} from './fixtures/v2-server.mjs';
const code=(await build({stdin:{contents:"export * from './src/api/v2';export * from './src/api/workflow';export * from './src/api/account-context';export * from './src/api/capture-draft';",resolveDir:process.cwd()},bundle:true,format:'esm',platform:'node',write:false})).outputFiles[0].text;
const m=await import(`data:text/javascript;base64,${Buffer.from(code).toString('base64')}`);
globalThis.document={cookie:'bindr_csrf=synthetic-csrf'};
test('v2 HTTP fixture: review, partial/pending/full/reopen, replay, stale state, privacy and deletion',async()=>{
  const server=await serveFixture();let owner='account-a';
  const transport=(url,options)=>fetch(url,{...options,headers:{...options.headers,'X-Fixture-Owner':owner}});
  const client=new m.V2Client(server.base,transport),workflow=new m.Workflow(client);
  m.setAccountContext(owner);
  try{
    const create={title:'Refund',merchant_name:'Shop'},op=m.operation(create);
    const c=await client.mutate('/cases',create,op,m.snapshot);
    assert.deepEqual(await client.mutate('/cases',create,op,m.snapshot),c);
    assert.equal((await client.mutate('/cases',create,m.operation(create),m.snapshot)).id===c.id,false);
    const proposal=await client.mutate(`/cases/${c.id}/extractions`,{expected_version:1,evidence_ids:['source-1']},m.operation({expected_version:1,evidence_ids:['source-1']}),m.proposal);
    const body={expected_version:1,proposal_id:proposal.proposal_id,decisions:proposal.candidates.map(p=>({candidate_id:p.candidate_id,selected:true,terms:p.terms,predecessor_ids:[]}))};
    await workflow.review(c.id,body,m.operation(body));let current=await client.case(c.id);
    assert.equal(current.obligations.length,1);assert.equal(current.projection.money_by_currency[0].amount_minor,50000);
    let input={expected_version:current.version,kind:'partial',allocations:[{obligation_id:current.obligations[0].id,amount_minor:20000,currency:'INR'}],received_at:null,note:'Received ₹200',source_ids:[]};
    const receipt=m.operation(input);await workflow.outcome(c.id,input,receipt);await workflow.outcome(c.id,input,receipt);current=await client.case(c.id);
    assert.equal(current.projection.money_by_currency[0].amount_minor,30000);assert.equal(current.obligations[0].outcomes.length,1);
    await assert.rejects(()=>workflow.outcome(c.id,input,m.operation(input)),e=>e.status===409);
    for(const kind of ['pending','company_claim']){input={...input,expected_version:current.version,kind,allocations:[{...input.allocations[0],amount_minor:null,currency:null}]};await workflow.outcome(c.id,input,m.operation(input));current=await client.case(c.id);assert.equal(current.projection.money_by_currency[0].amount_minor,30000);}
    input={...input,expected_version:current.version,kind:'full',allocations:[{...input.allocations[0],amount_minor:30000,currency:'INR'}]};await workflow.outcome(c.id,input,m.operation(input));current=await client.case(c.id);assert.equal(current.obligations[0].semantic_status,'fulfilled');
    const reopen={expected_version:current.version,action:'reopen',reason:'Receipt disputed'};await client.mutate(`/cases/${c.id}/lifecycle`,reopen,m.operation(reopen),m.snapshot);current=await client.case(c.id);assert.equal(current.obligations[0].balance[0].amount_minor,0);assert.equal(current.obligations[0].outcomes.length,4);
    owner='account-b';m.setAccountContext(owner);await assert.rejects(()=>client.case(c.id),e=>e.status===404);
    owner='account-a';m.setAccountContext(owner);const deletion={expected_version:current.version,confirmation:c.id};const j=await client.request(`/cases/${c.id}`,m.job,{method:'DELETE',body:deletion,operation:m.operation(deletion)});assert.equal((await client.job(j.id)).stage,'cleanup');await assert.rejects(()=>client.case(c.id),e=>e.status===404);
  }finally{await server.close();}
});
test('uncertain transport retains operation key and changed payload is blocked',async()=>{
  m.setAccountContext('a');let keys=[],calls=0;
  const client=new m.V2Client('/api/v2',async(url,o)=>{keys.push(o.headers['Idempotency-Key']);if(++calls===1)throw new TypeError('Network lost');return Response.json({ok:true});});
  const body={expected_version:2,note:'same'},op=m.operation(body);
  await assert.rejects(()=>client.mutate('/cases/a/outcomes',body,op,v=>v));assert.equal(op.state,'uncertain');await client.mutate('/cases/a/outcomes',body,op,v=>v);assert.equal(keys[0],keys[1]);
  await assert.rejects(()=>client.mutate('/cases/a/outcomes',{...body,note:'changed'},op,v=>v),/different content/);assert.equal(calls,2);
});
test('operation replay is bound to its action and case, including cached success',async()=>{
  m.setAccountContext('scope-owner');let calls=0;
  const client=new m.V2Client('/api/v2',async()=>{calls++;return Response.json({confirmed:true});});
  const body={expected_version:1},op=m.operation(body);
  await client.mutate('/cases/first/outcomes',body,op,v=>v);
  await assert.rejects(()=>client.mutate('/cases/second/outcomes',body,op,v=>v),/different action or case/);
  await assert.rejects(()=>client.request('/cases/first/outcomes',v=>v,{method:'DELETE',body,operation:op}),/different action or case/);
  assert.equal(calls,1);
});
test('v2 writes prefer the current host CSRF cookie and reject malformed cookies before transport',async()=>{
  m.setAccountContext('csrf-owner');let seen,calls=0;
  const client=new m.V2Client('/api/v2',async(url,options)=>{calls++;seen=options.headers['X-CSRF-Token'];return Response.json({ok:true});});
  const before=document.cookie;try{
    document.cookie='pk_csrf=stale; bindr_csrf=account; __Host-bindr_csrf=host%2Daccount';
    await client.mutate('/cases',{},m.operation({}),v=>v);assert.equal(seen,'host-account');
    document.cookie='pk_csrf=stale; __Host-bindr_csrf=%broken';
    await assert.rejects(()=>client.mutate('/cases',{},m.operation({}),v=>v));assert.equal(calls,1);
  }finally{document.cookie=before;}
});
test('an HTML 401 clears account identity and preserves the uncertain operation for same-account recovery',async()=>{
  m.setAccountContext('expired-owner');
  const client=new m.V2Client('/api/v2',async()=>new Response('<html>session expired</html>',{status:401,headers:{'Content-Type':'text/html'}}));
  const op=m.operation({});await assert.rejects(()=>client.mutate('/cases',{},op,v=>v),e=>e.status===401);
  assert.equal(m.accountContext().id,null);assert.equal(op.state,'uncertain');assert.equal(op.account_id,'expired-owner');
});
test('malformed extraction envelopes remain uncertain and an exact retry can decode a versioned proposal',async()=>{
  m.setAccountContext('extract-owner');let calls=0;const keys=[];
  const p={schema_version:2,proposal_id:'proposal-1',candidates:[],document_warnings:[]};
  const client=new m.V2Client('/api/v2',async(url,options)=>{keys.push(options.headers['Idempotency-Key']);return Response.json(++calls===1 ? {proposal:{schema_version:2,candidates:'invalid'}} : {proposal:p,case_version:4});});
  const body={expected_version:3,evidence_ids:['e1']},op=m.operation(body);
  await assert.rejects(()=>client.mutate('/cases/a/extractions',body,op,m.extractionResponse));assert.equal(op.state,'uncertain');
  const result=await client.mutate('/cases/a/extractions',body,op,m.extractionResponse);assert.equal(result.case_version,4);assert.equal(result.proposal.proposal_id,'proposal-1');assert.equal(calls,2);assert.equal(keys[0],keys[1]);
  assert.equal(m.extractionResponse(p).case_version,null);
  assert.equal(m.extractionResponse({job:{id:'j1',status:'queued',stage:'provider',retryable:false,request_id:'r1'},case_version:3}).job.status,'queued');
  assert.throws(()=>m.extractionResponse({proposal:p,case_version:0}));
});
test('future/invalid proposals, zero-decimal currencies, aggregates and offline manifest verifier',async()=>{
  assert.throws(()=>m.validateTerms({kind:'refund',description:'Refund',amount_minor:5,currency:'INR',due_at:'2026-11-31T10:00:00Z'}));
  assert.match(m.formatAuthoritativeMoney({currency:'JPY',amount_minor:500}),/500/);
  assert.equal(m.aggregateDisplay({eligible:1,fulfilled:1,minimum_sample:20,period:'November',method:'Self-reported',privacy_reviewed:true}).suppressed,true);
  assert.equal(m.aggregateDisplay({eligible:25,fulfilled:10,minimum_sample:20,period:'November',method:'Self-reported',privacy_reviewed:true}).rate,.4);
  const file=new File(['original'],'proof.txt');const digest=Buffer.from(await crypto.subtle.digest('SHA-256',await file.arrayBuffer())).toString('hex');const manifest={files:[{name:file.name,sha256:digest,size:file.size}]};assert.equal((await m.verifyManifest([file],manifest))[0].verified,true);assert.equal((await m.verifyManifest([new File(['tampered'],'proof.txt')],manifest))[0].verified,false);
});
test('original-byte upload replay, duplicate warning, account-bound cloud autosave and ISO money editing',async()=>{
  const server=await serveFixture();let owner='a';m.setAccountContext(owner);
  const client=new m.V2Client(server.base,(url,options)=>fetch(url,{...options,headers:{...options.headers,'X-Fixture-Owner':owner}}));
  try{
    const body={title:'Draft test',merchant_name:'Synthetic'},c=await client.mutate('/cases',body,m.operation(body),m.createdCase);
    const communication={date:'2026-11-14',time:null,timezone:'Asia/Kolkata',precision:'date',provenance:'user_confirmed',original_wording:null};
    const file=new File(['original bytes'],'proof.txt',{type:'text/plain'}),first=await m.prepareEvidenceUpload(file,1,communication);
    const one=await client.request(`/cases/${c.id}/evidence`,m.uploadResult,{method:'POST',...first});const again=await client.request(`/cases/${c.id}/evidence`,m.uploadResult,{method:'POST',...first});assert.deepEqual(one,again);
    const second=await m.prepareEvidenceUpload(file,one.case_version,communication);const duplicate=await client.request(`/cases/${c.id}/evidence`,m.uploadResult,{method:'POST',...second});assert.equal(duplicate.duplicate_of,one.evidence.id);assert.equal(duplicate.case_version,one.case_version);
    await assert.rejects(()=>m.prepareEvidenceUpload(new File(['changed'],'proof.txt'),1,communication,first.operation),/changed/);
    const controller=new m.CaptureDraftController(new m.DraftAutosave(client,'a'),'a');
    const session={text:'Same-account draft',company:'Shop',title:'Refund',communicationDate:'2026-11-14',job:null};
    await controller.save(session);await controller.save({...session,text:'New exact words'});const draft=controller.current();assert.equal(draft.version,2);assert.equal(draft.text,'New exact words');
    owner='b';m.setAccountContext(owner);await assert.rejects(()=>controller.save(session),/same account/);await assert.rejects(()=>client.request(`/capture-drafts/${draft.id}`,m.captureDraft),e=>e.status===404);
    await assert.rejects(()=>client.mutate('/cases',body,first.operation,v=>v),/different account/);
    assert.equal(m.reviewedAmount('500','JPY'),500);assert.throws(()=>m.reviewedAmount('1.5','JPY'));assert.equal(m.reviewedAmount('1.234','KWD'),1234);
  }finally{await server.close();}
});
