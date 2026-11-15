import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import vm from 'node:vm';
test('extension has explicit active-tab permissions and no credentials or host access',async()=>{
  const manifest=JSON.parse(await readFile('../extensions/chrome/manifest.json','utf8'));
  assert.deepEqual(manifest.permissions,['activeTab','scripting']);assert.equal(manifest.host_permissions,undefined);assert.equal(manifest.content_scripts,undefined);assert.equal(manifest.background,undefined);
  const source=await readFile('../extensions/chrome/popup.js','utf8');assert.doesNotMatch(source,/cookies\.|localStorage|<all_urls>|innerHTML/);assert.match(source,/captureVisibleTab/);assert.match(source,/getSelection/);
});
test('PWA POST sharing is ephemeral, client-bound, one-use, bounded and never caches private data',async()=>{
  const manifest=JSON.parse(await readFile('public/manifest.webmanifest','utf8'));assert.equal(manifest.share_target.method,'POST');
  const handlers={},network=[];const context={self:{location:{origin:'https://bindr.test'},addEventListener:(name,handler)=>handlers[name]=handler},URL,File,Response,Date,Map,fetch:async url=>{network.push(url);return new Response('<html>shell</html>');}};
  vm.runInNewContext(await readFile('public/sw.js','utf8'),context);
  const form=new FormData();form.append('text','Private ₹500 message');form.append('files',new File(['original'],'proof.txt'));
  let response;handlers.fetch({request:new Request('https://bindr.test/app/share',{method:'POST',body:form}),resultingClientId:'tab-a',respondWith:p=>response=p});assert.equal((await response).status,200);
  const take=id=>{let data='not returned';handlers.message({data:{type:'bindr:take-share'},source:{id},ports:[{postMessage:value=>data=value}]});return data;};
  assert.equal(take('tab-b'),null);assert.equal(take('tab-a').text,'Private ₹500 message');assert.equal(take('tab-a'),null);assert.deepEqual(network,['/']);
  let oversized;const huge=new FormData();huge.append('text','x'.repeat(50001));handlers.fetch({request:new Request('https://bindr.test/app/share',{method:'POST',body:huge}),resultingClientId:'tab-c',respondWith:p=>oversized=p});assert.equal((await oversized).status,303);assert.equal(take('tab-c'),null);
  const source=await readFile('public/sw.js','utf8');assert.doesNotMatch(source,/caches\.|indexedDB|localStorage|sessionStorage/);
});
