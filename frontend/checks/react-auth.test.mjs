import test from 'node:test';
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
import {JSDOM} from 'jsdom';
import React,{act} from 'react';
import {build} from 'esbuild';

const dom=new JSDOM('<!doctype html><html><body></body></html>',{url:'https://bindr.test/'});
globalThis.window=dom.window;globalThis.document=dom.window.document;
globalThis.IS_REACT_ACT_ENVIRONMENT=true;
const {createRoot}=await import('react-dom/client');
const {MemoryRouter}=await import('react-router-dom');
const require=createRequire(import.meta.url);
const stubs={
  'auth-context':`export const useAuth=()=>globalThis.__bindrReact.account;`,
  'account-api':`export const firebaseAuth=async()=>globalThis.__bindrReact.firebase;export const authMessage=e=>e.message;export const safeReturnTo=()=>'/app';export const accountRequest=(...args)=>globalThis.__bindrReact.request(...args);`,
  'firebase':`export const applyActionCode=(...args)=>globalThis.__bindrReact.apply(...args);export const verifyPasswordResetCode=async()=>'';export const reload=async()=>{};export const signOut=async()=>{};export const getMultiFactorResolver=()=>({});export const GoogleAuthProvider=class{};export const TotpMultiFactorGenerator={};export const confirmPasswordReset=(...args)=>globalThis.__bindrReact.resetPassword(...args);export const createUserWithEmailAndPassword=(...args)=>globalThis.__bindrReact.createUser(...args);export const sendEmailVerification=async()=>{};export const sendPasswordResetEmail=async()=>{};export const signInWithEmailAndPassword=async()=>{};export const signInWithPopup=async()=>{};export const updateProfile=async()=>{};export const validatePassword=async(...args)=>globalThis.__bindrReact.validate?.(...args) ?? {isValid:true};`,
  'case-service':`export const loadCase=id=>globalThis.__bindrReact.loadCase(id);`,
  'complaint-api':`export const newComplaintSession=view=>({snapshot:null,selection:{factIds:[],evidenceIds:[],remedy:''},subject:'',body:'',dirty:false,busy:false,stage:'setup',needsRefresh:false,exportConfirmed:false,preparedText:null});`,
  'api-index':`export const isMock=false;`,
  'http':`export const resetHttpSession=()=>{};`,
};
async function component(entry,provider=false){
  const code=(await build({entryPoints:[entry],bundle:true,format:'cjs',platform:'node',packages:'external',jsx:'automatic',loader:{'.css':'empty'},write:false,plugins:[{name:'controlled-external-boundaries',setup(b){
    b.onResolve({filter:/.*/},args=>{
      let stub;
      if(args.path==='@firebase/auth')stub='firebase';
      else if(args.path.endsWith('/api/account'))stub='account-api';
      else if(!provider && /(?:\/|^)Auth$/.test(args.path))stub='auth-context';
      else if(args.path.endsWith('/api/case-service'))stub='case-service';
      else if(args.path.endsWith('./complaint'))stub='complaint-api';
      else if(args.path==='../api')stub='api-index';
      else if(args.path.endsWith('/api/http'))stub='http';
      if(stub)return {path:stub,namespace:'test-stub'};
    });
    b.onLoad({filter:/.*/,namespace:'test-stub'},args=>({contents:stubs[args.path],loader:'js'}));
  }}]})).outputFiles[0].text;
  const mod={exports:{}};new Function('require','module','exports',code)(require,mod,mod.exports);return mod.exports;
}
const page=await component('src/pages/Auth.tsx');
const complaints=await component('src/state/Complaints.tsx');
const authentication=await component('src/state/Auth.tsx',true);
const config={provider:'firebase',configured:true,firebase:{apiKey:'preview',projectId:'preview',authDomain:'preview.test',appId:'preview'}};
const tick=()=>new Promise(resolve=>setImmediate(resolve));
function mount(node){const host=document.createElement('div');document.body.append(host);const root=createRoot(host);return {host,root,async render(){await act(async()=>{root.render(node);await tick();});},async close(){await act(async()=>root.unmount());host.remove();}};}

async function fill(view,selector,value){
  const input=view.host.querySelector(selector);
  assert.ok(input,`Missing input ${selector}`);
  await act(async()=>{
    Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype,'value').set.call(input,value);
    input.dispatchEvent(new window.Event('input',{bubbles:true}));
    await tick();
  });
}

for(const flow of ['register','reset'])test(`${flow} accepts 6–128 characters and still checks the provider policy`,async t=>{
  for(const [length,providerValid] of [[5,true],[6,true],[128,true],[129,true],[6,false]])await t.test(`${length} characters, provider ${providerValid ? 'accepts' : 'rejects'}`,async()=>{
    const password='a'.repeat(length),isRegister=flow==='register';
    let uses=0,validated=0;
    globalThis.__bindrReact={account:{status:'signed-out',config},firebase:{},
      validate:async()=>{validated++;return {isValid:providerValid};},
      createUser:async(auth,email,value)=>{uses++;assert.equal(value,password);return {user:{email,emailVerified:false}};},
      resetPassword:async(auth,code,value)=>{uses++;assert.equal(code,'reset-code');assert.equal(value,password);}};
    const route=isRegister ? '/register' : '/auth/action?mode=resetPassword&oobCode=reset-code';
    const view=mount(React.createElement(MemoryRouter,{initialEntries:[route]},React.createElement(page.default)));
    try{
      await view.render();
      if(isRegister){await fill(view,'[autocomplete="name"]','Example');await fill(view,'[type="email"]','test@example.test');}
      await fill(view,'[aria-label="Password"]',password);
      await fill(view,'[aria-label="Confirm password"]',password);
      const form=view.host.querySelector('form');
      for(const input of form.querySelectorAll('[autocomplete="new-password"]')){
        assert.equal(input.minLength,6);assert.equal(input.maxLength,128);
      }
      // Programmatically filled values bypass native length checks, so also exercise the submit handler.
      await act(async()=>{form.dispatchEvent(new window.Event('submit',{bubbles:true,cancelable:true}));await tick();});
      const accepted=length>=6 && length<=128 && providerValid;
      assert.equal(uses,accepted ? 1 : 0);
      assert.equal(validated,length>=6 && length<=128 ? 1 : 0);
      if(accepted)assert.match(view.host.textContent,isRegister ? /Check your inbox/ : /Your password has been updated/);
      else assert.match(view.host.querySelector('[role="alert"]').textContent,/6–128 characters/);
    }finally{await view.close();}
  });
});

test('a verification link is consumed once under React StrictMode',async()=>{
  let uses=0,finish;
  globalThis.__bindrReact={account:{status:'signed-out',config},firebase:{},apply:()=>{uses++;return new Promise(resolve=>{finish=resolve;});}};
  const view=mount(React.createElement(React.StrictMode,null,React.createElement(MemoryRouter,{initialEntries:['/auth/action?mode=verifyEmail&oobCode=single-use-code']},React.createElement(page.default))));
  try{await view.render();assert.equal(uses,1);await act(async()=>{finish();await tick();});assert.match(view.host.textContent,/Your email is verified/);assert.doesNotMatch(view.host.textContent,/invalid or has already/);}finally{await view.close();}
});

test('cloud draft hydration opens saved wording and does not overwrite later edits',async()=>{
  let value,finish;
  const detail={case:{id:'case-a',version:3},commitments:[],evidence:[]},caseView={detail,row:{company:'Shop',title:'Refund'}};
  globalThis.__bindrReact={account:{status:'signed-in'},request:()=>new Promise(resolve=>{finish=resolve;}),loadCase:async()=>caseView};
  function Probe(){value=complaints.useComplaints();return React.createElement('p',null,value.sessions['case-a']?.body || 'Waiting');}
  const view=mount(React.createElement(complaints.ComplaintsProvider,null,React.createElement(Probe)));
  try{await view.render();await act(async()=>{finish({drafts:[{case_id:'case-a',version:1,case_version:3,subject:'Saved subject',body:'Saved wording from another device'}]});await tick();});assert.equal(value.ready,true);assert.equal(value.sessions['case-a'].stage,'draft');assert.match(view.host.textContent,/Saved wording from another device/);await act(async()=>value.update('case-a',prior=>({...prior,body:'New unsaved words',dirty:true})));assert.match(view.host.textContent,/New unsaved words/);}finally{await view.close();}
});

test('late draft loading cannot replace an edited in-memory draft',async()=>{
  let value,finish;
  globalThis.__bindrReact={account:{status:'signed-in'},request:()=>new Promise(resolve=>{finish=resolve;}),loadCase:async()=>({detail:{case:{id:'case-a',version:3},commitments:[]},row:{company:'Shop',title:'Refund'}})};
  function Probe(){value=complaints.useComplaints();return null;}
  const view=mount(React.createElement(complaints.ComplaintsProvider,null,React.createElement(Probe)));
  try{await view.render();await act(async()=>value.update('case-a',()=>({body:'My newer editing',dirty:true,busy:false})));await act(async()=>{finish({drafts:[{case_id:'case-a',version:1,case_version:3,subject:'Old',body:'Old saved body'}]});await tick();});assert.equal(value.sessions['case-a'].body,'My newer editing');assert.equal(value.saved['case-a'].session.body,'Old saved body');}finally{await view.close();}
});

test('an ended session clears account state and cannot be restored by a late identity read',async()=>{
  let value,finish,pending=false;
  const info={account:{id:'account-a',email:'a@example.test',display_name:'A'},expires_at:Math.floor(Date.now()/1000)+3600};
  globalThis.__bindrReact={request:async path=>path==='/config' ? config : pending ? new Promise(resolve=>{finish=resolve;}) : info};
  function Probe(){value=authentication.useAuth();return React.createElement('p',null,value.info?.account.email || value.status);}
  const view=mount(React.createElement(authentication.AuthProvider,null,React.createElement(Probe)));
  try{await view.render();assert.equal(value.status,'signed-in');pending=true;let reading;await act(async()=>{reading=value.refresh();await tick();});await act(async()=>{window.dispatchEvent(new window.Event('bindr:session-ended'));await tick();});assert.equal(value.status,'signed-out');await act(async()=>{finish(info);await reading;});assert.equal(value.status,'signed-out');assert.equal(value.info,null);}finally{await view.close();}
});
