import test from 'node:test';
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
import {JSDOM,ResourceLoader,VirtualConsole} from 'jsdom';
import React,{act} from 'react';
import {build} from 'esbuild';
const loads=[],executions=[];
class Monitor extends ResourceLoader{fetch(url){loads.push(url);return null;}}
const dom=new JSDOM('<!doctype html><html><body></body></html>',{url:'https://bindr.test',runScripts:'dangerously',resources:new Monitor(),virtualConsole:new VirtualConsole()});
globalThis.window=dom.window;globalThis.document=dom.window.document;globalThis.IS_REACT_ACT_ENVIRONMENT=true;
dom.window.alert=value=>executions.push(value);
const {createRoot}=await import('react-dom/client');
const code=(await build({entryPoints:['src/components/workspace/ProposalReview.tsx'],bundle:true,format:'cjs',platform:'node',packages:'external',jsx:'automatic',loader:{'.css':'empty'},write:false})).outputFiles[0].text;
const mod={exports:{}};new Function('require','module','exports',code)(createRequire(import.meta.url),mod,mod.exports);const View=mod.exports.default;
const payload=`We will refund ₹500 by November 18, 2026. <img src="https://remote.invalid/pixel" onerror="alert('Bindr-XSS-Test')"><script>alert('Bindr-XSS-Test')</script><b>Refund approved</b>`;
test('serialized/reloaded proposal review escapes stored markup and records no execution or resource load',async()=>{
  const p={schema_version:2,proposal_id:'p1',document_warnings:[payload],candidates:[{candidate_id:'c1',terms:{kind:'refund',description:payload,amount_minor:50000,currency:'INR',due_at:null},sources:[{evidence_id:'e1',quote:payload,page:1}],temporal:{wording:payload,parse_status:'invalid'},relation:{kind:'contradiction',explanation:payload,predecessor_id:null},condition:{trigger:payload,status:'unknown'},warnings:[payload]}]};
  // Synthetic persistence boundary. Does not assert real SQL or browser acceptance.
  const saved=JSON.stringify(p);const host=document.createElement('div');document.body.append(host);const root=createRoot(host);
  try{await act(async()=>root.render(React.createElement(View,{proposal:JSON.parse(saved),busy:false,onConfirm:async()=>{}})));assert.match(host.textContent,/<script>alert/);assert.equal(host.querySelector('script,img,b,iframe'),null);assert.deepEqual(executions,[]);assert.deepEqual(loads,[]);}finally{await act(async()=>root.unmount());host.remove();}
});
