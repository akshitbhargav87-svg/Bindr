import test from 'node:test';
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
import React,{act} from 'react';
import {JSDOM} from 'jsdom';
import {build} from 'esbuild';
import {serveFixture} from './fixtures/v2-server.mjs';
const dom=new JSDOM('<!doctype html><html><body></body></html>',{url:'https://bindr.test/'});
globalThis.window=dom.window;globalThis.document=dom.window.document;globalThis.IS_REACT_ACT_ENVIRONMENT=true;document.cookie='bindr_csrf=synthetic';
const {createRoot}=await import('react-dom/client'),{MemoryRouter}=await import('react-router-dom');
const bundle=(await build({stdin:{contents:"export {default as Capture} from './src/pages/IntelligenceCapture';export {CaptureProvider,useCapture} from './src/state/Capture';export {setAccountContext} from './src/api/account-context';",resolveDir:process.cwd()},bundle:true,format:'cjs',platform:'node',packages:'external',jsx:'automatic',loader:{'.css':'empty'},define:{'import.meta.env':JSON.stringify({VITE_ENABLE_V2_CAPTURE:'true'})},write:false})).outputFiles[0].text;
const require=createRequire(import.meta.url),tick=()=>new Promise(r=>setImmediate(r));
async function until(predicate){for(let i=0;i<80;i++){let done;await act(async()=>{await new Promise(r=>setTimeout(r,10));done=predicate();});if(done)return;}assert.fail('Expected capture state did not arrive.');}
for(const loseResponse of [false,true])test(`actual v2 capture uses extraction version and saves once${loseResponse ? ' after an uncertain upload replay' : ''}`,async()=>{
  const server=await serveFixture({versionedExtraction:true}),transport=globalThis.fetch,calls=[];let dropped=false,hook;
  globalThis.fetch=async(url,options={})=>{const target=new URL(url,server.base);calls.push({path:target.pathname,method:options.method ?? 'GET',key:options.headers?.['Idempotency-Key']});const response=await transport(target,{...options,headers:{...options.headers,'X-Fixture-Owner':'flow-owner'}});if(loseResponse && !dropped && target.pathname.endsWith('/evidence') && options.method==='POST'){dropped=true;throw new TypeError('Synthetic response lost after upload');}return response;};
  const module={exports:{}};new Function('require','module','exports',bundle)(require,module,module.exports);const m=module.exports;m.setAccountContext('flow-owner');
  function Probe(){hook=m.useCapture();return React.createElement(m.Capture);}
  const host=document.createElement('div');document.body.append(host);const root=createRoot(host);
  async function extract(){const button=[...host.querySelectorAll('button')].find(b=>b.textContent==='Extract all proposals');await act(async()=>{button.click();await tick();});}
  try{
    await act(async()=>root.render(React.createElement(MemoryRouter,null,React.createElement(m.CaptureProvider,{account:'flow-owner'},React.createElement(Probe)))));
    await act(async()=>hook.setSession(s=>({...s,company:'Synthetic Shop',title:'Refund',text:'We will refund ₹500.',communicationDate:'2026-11-14'})));
    await extract();
    if(loseResponse){await until(()=>Boolean(hook.session.error));assert.match(hook.session.error,/response lost/);assert.equal(hook.session.text,'We will refund ₹500.');await extract();}
    await until(()=>Boolean(hook.session.v2?.proposal));assert.equal(hook.session.v2.version,3);
    const boxes=host.querySelectorAll('[type=checkbox]');await act(async()=>{boxes[0].click();boxes[1].click();});
    const confirm=[...host.querySelectorAll('button')].find(b=>b.textContent==='Confirm selected proposals');await act(async()=>{confirm.click();confirm.click();});
    await until(()=>hook.session.step==='saved');
    const current=await (await transport(server.base+`/cases/${hook.session.v2.caseId}`,{headers:{'X-Fixture-Owner':'flow-owner','X-Bindr-Account':'flow-owner'}})).json();
    assert.equal(current.version,4);assert.equal(current.obligations.length,1);assert.equal(current.obligations[0].terms.amount_minor,50000);
    assert.equal(calls.filter(c=>c.method==='POST' && c.path==='/api/v2/cases').length,1);assert.equal(calls.filter(c=>c.path.endsWith('/reviews')).length,1);
    const uploads=calls.filter(c=>c.path.endsWith('/evidence'));assert.equal(uploads.length,loseResponse ? 2 : 1);if(loseResponse)assert.equal(uploads[0].key,uploads[1].key);
  }finally{await act(async()=>root.unmount());host.remove();globalThis.fetch=transport;await server.close();}
});
