import {test} from 'node:test';
import assert from 'node:assert/strict';
import {build} from 'esbuild';
async function bundle(mock=true){return (await build({stdin:{contents:"export * from './src/api/complaint'; export {loadCase,recordCaseOutcome,manageCase} from './src/api/case-service'; export {mockApi,loadMockWorkspace} from './src/api/mock';",resolveDir:process.cwd()},bundle:true,format:'esm',platform:'node',write:false,define:{'import.meta.env':JSON.stringify({VITE_USE_MOCK:mock?'true':'false'})}})).outputFiles[0].text;}
const code=await bundle();let count=0;
const runtime=()=>import(`data:text/javascript;base64,${Buffer.from(code).toString('base64')}#complaint-${++count}`);
async function nova(m){const {cases}=await m.loadMockWorkspace();return m.loadCase(cases.find(c=>c.company==='NovaMart').id);}
async function prepared(m,view){const selection=m.initialSelection(view);const draft=await m.generateComplaint(view,selection);return {...m.newComplaintSession(view),snapshot:structuredClone(view),snapshotSelection:structuredClone(selection),subject:draft.subject,body:draft.body,usedEvidenceIds:draft.evidence_ids,exportConfirmed:true,stage:'export'};}

test('a factual draft preserves both deadlines, exact quotations and source references without changing the case',async()=>{
  const m=await runtime();const view=await nova(m);const before=structuredClone(view.detail);
  const draft=await m.generateComplaint(view,m.initialSelection(view));
  assert.match(draft.body,/9 Nov 2026/);assert.match(draft.body,/12 Nov 2026/);
  assert.match(draft.body,/within 5 business days/);assert.match(draft.body,/another 3 business days/);
  assert.match(draft.body,/\[E-01\]/);assert.match(draft.body,/\[E-02\]/);
  assert.match(draft.body,/not confirmed fulfilment/);
  assert.deepEqual((await m.loadCase(view.detail.case.id)).detail,before);
  const contracted=await m.mockApi.complaint(view.detail.case.id,view.detail.case.version,'Complete the refund.');assert.equal(contracted.case_version,view.detail.case.version);
});
test('partial receipts produce the remaining amount without changing the canonical promise total',async()=>{
  const m=await runtime();let view=await nova(m);await m.recordCaseOutcome(view,{kind:'partial',note:'Received 1000',amount:'1000'});view=await m.loadCase(view.detail.case.id);
  const draft=await m.generateComplaint(view,m.initialSelection(view));assert.match(draft.body,/₹1,000/);assert.match(draft.body,/₹3,999/);assert.match(draft.body,/₹4,999/);
  assert.equal(view.detail.commitments.find(c=>c.status==='active').amount_minor,499900);
});
test('selection rejects detached revisions, missing originals, foreign evidence and no active promise',async()=>{
  const m=await runtime();const view=await nova(m);const selection=m.initialSelection(view);const active=view.detail.commitments.find(c=>c.status==='active');
  await assert.rejects(()=>m.generateComplaint(view,{...selection,factIds:[active.id]}),/earlier promise/);
  await assert.rejects(()=>m.generateComplaint(view,{...selection,evidenceIds:[selection.evidenceIds[0]]}),/original sources/);
  await assert.rejects(()=>m.generateComplaint(view,{...selection,evidenceIds:[crypto.randomUUID()]}),/linked evidence/);
  await assert.rejects(()=>m.generateComplaint(view,{...selection,factIds:[active.supersedes_id]}),/current/);
});
test('generation failure preserves selected inputs and permits a manual template with no invented receipt',async()=>{
  const m=await runtime();const view=await nova(m);const selection=m.initialSelection(view);selection.remedy='Please pay the remaining refund.';const original=structuredClone(selection);
  await assert.rejects(()=>m.generateComplaint(view,selection,true),/could not be prepared/);assert.deepEqual(selection,original);
  const manual=m.manualComplaint(view,selection);assert.match(manual.body,/Please pay the remaining refund/);assert.match(manual.body,/\[Describe/);assert.doesNotMatch(manual.body,/refund received in full/i);
});
test('closed and archived cases cannot generate or export a new complaint',async()=>{
  const m=await runtime();let view=await nova(m);const session=await prepared(m,view);await m.recordCaseOutcome(view,{kind:'full',note:'Received all',amount:''});
  await assert.rejects(()=>m.prepareComplaintExport(session),/unresolved/);view=await m.loadCase(view.detail.case.id);await assert.rejects(()=>m.generateComplaint(view,m.initialSelection(view)),/unresolved/);
  await m.manageCase(view,'archive',{});view=await m.loadCase(view.detail.case.id);await assert.rejects(()=>m.generateComplaint(view,m.initialSelection(view)),/Restore/);
});
test('stale preparation and export fail, leaving edited wording untouched',async()=>{
  const m=await runtime();const view=await nova(m);const session=await prepared(m,view);session.subject='My edited subject';session.body='My reviewed wording.';
  await m.recordCaseOutcome(view,{kind:'pending',note:'Still waiting',amount:''});
  await assert.rejects(()=>m.generateComplaint(view,m.initialSelection(view)),e=>e.status===409);
  await assert.rejects(()=>m.prepareComplaintExport(session),e=>e.status===409);assert.equal(session.body,'My reviewed wording.');
});
test('export requires confirmation and uses the exact edited subject/body with the selected appendices',async()=>{
  const m=await runtime();const session=await prepared(m,await nova(m));session.subject='My subject';session.body='My amended words. ₹3,999 remains.';session.exportConfirmed=false;
  await assert.rejects(()=>m.prepareComplaintExport(session),/Confirm/);session.exportConfirmed=true;
  const text=await m.prepareComplaintExport(session);assert.ok(text.startsWith('Subject: My subject\n\nMy amended words. ₹3,999 remains.'));
  assert.match(text,/Evidence index \(original files are not attached\)/);assert.match(text,/Confirmed promise history/);assert.doesNotMatch(text,/download_path|sha256|api\/v1/);
  session.includeEvidence=false;session.includeHistory=false;assert.equal(await m.prepareComplaintExport(session),'Subject: My subject\n\nMy amended words. ₹3,999 remains.');
  session.body='  My spacing stays.\n\n';assert.equal(await m.prepareComplaintExport(session),'Subject: My subject\n\n  My spacing stays.\n\n');
});
test('changing setup selections cannot silently change the facts of an already prepared draft',async()=>{
  const m=await runtime();const session=await prepared(m,await nova(m));session.selection={factIds:[],evidenceIds:[],remedy:'Different request'};
  const text=m.buildExportText(session);assert.match(text,/Original promise/);assert.match(text,/Revised promise/);assert.match(text,/refund-follow-up.txt/);
});
test('history export restores original source references even when a provider cites only one source',async()=>{
  const m=await runtime();const session=await prepared(m,await nova(m));session.usedEvidenceIds=[session.usedEvidenceIds[1]];
  assert.equal(m.exportEvidenceIds(session).length,2);assert.match(m.buildExportText(session),/refund-confirmation.txt/);
});
test('empty or excessive text cannot be saved as a valid draft/export',async()=>{
  const m=await runtime();assert.throws(()=>m.validateDraftText('', 'Body'));assert.throws(()=>m.validateDraftText('Subject','x'.repeat(10001)));
  const session=await prepared(m,await nova(m));session.body=' ';await assert.rejects(()=>m.prepareComplaintExport(session),/draft between/);
});
test('HTTP drafting sends only the contracted fields, cookies and CSRF and never sends a message',async()=>{
  const m=await runtime();const view=await nova(m);const http=await bundle(false);const h=await import(`data:text/javascript;base64,${Buffer.from(http).toString('base64')}#http-success`);
  const previousFetch=globalThis.fetch,previousDocument=globalThis.document;const calls=[];globalThis.document={cookie:'pk_csrf=token'};
  globalThis.fetch=async(url,options)=>{calls.push({url,options});return Response.json(options.method==='POST' ? {draft:{subject:'Reviewed follow-up',body:'Please complete the confirmed refund.',evidence_ids:view.detail.evidence.map(e=>e.id)},case_version:view.detail.case.version} : view.detail);};
  try{await h.generateComplaint(view,h.initialSelection(view));const posts=calls.filter(c=>c.options.method==='POST');assert.equal(posts.length,1);assert.match(posts[0].url,/\/complaint-draft$/);assert.deepEqual(Object.keys(JSON.parse(posts[0].options.body)).sort(),['expected_version','requested_remedy']);assert.equal(posts[0].options.credentials,'include');assert.equal(posts[0].options.headers['X-CSRF-Token'],'token');}
  finally{globalThis.fetch=previousFetch;if(previousDocument===undefined)delete globalThis.document;else globalThis.document=previousDocument;}
});
test('HTTP rejects unknown sources and a case changed during generation without retrying the POST',async()=>{
  const m=await runtime();const view=await nova(m);const http=await bundle(false);const h=await import(`data:text/javascript;base64,${Buffer.from(http).toString('base64')}#http-reject`);
  const previousFetch=globalThis.fetch,previousDocument=globalThis.document;globalThis.document={cookie:''};let posts=0;let badSource=true;
  globalThis.fetch=async(url,options)=>{if(options.method==='POST'){posts++;return Response.json({draft:{subject:'Follow-up',body:'Confirmed words.',evidence_ids:badSource ? ['unknown-source'] : view.detail.evidence.map(e=>e.id)},case_version:view.detail.case.version});}return Response.json({...view.detail,case:{...view.detail.case,version:view.detail.case.version+1}});};
  try{await assert.rejects(()=>h.generateComplaint(view,h.initialSelection(view)),/unavailable source/);assert.equal(posts,1);badSource=false;await assert.rejects(()=>h.generateComplaint(view,h.initialSelection(view)),e=>e.status===409);assert.equal(posts,2);}
  finally{globalThis.fetch=previousFetch;if(previousDocument===undefined)delete globalThis.document;else globalThis.document=previousDocument;}
});
