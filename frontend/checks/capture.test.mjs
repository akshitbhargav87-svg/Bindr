import {test} from 'node:test';
import assert from 'node:assert/strict';
import {build} from 'esbuild';
async function makeBundle(mock=true) {
  return (await build({stdin:{contents:"export * from './src/api/capture'; export * from './src/api/capture-validation'; export {mockApi,loadMockWorkspace} from './src/api/mock';",resolveDir:process.cwd()},bundle:true,format:'esm',platform:'node',write:false,define:{'import.meta.env':JSON.stringify({VITE_USE_MOCK:mock?'true':'false'})}})).outputFiles[0].text;
}
const code=await makeBundle();let runtimeId=0;
const runtime=async()=>import(`data:text/javascript;base64,${Buffer.from(code).toString('base64')}#${++runtimeId}`);
function input(m,scenario='standard') {
  const sample=m.captureSample(scenario);
  return {company:sample.company,title:sample.title,sources:[{key:'source-1',file:new File([sample.text],'company-message.txt',{type:'text/plain'}),communicationDate:sample.communicationDate,error:null}]};
}
test('file validation enforces supported types, empty files and the size ceiling',async()=>{
  const m=await runtime();
  assert.match(m.validateFile({size:0,type:'text/plain',name:'empty.txt'},true),/empty/);
  assert.match(m.validateFile({size:10485761,type:'application/pdf',name:'big.pdf'},true),/10 MB/);
  assert.equal(m.validateFile({size:10485760,type:'application/pdf',name:'ok.pdf'},false),null);
  assert.equal(m.validateFile({size:100,type:'image/png',name:'screen.png'},false),null);
  assert.equal(m.validateFile({size:100,type:'image/png',name:'screen.png'},true),null);
});
test('business-day counting and date-only conversion follow the confirmed calendar rules',async()=>{
  const m=await runtime();
  assert.equal(m.relativeMockDate('2026-11-02',5,true),'2026-11-09');
  assert.equal(m.relativeMockDate('2026-11-09',3,true),'2026-11-12');
  assert.equal(m.relativeMockDate('2026-11-14',3,true),'2026-11-18');
  assert.equal(m.validDay('2026-02-30'),false);
  assert.throws(()=>m.minorUnits('12.345'));
});
test('extraction creates a pending draft, never a tracked promise; confirmation adds it once',async()=>{
  const m=await runtime();const source=input(m);const job=await m.prepareCapture(source,null,()=>{});
  assert.equal((await m.loadMockWorkspace()).cases.length,5);
  const draft=await m.mockApi.getCase(job.caseId);
  assert.equal(draft.commitments.length,0);assert.equal(draft.extractions[0].status,'pending_review');
  assert.ok((await source.sources[0].file.text()).includes(job.candidates[0].sources[0].quote));
  await m.confirmCapture(job,m.reviewFields(job.candidates),false);
  const after=await m.mockApi.getCase(job.caseId);
  assert.equal(after.commitments.length,1);assert.equal(after.commitments[0].amount_minor,329900);
  assert.equal(after.commitments[0].due_at,'2026-11-18T18:29:59Z');
  assert.equal((await m.loadMockWorkspace()).cases.length,6);
  await assert.rejects(()=>m.confirmCapture(job,m.reviewFields(job.candidates),false),e=>e.status===409);
  assert.equal((await m.mockApi.getCase(job.caseId)).commitments.length,1);
});
test('several promises can be selected independently and only chosen ones are saved',async()=>{
  const m=await runtime();const job=await m.prepareCapture(input(m,'multiple'),null,()=>{});
  const fields=m.reviewFields(job.candidates);assert.equal(fields.length,2);fields[1].selected=false;
  await m.confirmCapture(job,fields,false);
  assert.equal((await m.mockApi.getCase(job.caseId)).commitments.length,1);
});
test('vague and ambiguous dates stay unset until a user supplies an explicit date',async()=>{
  const m=await runtime();
  for(const scenario of ['vague','date-review']) {
    const job=await m.prepareCapture(input(m,scenario),null,()=>{});const fields=m.reviewFields(job.candidates);
    assert.equal(fields[0].deadline,'');assert.equal(m.termsFromFields(fields[0]).due_at,null);
    fields[0].deadline='2026-11-20';assert.equal(m.termsFromFields(fields[0]).due_at,'2026-11-20T18:29:59Z');
  }
});
test('no-promise evidence is retained without inventing a commitment',async()=>{
  const m=await runtime();const job=await m.prepareCapture(input(m,'no-promise'),null,()=>{});
  assert.equal(job.candidates.length,0);await m.retainEvidence(job);
  const detail=await m.mockApi.getCase(job.caseId);assert.equal(detail.evidence.length,1);assert.equal(detail.commitments.length,0);assert.equal(detail.extractions[0].status,'rejected');
  assert.equal((await m.loadMockWorkspace()).cases.length,5);
});
test('save failure leaves reviewed values and database state intact; explicit retry works',async()=>{
  const m=await runtime();const job=await m.prepareCapture(input(m),null,()=>{});const fields=m.reviewFields(job.candidates);fields[0].amount='3000';
  await assert.rejects(()=>m.confirmCapture(job,fields,false,true),/could not be saved/);
  assert.equal(fields[0].amount,'3000');assert.equal((await m.mockApi.getCase(job.caseId)).commitments.length,0);
  await m.confirmCapture(job,fields,false);assert.equal((await m.mockApi.getCase(job.caseId)).commitments[0].amount_minor,300000);
});
test('stale versions cannot create a commitment, and reconciliation preserves editable values',async()=>{
  const m=await runtime();const job=await m.prepareCapture(input(m),null,()=>{});const fields=m.reviewFields(job.candidates);fields[0].description='Reviewed by user';
  await m.mockApi.uploadEvidence(job.caseId,new File(['Additional communication'],'extra.txt',{type:'text/plain'}),job.version);
  await assert.rejects(()=>m.confirmCapture(job,fields,false),e=>e.status===409);
  assert.equal((await m.mockApi.getCase(job.caseId)).commitments.length,0);
  const fresh=await m.reconcileCapture(job);await m.confirmCapture(fresh,fields,false);
  assert.equal((await m.mockApi.getCase(job.caseId)).commitments[0].description,'Reviewed by user');
});
test('extraction failure can be retried without uploading the original a second time',async()=>{
  const m=await runtime();const source=input(m);let job;
  await assert.rejects(()=>m.prepareCapture(source,null,value=>{job=value;},true),/unavailable/);
  assert.equal((await m.mockApi.getCase(job.caseId)).evidence.length,1);
  job=await m.prepareCapture(source,job,()=>{});
  assert.equal((await m.mockApi.getCase(job.caseId)).evidence.length,1);assert.equal(job.candidates.length,1);
});
test('duplicates are suggestions and never silently merge or confirm',async()=>{
  const m=await runtime();const job=await m.prepareCapture(input(m,'duplicate'),null,()=>{});
  assert.ok(job.duplicateId);assert.notEqual(job.duplicateId,job.caseId);
  assert.equal((await m.mockApi.getCase(job.caseId)).commitments.length,0);
});
test('manual fallback keeps the source but does not fabricate an AI quotation',async()=>{
  const m=await runtime();const job=await m.prepareCapture(input(m),null,()=>{},false,true);const fields=m.manualFields();
  assert.equal(fields[0].quote,null);fields[0].description='Refund entered by user';fields[0].amount='2500';
  await m.confirmCapture(job,fields,true);
  const detail=await m.mockApi.getCase(job.caseId);assert.equal(detail.evidence.length,1);assert.equal(detail.extractions.length,0);assert.equal(detail.commitments.length,1);
});
test('original bytes remain available and date edits preserve an explicit extracted time until changed',async()=>{
  const m=await runtime();const source=input(m);const job=await m.prepareCapture(source,null,()=>{});
  assert.deepEqual(await m.mockApi.getEvidenceFile(job.evidenceIds[0]).arrayBuffer(),await source.sources[0].file.arrayBuffer());
  const field=m.reviewFields(job.candidates)[0];field.originalDueAt='2026-11-18T06:30:00Z';
  assert.equal(m.termsFromFields(field).due_at,field.originalDueAt);
  assert.match(m.deadlineSummary(field),/12:00/);
  field.deadline='2026-11-19';assert.equal(m.termsFromFields(field).due_at,'2026-11-19T18:29:59Z');
  assert.match(m.deadlineSummary(field),/23:59/);
});
test('an upload with a lost response is reconciled by hash before any retry',async()=>{
  const http=await makeBundle(false);const m=await import(`data:text/javascript;base64,${Buffer.from(http).toString('base64')}#upload-recovery`);
  const oldFetch=globalThis.fetch;const oldDocument=globalThis.document;let uploads=0;let job;const source=input(m);
  const sha256=Buffer.from(await crypto.subtle.digest('SHA-256',await source.sources[0].file.arrayBuffer())).toString('hex');
  const item={id:'case-1',title:source.title,merchant_name:source.company,status:'open',version:1,resolution_note:null,resolved_at:null,created_at:'2026-11-14T09:00:00Z'};
  const evidence={id:'evidence-1',case_id:item.id,filename:'company-message.txt',media_type:'text/plain',size_bytes:source.sources[0].file.size,sha256,created_at:item.created_at,download_path:'/content'};
  const extraction={id:'draft-1',case_id:item.id,evidence_ids:[evidence.id],status:'pending_review',candidates:[],reviewed_commitment_ids:[],created_at:item.created_at};
  globalThis.document={cookie:''};globalThis.fetch=async(url,options)=>{if(url.endsWith('/auth/session'))return Response.json({session_id:'test',user_id:'anonymous-test',csrf_token:'token'});
    if(url.endsWith('/evidence')){uploads++;item.version=2;throw new TypeError('Upload response interrupted');}
    if(url.endsWith('/extractions'))return Response.json({extraction,case_version:3});
    if(options.method==='POST')return Response.json({case:item});
    return Response.json({case:item,evidence:[evidence],extractions:[],commitments:[]});
  };
  try {
    await assert.rejects(()=>m.prepareCapture(source,null,value=>{job=value;}));
    assert.equal(job.state,'needs-reconciliation');assert.equal(job.pendingUpload.sha256,sha256);
    job=await m.reconcileCapture(job);assert.deepEqual(job.evidenceIds,[evidence.id]);
    await m.prepareCapture(source,job,()=>{});assert.equal(uploads,1);
  } finally {globalThis.fetch=oldFetch;if(oldDocument===undefined)delete globalThis.document;else globalThis.document=oldDocument;}
});
test('unverifiable HTTP create result blocks further mutation instead of blind retry',async()=>{
  const http=await makeBundle(false);const m=await import(`data:text/javascript;base64,${Buffer.from(http).toString('base64')}`);
  const oldFetch=globalThis.fetch;const oldDocument=globalThis.document;let calls=0;let job;
  globalThis.document={cookie:''};globalThis.fetch=async()=>{calls++;throw new TypeError('Network request interrupted');};
  try {
    await assert.rejects(()=>m.prepareCapture(input(m),null,value=>{job=value;}));
    assert.equal(job.state,'needs-reconciliation');assert.equal(calls,1);
    await assert.rejects(()=>m.prepareCapture(input(m),job,()=>{}),/latest case state/);
    assert.equal(calls,1);
  } finally {globalThis.fetch=oldFetch;if(oldDocument===undefined)delete globalThis.document;else globalThis.document=oldDocument;}
});
test('re-analysis recovery never restores a prior draft for a replaced communication',async()=>{
  const m=await runtime();const initial=await m.prepareCapture(input(m),null,()=>{});
  const replacement=input(m);replacement.sources[0].key='replacement-source';replacement.sources[0].file=new File(['We will refund INR 3000 by 2026-11-25.'],'replacement.txt',{type:'text/plain'});
  let interrupted;
  await assert.rejects(()=>m.prepareCapture(replacement,initial,value=>{interrupted=value;},true),/unavailable/);
  assert.equal(interrupted.extractionId,null);
  const recovered=await m.reconcileCapture({...interrupted,state:'needs-reconciliation'});
  assert.equal(recovered.extractionId,null);assert.deepEqual(recovered.candidates,[]);
  const retry=await m.prepareCapture(replacement,recovered,()=>{});
  assert.equal(retry.candidates[0].terms.amount_minor,300000);
});


test('review preserves extracted currency and clears amount/currency together',async()=>{
  const m=await runtime();const source=input(m);const job=await m.prepareCapture(source,null,()=>{});const candidate=structuredClone(job.candidates[0]);candidate.terms.currency='USD';candidate.terms.amount_minor=12550;
  const field=m.reviewFields([candidate])[0];assert.equal(field.amount,'125.5');assert.equal(field.currency,'USD');assert.equal(m.termsFromFields(field).currency,'USD');assert.equal(m.termsFromFields(field).amount_minor,12550);
  field.kind='service';field.amount='';const cleared=m.termsFromFields(field);assert.equal(cleared.amount_minor,null);assert.equal(cleared.currency,null);
});
