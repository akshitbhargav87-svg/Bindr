import test from 'node:test';
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
import {JSDOM} from 'jsdom';
import React,{act} from 'react';
import {build} from 'esbuild';
const dom=new JSDOM('<!doctype html><html><body></body></html>',{url:'https://bindr.test'});
globalThis.window=dom.window;globalThis.document=dom.window.document;globalThis.IS_REACT_ACT_ENVIRONMENT=true;
const {createRoot}=await import('react-dom/client');
const code=(await build({entryPoints:['src/state/Capture.tsx'],bundle:true,format:'cjs',platform:'node',packages:'external',jsx:'automatic',write:false})).outputFiles[0].text;
const mod={exports:{}};new Function('require','module','exports',code)(createRequire(import.meta.url),mod,mod.exports);const m=mod.exports;
const tick=()=>new Promise(r=>setImmediate(r));
test('actual capture survives auth subtree remount, hides while signed out and rejects late cross-account writes',async()=>{
  let value;function Probe(){value=m.useCapture();return React.createElement('p',null,value.session.text);}
  const host=document.createElement('div');document.body.append(host);const root=createRoot(host);
  async function render(account,key){await act(async()=>{root.render(React.createElement(m.CaptureProvider,{account},React.createElement(Probe,{key})));await tick();});}
  try{
    await render('account-a','before');await act(async()=>value.setSession(s=>({...s,text:'Private ₹500 हिन्दी ગુજરાતી <script>attack()</script>',company:'A',pending:true,step:'processing'})));
    const late=value.setSession;
    await render(null,'signed-out');assert.equal(host.textContent,'');
    await act(async()=>late(s=>({...s,text:'Late response'})));assert.equal(host.textContent,'');
    await render('account-b','other-login');assert.equal(host.textContent,'');await act(async()=>value.setSession(s=>({...s,text:'B private'})));
    await act(async()=>late(s=>({...s,text:'Leaked A'})));assert.equal(host.textContent,'B private');
    await render('account-a','reauthenticated');assert.match(host.textContent,/Private ₹500 हिन्दी ગુજરાતી/);assert.equal(value.session.pending,false);assert.equal(value.session.step,'capture');
    await act(async()=>late(s=>({...s,text:'Stale A response after reauthentication'})));assert.match(host.textContent,/Private ₹500 हिन्दी ગુજરાતી/);
    assert.equal(localStorageEntries(),0);assert.equal(host.querySelector('script'),null);
    await act(async()=>value.reset());assert.equal(host.textContent,'');
  }finally{await act(async()=>root.unmount());host.remove();}
});
function localStorageEntries(){return window.localStorage.length+window.sessionStorage.length;}
