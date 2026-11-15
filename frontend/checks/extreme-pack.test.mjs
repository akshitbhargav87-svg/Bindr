import test from 'node:test';
import assert from 'node:assert/strict';
import {build} from 'esbuild';
import {createRequire} from 'node:module';
import {appendFileSync,mkdirSync,readFileSync} from 'node:fs';
import {resolve} from 'node:path';
import React,{act} from 'react';
import {JSDOM} from 'jsdom';
const output=resolve('../storage/extreme-testing-2026-11-15/scenario-frontend.jsonl');
mkdirSync(resolve('../storage/extreme-testing-2026-11-15'),{recursive:true});
const report=(id,verdict,observation)=>appendFileSync(output,JSON.stringify({id,verdict,observation})+'\n');
const dom=new JSDOM('<!doctype html><html><body></body></html>',{url:'https://bindr.test/'});
globalThis.window=dom.window;globalThis.document=dom.window.document;globalThis.IS_REACT_ACT_ENVIRONMENT=true;
const {createRoot}=await import('react-dom/client');
const {MemoryRouter}=await import('react-router-dom');
const require=createRequire(import.meta.url),tick=()=>new Promise(r=>setImmediate(r));
const firebaseNames=readFileSync('src/pages/Auth.tsx','utf8').match(/import \{([^}]+)\} from '@firebase\/auth'/)[1].split(',').map(n=>n.trim()).filter(n=>!n.startsWith('type '));
const stubs={
 captureContext:`export const useCapture=()=>globalThis.__captureHook;export const newCapture=()=>globalThis.__captureInitial();`,
 workspace:`export const useWorkspace=()=>({offline:false,isMock:false,refresh:async()=>{},markIntroduced:()=>{}});`,
 capture:`export * from ${JSON.stringify('./src/api/capture.ts')}; export const prepareCapture=(...a)=>globalThis.__extreme.prepare(...a);`,
 auth:`export const useAuth=()=>globalThis.__extreme.account;`,
 account:`export const firebaseAuth=async()=>({});export const authMessage=e=>e.message;export const safeReturnTo=()=>'/app';`,
 firebase:firebaseNames.map(n=>n==='GoogleAuthProvider' ? 'export class GoogleAuthProvider{}' : `export const ${n}=(...a)=>globalThis.__extreme.firebase?.(${JSON.stringify(n)},...a);`).join('\n'),
};
async function module(entry,stubbing=true){
 const code=(await build({entryPoints:[entry],bundle:true,format:'cjs',platform:'node',packages:'external',jsx:'automatic',loader:{'.css':'empty'},write:false,define:{'import.meta.env':JSON.stringify({VITE_USE_MOCK:'false',VITE_API_URL:'/api/v1'})},plugins:stubbing?[{name:'boundaries',setup(b){b.onResolve({filter:/.*/},a=>{let s;if(a.path==='../state/Capture')s='captureContext';if(a.path==='../state/Workspace')s='workspace';if(a.path==='../api/capture')s='capture';if(a.path==='../state/Auth')s='auth';if(a.path==='../api/account')s='account';if(a.path==='@firebase/auth')s='firebase';if(s)return {path:s,namespace:'extreme-stub'};});b.onLoad({filter:/.*/,namespace:'extreme-stub'},a=>({contents:stubs[a.path],loader:'js',resolveDir:process.cwd()}));}}]:[]})).outputFiles[0].text;
 const m={exports:{}};new Function('require','module','exports',code)(require,m,m.exports);return m.exports;
}
const capture=await module('src/pages/Capture.tsx'),state=await module('src/state/Capture.tsx'),auth=await module('src/pages/Auth.tsx');
function mount(node){const host=document.createElement('div');document.body.append(host);const root=createRoot(host);return {host,root,async render(next=node){await act(async()=>{root.render(next);await tick();});},async close(){await act(async()=>root.unmount());host.remove();}};}
async function fill(host,selector,text){const e=host.querySelector(selector);assert.ok(e,selector);await act(async()=>{const p=e.tagName==='TEXTAREA'?window.HTMLTextAreaElement.prototype:window.HTMLInputElement.prototype;Object.getOwnPropertyDescriptor(p,'value').set.call(e,text);e.dispatchEvent(new window.Event('input',{bubbles:true}));await tick();});}
async function submit(host,count=1){await act(async()=>{for(let i=0;i<count;i++)host.querySelector('form').dispatchEvent(new window.Event('submit',{bubbles:true,cancelable:true}));await tick();});}
let session;
function Probe(){session=state.useCapture();globalThis.__captureHook=session;globalThis.__captureInitial=state.newCapture;return React.createElement(capture.default);}
function captureNode(key='same'){return React.createElement(MemoryRouter,null,React.createElement(state.CaptureProvider,{key},React.createElement(Probe)));}
async function setup(text='We will refund INR 500 by 2026-11-20.',date='2026-11-14'){
 const view=mount(captureNode());await view.render();await act(async()=>{session.setSession(s=>({...s,tab:'paste',company:'Synthetic Shop',text,communicationDate:date}));await tick();});return view;
}

test('empty and oversized pasted messages are blocked before transport',async()=>{
 let calls=0;globalThis.__extreme={prepare:async()=>{calls++;throw Error('transport should not run');}};
 for(const [text,expect] of [[' \n  ','Paste the original company message.'],['x'.repeat(100000),'Use at most 50,000 characters.']]){
  const v=await setup(text);try{await submit(v.host);assert.match(v.host.textContent,new RegExp(expect.replaceAll('.','\\.')));assert.equal(calls,0);}finally{await v.close();}
 }
 report('P2-03','PASS','Actual React paste form rejects whitespace before preparing a case.');
 report('P2-02','PASS','Actual React paste form rejects programmatically supplied 100,000 characters; textarea declares maxlength=50,000. Backend parser boundary separately tested.');
});

test('repeated submits, deferred AI, and network failure keep input',async()=>{
 let calls=0,reject;globalThis.__extreme={prepare:()=>{calls++;return new Promise((_,r)=>reject=r);}};
 const v=await setup();try{
  await submit(v.host,2);assert.equal(calls,1);assert.match(v.host.textContent,/Keeping the words/);
  await act(async()=>{reject(new TypeError('Network unavailable'));await tick();});
  assert.equal(session.session.text,'We will refund INR 500 by 2026-11-20.');assert.match(v.host.textContent,/Your input is still here/);
  report('P2-01','PARTIAL','Same-turn double submit of actual React capture form invoked preparation once. Raw API replay still creates two cases.');
  report('P2-10','PARTIAL','Deferred capture promise shows processing state and ignores repeated submit. API timeout/retry tested separately; no real DevTools throttling.');
  report('P2-11','PASS','Injected network rejection returns capture form with exact pasted text and recoverable error. Backend retry preservation tested separately.');
 }finally{await v.close();}
});

test('far-future communication date policy',async()=>{
 let observed;globalThis.__extreme={prepare:async input=>{observed=input;throw Error('Stopped after validation');}};
 const v=await setup('Synthetic message','2099-01-01');try{
  await submit(v.host);assert.equal(observed.sources[0].communicationDate,'2099-01-01');
  report('P2-08','FAIL','Actual React form accepts communication date 2099-01-01 without a future-date warning. Connected upload contract does not persist communicationDate (source inspection).');
 }finally{await v.close();}
});

test('capture provider loses unsaved text when account key changes',async()=>{
 globalThis.__extreme={};const v=await setup('UNSAVED PRIVATE NOTE');try{
  assert.equal(session.session.text,'UNSAVED PRIVATE NOTE');await v.render(captureNode('signed-out'));assert.equal(session.session.text,'');
  report('P2-12','FAIL','Rekeying the actual CaptureProvider resets unsaved text to empty. App.tsx nests it beneath PreferencesProvider keyed by account ID/status, so expiry/sign-out remounts this subtree. This verifies state reset, not a live Firebase reauthentication session.');
 }finally{await v.close();}
});

test('bare email action path reports an invalid-link state',async()=>{
 globalThis.__extreme={account:{status:'signed-out',config:{configured:true}},firebase:()=>Promise.resolve()};
 const v=mount(React.createElement(MemoryRouter,{initialEntries:['/auth/action']},React.createElement(auth.default)));
 try{await v.render();assert.match(v.host.textContent,/This account link is not supported/);assert.doesNotMatch(v.host.textContent,/404 \/ PAGE NOT FOUND/);report('P2-14','PASS','Actual React Auth page at bare /auth/action presents unsupported-link message rather than generic 404. HTTP SPA shell tested separately.');}finally{await v.close();}
});

test('dashboard projection uses current obligations and excludes resolved/review records',async()=>{
 const mapper=await module('src/api/mapper.ts',false),lib=await module('src/lib/cases.ts',false);
 const make=(id,status,commitments)=>({case:{id,title:id,merchant_name:'Same Company',status,version:1,resolved_at:null},commitments,evidence:[]});
 const fact=(amount,due,status='active',currency='INR')=>({id:crypto.randomUUID(),status,amount_minor:amount,currency,due_at:due,supersedes_id:null});
 const a=mapper.mapCaseRow(make('a','overdue',[fact(10000,'2026-11-12T00:00:00Z','superseded'),fact(15000,'2026-11-17T00:00:00Z'),fact(20000,'2026-11-20T00:00:00Z')]));
 const b=mapper.mapCaseRow(make('b','open',[fact(5000,'2026-11-22T00:00:00Z')]));
 const c=mapper.mapCaseRow(make('c','resolved',[fact(90000,'2026-11-10T00:00:00Z','fulfilled')]));
 const d=mapper.mapCaseRow(make('d','open',[]));
 assert.deepEqual(lib.summarizeCases([a,b,c,d]),{open:2,outstandingMinor:40000,overdue:1});
 assert.equal(a.dueAt,'2026-11-17T00:00:00Z');assert.equal(a.amountMinor,35000);
 report('P3-10','PASS','Real frontend mapper/summary: two open tracked cases, INR 400 outstanding, one overdue. Superseded INR 100 and resolved INR 900 excluded. Fixture projection, not live dashboard SQL comparison.');
 report('P3-05','PARTIAL','Two active monetary obligations aggregate INR 350 with earliest date displayed; individual dates remain in detail. Mixed past/future API case tested separately.');
});
