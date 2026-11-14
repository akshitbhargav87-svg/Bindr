// Opt-in integration smoke against the real API, using synthetic evidence only.
// Run: node checks/live-api.mjs http://127.0.0.1:8000
import assert from 'node:assert/strict';
import {build} from 'esbuild';

const origin = process.argv[2];
if (!origin || !/^https?:\/\//.test(origin)) throw new Error('Pass the intended API origin explicitly. This check creates a synthetic case in a new anonymous workspace.');
const code = (await build({stdin:{contents:"export {httpApi,downloadHttpEvidence} from './src/api/http';",resolveDir:process.cwd()},bundle:true,format:'esm',platform:'node',write:false,define:{'import.meta.env':JSON.stringify({VITE_API_URL:origin,VITE_USE_MOCK:'false'})}})).outputFiles[0].text;
const browserCookies = new Map();
globalThis.document = {get cookie(){return [...browserCookies].map(([key,value])=>`${key}=${value}`).join('; ');}};
const transport = globalThis.fetch;
globalThis.fetch = async (url, options = {}) => {
  const headers = new Headers(options.headers);
  headers.set('Cookie', document.cookie);
  headers.set('Origin', new URL(origin).origin);
  const response = await transport(url,{...options,headers});
  for (const cookie of response.headers.getSetCookie()) {
    const [pair] = cookie.split(';');const equal = pair.indexOf('=');
    browserCookies.set(pair.slice(0,equal),pair.slice(equal+1));
  }
  return response;
};
const {httpApi:api,downloadHttpEvidence} = await import(`data:text/javascript;base64,${Buffer.from(code).toString('base64')}`);
const {case:made} = await api.createCase({title:'Synthetic acceptance refund',merchant_name:'Bindr Test Shop'});
const original = 'We will refund INR 4999 for the returned headphones by 2026-11-18.';
const first = await api.uploadEvidence(made.id,new File([original],'original.txt',{type:'text/plain'}),made.version);
const extracted = await api.extract(made.id,[first.evidence.id],first.case_version);
assert.ok(extracted.extraction.candidates.length,'The configured provider must extract the synthetic refund.');
assert.equal((await api.getCase(made.id)).commitments.length,0);
const candidate = extracted.extraction.candidates[0];
assert.equal(candidate.sources[0].evidence_id,first.evidence.id);
assert.ok(original.includes(candidate.sources[0].quote));
const reviewed = await api.review(made.id,extracted.extraction.id,{expected_version:extracted.case_version,decision:'approve',items:[{candidate_id:candidate.candidate_id,action:'new',supersedes_id:null,terms:{kind:'refund',description:'Refund for returned headphones',amount_minor:499900,currency:'INR',due_at:'2026-11-18T18:29:59Z'},evidence_ids:[first.evidence.id]}]});
const second = await api.uploadEvidence(made.id,new File(['We will refund INR 4999 for the returned headphones by 2026-11-20.'],'revision.txt',{type:'text/plain'}),reviewed.case_version);
const revision = await api.extract(made.id,[second.evidence.id],second.case_version);
const revised = await api.review(made.id,revision.extraction.id,{expected_version:revision.case_version,decision:'approve',items:[{candidate_id:revision.extraction.candidates[0].candidate_id,action:'revision',supersedes_id:reviewed.commitments[0].id,terms:{kind:'refund',description:'Revised refund for returned headphones',amount_minor:499900,currency:'INR',due_at:'2026-11-20T18:29:59Z'},evidence_ids:[first.evidence.id,second.evidence.id]}]});
const detail = await api.getCase(made.id);
const originalId = reviewed.commitments[0].id;
const revisedId = revised.commitments[0].id;
assert.equal(detail.commitments.find(c=>c.id===originalId)?.status,'superseded');
assert.equal(detail.commitments.find(c=>c.id===revisedId)?.supersedes_id,originalId);
assert.equal(detail.commitments.find(c=>c.id===originalId)?.due_at,'2026-11-18T18:29:59Z');
assert.equal(detail.commitments.find(c=>c.id===revisedId)?.due_at,'2026-11-20T18:29:59Z');
assert.deepEqual(new Set(detail.commitments.find(c=>c.id===originalId)?.evidence_ids),new Set([first.evidence.id]));
assert.deepEqual(new Set(detail.commitments.find(c=>c.id===revisedId)?.evidence_ids),new Set([first.evidence.id,second.evidence.id]));
const complaint = await api.complaint(made.id,revised.case_version,'Complete the promised refund.');
assert.ok(complaint.draft.body.length);
assert.equal(complaint.case_version,revised.case_version);
assert.equal(await (await downloadHttpEvidence(first.evidence)).text(),original);
await assert.rejects(()=>api.resolve(made.id,made.version,'Stale attempt'),error=>error.status===409);
await api.resolve(made.id,revised.case_version,'Synthetic receipt confirmed.');
const final = await api.getCase(made.id);
assert.equal(final.case.status,'resolved');
assert.equal(final.commitments.find(c=>c.id===originalId)?.status,'superseded');
assert.equal(final.commitments.find(c=>c.id===revisedId)?.status,'fulfilled');
console.log('PASS: real API session, create, upload, extract, review, revision, complaint, original bytes, stale-write rejection and resolution.');
