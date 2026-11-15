import test from 'node:test';
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
import {JSDOM} from 'jsdom';
import React,{act} from 'react';
import {build} from 'esbuild';
const dom=new JSDOM('<!doctype html><html><body></body></html>',{url:'https://bindr.test'});
globalThis.window=dom.window;globalThis.document=dom.window.document;globalThis.IS_REACT_ACT_ENVIRONMENT=true;
const {createRoot}=await import('react-dom/client');
const code=(await build({stdin:{contents:"export * from './src/state/Capture';export {default as ProposalReview} from './src/components/workspace/ProposalReview';",resolveDir:process.cwd()},bundle:true,format:'cjs',platform:'node',packages:'external',jsx:'automatic',write:false})).outputFiles[0].text;
const mod={exports:{}};new Function('require','module','exports',code)(createRequire(import.meta.url),mod,mod.exports);const m=mod.exports;
const tick=()=>new Promise(r=>setImmediate(r));
test('actual capture survives auth subtree remount, hides while signed out and rejects late cross-account writes',async()=>{
  let value;function Probe(){value=m.useCapture();return React.createElement('p',null,value.session.text);}
  const host=document.createElement('div');document.body.append(host);const root=createRoot(host);
  async function render(account,key){await act(async()=>{root.render(React.createElement(m.CaptureProvider,{account},React.createElement(Probe,{key})));await tick();});}
  try{
    const reviewDraft={proposal_id:'p-a',values:{selected:{c1:true},edits:{c1:{kind:'refund',description:'My corrected wording',amount_minor:50000,currency:'INR',due_at:null}},amounts:{c1:'500'},predecessors:{},dates:{c1:'2026-11-18'},reasons:{c1:'Reviewed the source'}}};
    await render('account-a','before');await act(async()=>value.setSession(s=>({...s,text:'Private ₹500 हिन्दी ગુજરાતી <script>attack()</script>',company:'A',pending:true,step:'processing',v2:{caseId:'case-a',version:2,evidenceIds:[],uploadedKeys:[],proposal:null,job:null,operations:{},manualDescription:'Unsaved manual promise',manualAmount:'500',reviewDraft}})));
    const late=value.setSession;
    await render(null,'signed-out');assert.equal(host.textContent,'');
    await act(async()=>late(s=>({...s,text:'Late response'})));assert.equal(host.textContent,'');
    await render('account-b','other-login');assert.equal(host.textContent,'');await act(async()=>value.setSession(s=>({...s,text:'B private'})));
    await act(async()=>late(s=>({...s,text:'Leaked A'})));assert.equal(host.textContent,'B private');
    await render('account-a','reauthenticated');assert.match(host.textContent,/Private ₹500 हिन्दी ગુજરાતી/);assert.equal(value.session.pending,false);assert.equal(value.session.step,'capture');
    assert.equal(value.session.v2.manualDescription,'Unsaved manual promise');assert.deepEqual(value.session.v2.reviewDraft,reviewDraft);assert.equal(value.session.confirmed,false);
    await act(async()=>late(s=>({...s,text:'Stale A response after reauthentication'})));assert.match(host.textContent,/Private ₹500 हिन्दी ગુજરાતી/);
    assert.equal(localStorageEntries(),0);assert.equal(host.querySelector('script'),null);
    await act(async()=>value.reset());assert.equal(host.textContent,'');
  }finally{await act(async()=>root.unmount());host.remove();}
});
function localStorageEntries(){return window.localStorage.length+window.sessionStorage.length;}
test('edited review terms survive the account subtree remount but require fresh confirmation',async()=>{
  let capture;
  function Editor(){capture=m.useCapture();const state=capture.session.v2;if(!state?.proposal)return null;return React.createElement(m.ProposalReview,{proposal:state.proposal,initialDraft:state.reviewDraft?.values,busy:false,onConfirm:async()=>{},onDraftChange:values=>capture.setSession(old=>({...old,v2:{...old.v2,reviewDraft:{proposal_id:state.proposal.proposal_id,values}}}))});}
  const p={schema_version:2,proposal_id:'p1',document_warnings:[],candidates:[{candidate_id:'c1',terms:{kind:'refund',description:'Original description',amount_minor:50000,currency:'INR',due_at:null},sources:[{evidence_id:'e1',quote:'Refund ₹500.'}],temporal:{wording:null,anchor:null,parse_status:'unknown'},relation:{kind:'new',predecessor_id:null,explanation:'Initial proposal'},condition:{trigger:null,status:'not_applicable'},warnings:[]}]};
  const host=document.createElement('div');document.body.append(host);const root=createRoot(host);
  const render=async account=>act(async()=>{root.render(React.createElement(m.CaptureProvider,{account},React.createElement(Editor,{key:account})));await tick();});
  try{
    await render('review-a');await act(async()=>capture.setSession(s=>({...s,text:'Source retained',v2:{caseId:'case-a',version:2,evidenceIds:['e1'],uploadedKeys:[],proposal:p,job:null,operations:{}}})));
    const field=host.querySelector('textarea');await act(async()=>{Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype,'value').set.call(field,'My reviewed exact words ₹500');field.dispatchEvent(new window.Event('input',{bubbles:true}));await tick();});
    const boxes=host.querySelectorAll('[type=checkbox]');await act(async()=>{boxes[0].click();boxes[1].click();await tick();});assert.equal(boxes[1].checked,true);
    await render(null);assert.equal(host.textContent,'');await render('review-b');assert.equal(host.textContent,'');
    await render('review-a');assert.equal(host.querySelector('textarea').value,'My reviewed exact words ₹500');assert.equal(host.querySelectorAll('[type=checkbox]')[0].checked,true);assert.equal(host.querySelectorAll('[type=checkbox]')[1].checked,false);
    assert.equal(localStorageEntries(),0);
  }finally{await act(async()=>root.unmount());host.remove();}
});
