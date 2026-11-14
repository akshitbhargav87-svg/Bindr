import {test} from 'node:test';
import assert from 'node:assert/strict';
import {build} from 'esbuild';

async function bundle(mock=true) {
  return (await build({stdin:{contents:"export * from './src/api/case-service'; export {mockApi,loadMockWorkspace} from './src/api/mock'; export {prepareCapture,reviewFields} from './src/api/capture';",resolveDir:process.cwd()},bundle:true,format:'esm',platform:'node',write:false,define:{'import.meta.env':JSON.stringify({VITE_USE_MOCK:mock?'true':'false'})}})).outputFiles[0].text;
}
const code=await bundle();let serial=0;
const runtime=async()=>import(`data:text/javascript;base64,${Buffer.from(code).toString('base64')}#case-${++serial}`);
async function sample(m,company='NovaMart') {
  const {cases}=await m.loadMockWorkspace();
  return m.loadCase(cases.find(c=>c.company===company).id);
}
async function communication(m,view,text='We will refund INR 4999 for your returned headphones by 2026-11-20.') {
  return m.prepareCapture({company:view.detail.case.merchant_name,title:view.detail.case.title,sources:[{key:crypto.randomUUID(),file:new File([text],'follow-up.txt',{type:'text/plain'}),communicationDate:'2026-11-14',error:null}]},{caseId:view.detail.case.id,version:view.detail.case.version,evidenceIds:[],uploadedKeys:[],extractionId:null,candidates:[],duplicateId:null,state:'ready'},()=>{});
}
const current=view=>view.detail.commitments.find(c=>c.status==='active');

test('seed evidence bytes match their hashes and original/revised quotations remain exact source text',async()=>{
  const m=await runtime();const views=await m.listEvidence();assert.equal(views.length,5);
  for(const view of views) {
    for(const source of view.detail.evidence) {
      const blob=await m.loadEvidenceFile(source);
      assert.equal(blob.size,source.size_bytes);
      assert.equal(Buffer.from(await crypto.subtle.digest('SHA-256',await blob.arrayBuffer())).toString('hex'),source.sha256);
    }
  }
  const nova=views.find(v=>v.detail.case.merchant_name==='NovaMart');
  assert.equal(nova.detail.commitments.length,2);
  for(const promise of nova.detail.commitments) {
    const sources=m.sourceQuotes(nova.detail,promise.id);assert.equal(sources.length,1);
    const source=nova.detail.evidence.find(e=>e.id===sources[0].evidence_id);
    assert.ok((await (await m.loadEvidenceFile(source)).text()).includes(sources[0].quote));
  }
});

test('missing originals and evidence from a different case fail without exposing another file',async()=>{
  const m=await runtime();const nova=await sample(m);const aster=await sample(m,'Aster Electronics');
  await assert.rejects(()=>m.loadEvidenceFile({...nova.detail.evidence[0],id:crypto.randomUUID()}),e=>e.status===404);
  await assert.rejects(()=>m.loadEvidenceFile({...nova.detail.evidence[0],case_id:aster.detail.case.id}),e=>e.status===404);
});

test('a confirmed revision appends to its predecessor while keeping original terms and source links',async()=>{
  const m=await runtime();const before=await sample(m);const predecessor=current(before);
  const job=await communication(m,before);const fields=m.reviewFields(job.candidates);
  assert.equal((await m.loadCase(job.caseId)).detail.commitments.length,2);
  await m.reviewCommunication(job,[{field:fields[0],action:'revision',predecessor:predecessor.id}],'Company supplied a later deadline.');
  const after=await m.loadCase(job.caseId);assert.equal(after.detail.commitments.length,3);
  const newest=current(after);assert.equal(newest.supersedes_id,predecessor.id);
  assert.equal(newest.due_at,'2026-11-20T18:29:59Z');
  for(const old of before.detail.commitments) {
    const preserved=after.detail.commitments.find(c=>c.id===old.id);
    assert.deepEqual({...preserved,status:old.status},old);
    assert.equal(preserved.status,'superseded');
  }
  assert.ok(predecessor.evidence_ids.every(id=>newest.evidence_ids.includes(id)));
  assert.ok(job.evidenceIds.every(id=>newest.evidence_ids.includes(id)));
  assert.ok(m.sourceQuotes(after.detail,newest.id)[0].quote.includes('2026-11-20'));
  assert.equal(after.meta.events.find(e=>e.kind==='review').note,'Company supplied a later deadline.');
  const snapshot=structuredClone(after.detail);
  await assert.rejects(()=>m.reviewCommunication(job,[{field:fields[0],action:'revision',predecessor:predecessor.id}],'Repeated click'));
  assert.deepEqual((await m.loadCase(job.caseId)).detail,snapshot);
});

test('stale revision review fails without modifying current promises or its pending draft',async()=>{
  const m=await runtime();const view=await sample(m);const predecessor=current(view);
  const job=await communication(m,view);const fields=m.reviewFields(job.candidates);
  await m.mockApi.uploadEvidence(job.caseId,new File(['Another communication'],'other.txt',{type:'text/plain'}),job.version);
  const before=await m.mockApi.getCase(job.caseId);
  await assert.rejects(()=>m.reviewCommunication(job,[{field:fields[0],action:'revision',predecessor:predecessor.id}],'Confirmed revised date'),e=>e.status===409);
  assert.deepEqual(await m.mockApi.getCase(job.caseId),before);
});

test('one review cannot branch two revisions from the same predecessor and fails atomically',async()=>{
  const m=await runtime();const view=await sample(m);const predecessor=current(view);
  const job=await communication(m,view,'We will refund INR 4999 by 2026-11-20.\n\nWe will refund INR 4999 by 2026-11-21.');
  assert.equal(job.candidates.length,2);const before=await m.mockApi.getCase(job.caseId);
  await assert.rejects(()=>m.reviewCommunication(job,m.reviewFields(job.candidates).map(field=>({field,action:'revision',predecessor:predecessor.id})),'These dates conflict.'),e=>e.status===409);
  assert.deepEqual(await m.mockApi.getCase(job.caseId),before);
});

test('partial receipts validate against outstanding money and preserve original amount, deadline and overdue state',async()=>{
  const m=await runtime();let view=await sample(m);const promise=structuredClone(current(view));
  for(const amount of ['0','-1','4999','5000','1.001']) {
    await assert.rejects(()=>m.recordCaseOutcome(view,{kind:'partial',note:'Received part of the refund',amount}));
    assert.equal((await m.loadCase(view.detail.case.id)).detail.case.version,view.detail.case.version);
  }
  await m.recordCaseOutcome(view,{kind:'partial',note:'Received INR 1000',amount:'1000'});
  view=await m.loadCase(view.detail.case.id);
  assert.equal(view.totalMinor,499900);assert.equal(view.outstandingMinor,399900);assert.equal(view.meta.receivedMinor,100000);
  assert.equal(view.row.partial,true);assert.equal(view.row.status,'Overdue');assert.deepEqual(current(view),promise);
  assert.equal((await m.loadMockWorkspace()).cases.find(c=>c.id===view.detail.case.id).amountMinor,399900);
  await assert.rejects(()=>m.recordCaseOutcome(view,{kind:'partial',note:'Too much',amount:'4000'}));
  await m.recordCaseOutcome(view,{kind:'pending',note:'Still waiting for the balance',amount:''});
  const pending=await m.loadCase(view.detail.case.id);
  assert.notEqual(pending.detail.case.status,'resolved');assert.equal(pending.outstandingMinor,399900);
  assert.equal(pending.meta.events.at(-1).kind,'pending');
});

test('non-monetary partial fulfilment remains open and requires a descriptive note',async()=>{
  const m=await runtime();let view=await sample(m,'Aster Electronics');
  await assert.rejects(()=>m.recordCaseOutcome(view,{kind:'partial',note:'',amount:''}));
  await m.recordCaseOutcome(view,{kind:'partial',note:'Keyboard arrived; replacement cable is still missing.',amount:''});
  view=await m.loadCase(view.detail.case.id);
  assert.equal(view.row.partial,true);assert.equal(view.totalMinor,null);assert.equal(view.row.status,'Due today');
  assert.equal(current(view).status,'active');
});

test('full fulfilment resolves only current promises and preserves superseded history',async()=>{
  const m=await runtime();let view=await sample(m);const original=view.detail.commitments.find(c=>c.status==='superseded');
  await m.recordCaseOutcome(view,{kind:'full',note:'I received the entire refund.',amount:''});
  view=await m.loadCase(view.detail.case.id);assert.equal(view.detail.case.status,'resolved');assert.equal(view.outstandingMinor,0);
  assert.equal(view.detail.case.resolution_note,'I received the entire refund.');
  assert.deepEqual(view.detail.commitments.find(c=>c.id===original.id),original);
  assert.equal(view.detail.commitments.filter(c=>c.status==='fulfilled').length,1);
  assert.equal(m.caseTimeline(view).filter(e=>e.title==='Fulfilment confirmed by you').length,1);
});

test('reopening a resolved seed retains the past resolution and records the reason',async()=>{
  const m=await runtime();let view=await sample(m,'Orbit Store');
  const resolvedAt=view.detail.case.resolved_at;const resolutionNote=view.detail.case.resolution_note;
  await assert.rejects(()=>m.manageCase(view,'reopen',{note:''}));
  await m.manageCase(view,'reopen',{note:'The payment was reversed by my bank.'});
  view=await m.loadCase(view.detail.case.id);assert.notEqual(view.detail.case.status,'resolved');assert.equal(current(view).status,'active');
  const events=m.caseTimeline(view);
  assert.ok(events.some(e=>e.at===resolvedAt && e.note===resolutionNote && e.title==='Fulfilment confirmed by you'));
  assert.ok(events.some(e=>e.note==='The payment was reversed by my bank.' && e.title==='Case reopened'));
});

test('archiving hides a case from workspace totals, retains originals, and restore returns it',async()=>{
  const m=await runtime();let view=await sample(m);const source=view.detail.evidence[0];
  const original=await (await m.loadEvidenceFile(source)).text();
  await m.manageCase(view,'archive',{});
  assert.equal((await m.loadMockWorkspace()).cases.some(c=>c.id===view.detail.case.id),false);
  assert.equal(await (await m.loadEvidenceFile(source)).text(),original);
  view=await m.loadCase(view.detail.case.id);assert.equal(view.meta.archived,true);
  await assert.rejects(()=>m.recordCaseOutcome(view,{kind:'pending',note:'Waiting',amount:''}),e=>e.status===409);
  await m.manageCase(view,'restore',{});
  assert.equal((await m.loadMockWorkspace()).cases.some(c=>c.id===view.detail.case.id),true);
});

test('identity corrections retain facts and sources, and deletion requires the exact case ID',async()=>{
  const m=await runtime();let view=await sample(m);const original=structuredClone(view.detail);
  await m.manageCase(view,'edit',{company:'Corrected company',title:'Corrected title',note:'Corrected a company spelling.'});
  view=await m.loadCase(view.detail.case.id);assert.deepEqual(view.detail.commitments,original.commitments);assert.deepEqual(view.detail.evidence,original.evidence);
  assert.match(view.meta.events.at(-1).note,/NovaMart/);
  await assert.rejects(()=>m.manageCase(view,'delete',{confirmation:'DELETE'}));
  assert.equal((await m.loadCase(view.detail.case.id)).detail.case.title,'Corrected title');
  await m.manageCase(view,'delete',{confirmation:view.detail.case.id});
  await assert.rejects(()=>m.loadCase(view.detail.case.id),e=>e.status===404);
  await assert.rejects(()=>m.loadEvidenceFile(original.evidence[0]),e=>e.status===404);
  assert.equal((await m.loadMockWorkspace()).cases.some(c=>c.id===view.detail.case.id),false);
});

test('a company fulfilment claim keeps receipt unconfirmed and does not change the current deadline',async()=>{
  const m=await runtime();const before=await sample(m);const job=await communication(m,before,'Your refund has been processed. Please check your account.');
  assert.equal(job.candidates.length,0);await m.keepCommunication(job,'claim','The company says the refund was processed; I have not received it.');
  const after=await m.loadCase(job.caseId);assert.deepEqual(after.detail.commitments,before.detail.commitments);
  assert.equal(after.row.status,'Overdue');assert.equal(after.detail.case.resolved_at,null);
  assert.equal(after.meta.events.at(-1).kind,'claim');
});

test('HTTP original downloads use the contracted authenticated route and ignore supplied external paths',async()=>{
  const http=await bundle(false);const m=await import(`data:text/javascript;base64,${Buffer.from(http).toString('base64')}#http-download`);
  const oldFetch=globalThis.fetch;let request;
  globalThis.fetch=async(url,options)=>{request={url,options};return new Response('Original bytes',{headers:{'Content-Type':'text/plain'}});};
  try {
    const blob=await m.loadEvidenceFile({id:'source/one',case_id:'case/one',download_path:'https://untrusted.example/private',filename:'original.txt',media_type:'text/plain',size_bytes:14,sha256:'a'.repeat(64),created_at:'2026-11-14T09:00:00Z'});
    assert.equal(request.url,'http://localhost:8000/api/v1/cases/case%2Fone/evidence/source%2Fone/content');
    assert.equal(request.options.credentials,'include');assert.equal(request.options.cache,'no-store');assert.equal(await blob.text(),'Original bytes');
  } finally {globalThis.fetch=oldFetch;}
});
test('same-day partial receipt, revision, resolution and reopen stay in actual event order',async()=>{
  const m=await runtime();let view=await sample(m);
  await m.recordCaseOutcome(view,{kind:'partial',note:'First receipt',amount:'1000'});view=await m.loadCase(view.detail.case.id);
  const job=await communication(m,view);await m.reviewCommunication(job,[{field:m.reviewFields(job.candidates)[0],action:'revision',predecessor:current(view).id}],'Later promise confirmed after the partial receipt.');
  view=await m.loadCase(view.detail.case.id);const timeline=m.caseTimeline(view);
  assert.ok(timeline.findIndex(e=>e.note==='First receipt')<timeline.findIndex(e=>e.commitment?.supersedes_id===current(view).supersedes_id && e.commitment?.status==='active'));
  await m.recordCaseOutcome(view,{kind:'full',note:'Received the balance',amount:''});view=await m.loadCase(view.detail.case.id);
  await m.manageCase(view,'reopen',{note:'Payment reversed.'});view=await m.loadCase(view.detail.case.id);
  assert.equal(m.caseTimeline(view).filter(e=>e.title==='Fulfilment confirmed by you').length,1);
});
