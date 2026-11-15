/** Serialized synthetic records through actual renderers; no live account/server claim. */
import test from 'node:test';
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
import {JSDOM,ResourceLoader,VirtualConsole} from 'jsdom';
import React,{act} from 'react';
import {build} from 'esbuild';

const payload=`Stored ₹500 हिन्दी ગુજરાતી <img src="https://remote.invalid/pixel" onerror="alert('Bindr-XSS-Test')"><script>alert('Bindr-XSS-Test')</script><b>Refund approved</b>`;
const loads=[],effects=[];
class Monitor extends ResourceLoader{fetch(url){loads.push(url);return null;}}
const dom=new JSDOM('<!doctype html><html><body></body></html>',{url:'https://bindr.test/',runScripts:'dangerously',resources:new Monitor(),virtualConsole:new VirtualConsole()});
globalThis.window=dom.window;globalThis.document=dom.window.document;globalThis.HTMLElement=dom.window.HTMLElement;globalThis.IS_REACT_ACT_ENVIRONMENT=true;
window.alert=value=>effects.push(value);
window.HTMLDialogElement.prototype.showModal=function(){this.open=true;};window.HTMLDialogElement.prototype.close=function(){this.open=false;};
const {createRoot}=await import('react-dom/client');const {MemoryRouter,Routes,Route}=await import('react-router-dom');
const require=createRequire(import.meta.url),tick=()=>new Promise(r=>setImmediate(r));
const config={'import.meta.env':JSON.stringify({VITE_USE_MOCK:'true'})};
const library=(await build({stdin:{contents:"export * from './src/api/case-service';export * from './src/api/complaint';export * from './src/api/complaint-document';export {loadMockWorkspace} from './src/api/mock';",resolveDir:process.cwd()},bundle:true,platform:'node',format:'esm',write:false,define:config})).outputFiles[0].text;
const logic=await import(`data:text/javascript;base64,${Buffer.from(library).toString('base64')}`);
const seed=(await logic.loadMockWorkspace()).cases.find(c=>c.company==='NovaMart');
const view=structuredClone(await logic.loadCase(seed.id));
view.row.company=payload;view.row.title=payload;view.detail.case.merchant_name=payload;view.detail.case.title=payload;
view.detail.commitments.forEach(c=>c.description=payload);
view.detail.evidence.forEach(e=>e.filename=payload+'.txt');
view.detail.extractions.forEach(e=>e.candidates.forEach(c=>c.sources.forEach(s=>s.quote=payload)));
view.meta.events.push({id:'stored-note',kind:'update',title:payload,note:payload,at:'2026-11-14T10:00:00Z',evidenceIds:[view.detail.evidence[0].id],amountMinor:null});
const serialized=JSON.stringify(view),saved=()=>JSON.parse(serialized);
globalThis.__storedLogic=logic;globalThis.__storedSaved=saved;globalThis.__storedPayload=payload;
const session={...logic.newComplaintSession(saved()),stage:'draft',snapshot:saved(),subject:payload.slice(0,200),body:payload,exportConfirmed:true};
session.snapshotSelection=structuredClone(session.selection);session.usedEvidenceIds=[...session.selection.evidenceIds];
const drafts={sessions:{[seed.id]:session},saved:{},update:()=>{},save:async()=>true,remove:()=>{},ready:true};
globalThis.__storedDrafts=drafts;
globalThis.__storedWorkspace={offline:false,isMock:true,view:'sample',data:{cases:[view.row],asOf:'2026-11-15T10:00:00Z'},refresh:async()=>{},markIntroduced:()=>{},chooseView:()=>{}};
globalThis.__storedPreferences={preferences:{caseUpdates:true,deadlinePrompts:true},readIds:new Set(),markRead:()=>{},ready:true};
const stubs={
  workspace:'export const useWorkspace=()=>globalThis.__storedWorkspace;',
  complaints:'export const useComplaints=()=>globalThis.__storedDrafts;',
  preferences:'export const usePreferences=()=>globalThis.__storedPreferences;',
  capture:'export const useCapture=()=>({session:{},setSession:()=>{}});export const newCapture=()=>({});',
  auth:"export const useAuth=()=>({status:'signed-in',info:null});",
  services:`export const loadCase=async()=>globalThis.__storedSaved();export const listEvidence=async()=>[globalThis.__storedSaved()];export const loadEvidenceFile=async()=>new Blob([globalThis.__storedPayload],{type:'text/plain'});export const caseTimeline=(...a)=>globalThis.__storedLogic.caseTimeline(...a);export const sourceQuotes=(...a)=>globalThis.__storedLogic.sourceQuotes(...a);export const caseReference=(...a)=>globalThis.__storedLogic.caseReference(...a);export const manageCase=async()=>{};export const recordCaseOutcome=async()=>{};`,
};
async function component(entry){
  const code=(await build({entryPoints:[entry],bundle:true,format:'cjs',platform:'node',packages:'external',jsx:'automatic',loader:{'.css':'empty'},define:config,write:false,plugins:[{name:'controlled-owned-boundaries',setup(b){b.onResolve({filter:/.*/},args=>{const path=args.path;let key;if(path.endsWith('/state/Workspace'))key='workspace';if(path.endsWith('/state/Complaints'))key='complaints';if(path.endsWith('/state/Preferences'))key='preferences';if(path.endsWith('/state/Capture'))key='capture';if(path.endsWith('/state/Auth'))key='auth';if(path.endsWith('/case-service'))key='services';if(key)return {path:key,namespace:'stored-stub'};});b.onLoad({filter:/.*/,namespace:'stored-stub'},args=>({contents:stubs[args.path],loader:'js'}));}}]})).outputFiles[0].text;
  const mod={exports:{}};new Function('require','module','exports',code)(require,mod,mod.exports);return mod.exports;
}
const pages={detail:(await component('src/pages/CaseDetail.tsx')).default,evidence:(await component('src/pages/EvidenceLibrary.tsx')).default,activity:(await component('src/pages/Planning.tsx')).Activity,complaint:(await component('src/pages/Complaint.tsx')).default};
async function renderPage(Page,props={}){
  const host=document.createElement('div');document.body.append(host);const root=createRoot(host);
  await act(async()=>{root.render(React.createElement(MemoryRouter,{initialEntries:[`/app/cases/${seed.id}`]},React.createElement(Routes,null,React.createElement(Route,{path:'/app/cases/:caseId',element:React.createElement(Page,props)}))));await tick();await tick();});
  return {host,async close(){await act(async()=>root.unmount());host.remove();}};
}
function assertSafe(host){assert.ok(host.textContent.includes(payload),'Stored Unicode/source markup is still literal text');assert.equal(host.querySelector('script,iframe,[onerror],[onclick]'),null);assert.equal(host.querySelector('img[src*="remote.invalid"]'),null);assert.deepEqual(effects,[]);assert.equal(loads.filter(url=>url.includes('remote.invalid')).length,0);}
for(const [name,Page] of Object.entries(pages))test(`stored-XSS: saved/reloaded ${name} renderer has no script/event/remote-load effects`,async()=>{const rendered=await renderPage(Page);try{assertSafe(rendered.host);}finally{await rendered.close();}});
test('stored-XSS: original text viewer and unsupported HTML never embed source markup',async()=>{
  const Viewer=(await component('src/components/workspace/EvidenceViewer.tsx')).default;
  for(const mime of ['text/plain','text/html','image/svg+xml']){
    const rendered=await renderPage(Viewer,{evidence:saved().detail.evidence[0],quote:payload,loadFile:async()=>new Blob([payload],{type:mime}),onClose:()=>{}});
    try{assertSafe(rendered.host);assert.equal(rendered.host.querySelector('object,iframe,img'),null);if(mime!=='text/plain')assert.match(rendered.host.textContent,/cannot be previewed/);}finally{await rendered.close();}
  }
});
test('stored-XSS: plaintext export preserves exact wording without interpreting it as HTML',()=>{
  const exported=logic.buildExportText({...session,snapshot:saved()});assert.ok(exported.includes(payload));
  assert.equal(typeof exported,'string');assert.deepEqual(effects,[]);
});
