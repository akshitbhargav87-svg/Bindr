import {test} from 'node:test';
import assert from 'node:assert/strict';
import {build} from 'esbuild';
// Bundle the actual typed modules through Vite's existing build dependency.
// No browser, backend, external provider, or mirrored fixture values in UI code.
const bundle = await build({stdin: {contents: "export {loadMockWorkspace, mockApi} from './src/api/mock'; export {mapCaseRow} from './src/api/mapper'; export {summarizeCases,filterCases} from './src/lib/cases';", resolveDir: process.cwd()}, bundle:true, format:'esm', platform:'node', write:false});
const {loadMockWorkspace, mockApi, mapCaseRow, summarizeCases, filterCases} = await import(`data:text/javascript;base64,${Buffer.from(bundle.outputFiles[0].text).toString('base64')}`);

test('demo totals count outstanding promises once and exclude resolved amounts',async () => {
  const snapshot = await loadMockWorkspace();
  assert.deepEqual(summarizeCases(snapshot.cases), {open:4,outstandingMinor:579800,overdue:1});
  assert.equal(snapshot.asOf,'2026-11-14');
  assert.equal(snapshot.cases.find(c => c.company === 'Aster Electronics').status,'Due today');
  assert.equal(snapshot.cases.find(c => c.company === 'Orbit Store').status,'Resolved');
  assert.equal(snapshot.cases.find(c => c.company === 'Loop Internet').status,'Active');
});
test('NovaMart revision keeps original terms and original evidence',async () => {
  const snapshot = await loadMockWorkspace();
  const row = snapshot.cases.find(c => c.company === 'NovaMart');
  const detail = await mockApi.getCase(row.id);
  const original = detail.commitments.find(c => c.status === 'superseded');
  const current = detail.commitments.find(c => c.status === 'active');
  assert.equal(original.due_at,'2026-11-09T18:29:59Z');
  assert.equal(current.due_at,'2026-11-12T18:29:59Z');
  assert.equal(current.supersedes_id,original.id);
  assert.ok(original.evidence_ids.every(id => current.evidence_ids.includes(id)));
  assert.equal(row.revisionCount,1); assert.equal(row.evidenceCount,2); assert.equal(row.amountMinor,499900);
});
test('missing date never becomes overdue and raw backend status stays authoritative',async () => {
  const {cases} = await loadMockWorkspace();
  const detail = await mockApi.getCase(cases.find(c => c.company === 'Loop Internet').id);
  detail.commitments.forEach(c => {c.due_at = null;});
  assert.equal(mapCaseRow(detail).status,'Needs a date');
  detail.commitments.forEach(c => {c.due_at = '2030-01-01T18:29:59Z';});
  detail.case.status = 'overdue';
  assert.equal(mapCaseRow(detail).status,'Overdue');
  detail.case.status = 'resolved';
  assert.equal(mapCaseRow(detail).status,'Resolved');
});
test('search and status intersect, tolerate case/whitespace, and preserve input data',async () => {
  const {cases} = await loadMockWorkspace();
  const unchanged = structuredClone(cases);
  assert.equal(filterCases(cases,'  NOVA  ','Overdue').length,1);
  assert.equal(filterCases(cases,'refund','Resolved').length,1);
  assert.equal(filterCases(cases,'headphones','Active').length,0);
  assert.equal(filterCases(cases,'','Needs a date').length,0);
  assert.equal(filterCases(cases,'','Open').length,4);
  assert.deepEqual(cases,unchanged);
});
test('returned mock snapshots cannot mutate the adapter fixtures',async () => {
  const snapshot = await loadMockWorkspace(); snapshot.cases.length = 0;
  assert.equal((await loadMockWorkspace()).cases.length,5);
});


test('unconfirmed records remain distinct from tracked promise totals',async () => {
  const snapshot=await loadMockWorkspace();const detail=await mockApi.getCase(snapshot.cases[0].id);detail.commitments=[];detail.case.status='open';const row=mapCaseRow(detail);assert.equal(row.status,'Needs review');assert.deepEqual(summarizeCases([row]),{open:0,outstandingMinor:0,overdue:0});assert.equal(filterCases([row],'','Needs review').length,1);
});


test('case amounts retain currency and unrelated currencies are never summed',async()=>{
  const {cases}=await loadMockWorkspace();const detail=await mockApi.getCase(cases[0].id);detail.case.status='open';detail.commitments=detail.commitments.filter(c=>c.status==='active');detail.commitments[0].currency='USD';detail.commitments[0].amount_minor=12550;
  const row=mapCaseRow(detail);assert.equal(row.currency,'USD');assert.equal(row.amountMinor,12550);assert.equal(summarizeCases([row]).outstandingMinor,0);
  detail.commitments.push({...detail.commitments[0],id:'other-currency',currency:'INR',amount_minor:10000});const mixed=mapCaseRow(detail);assert.equal(mixed.amountMinor,null);assert.equal(mixed.currency,null);assert.equal(mixed.multipleCurrencies,true);assert.equal(summarizeCases([mixed]).outstandingMinor,10000);
});
