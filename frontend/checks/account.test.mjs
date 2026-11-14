import test from 'node:test';
import assert from 'node:assert/strict';
import {build} from 'esbuild';
const code=(await build({stdin:{contents:"export {safeReturnTo,authMessage,accountCsrf,accountRequest} from './src/api/account';",resolveDir:process.cwd()},bundle:true,format:'esm',platform:'node',external:['@firebase/app','@firebase/auth'],write:false,define:{'import.meta.env':JSON.stringify({VITE_API_URL:'/api/v1'})}})).outputFiles[0].text;
const api=await import(`data:text/javascript;base64,${Buffer.from(code).toString('base64')}`);

test('account return paths cannot navigate to external sites or backslash URLs',()=>{
  for(const value of [null,'https://evil.test','//evil.test','javascript:alert(1)','/application','/app\\evil.test'])assert.equal(api.safeReturnTo(value),'/app');
  assert.equal(api.safeReturnTo('/app/cases?status=overdue'),'/app/cases?status=overdue');
});

test('credential errors do not reveal whether an email exists or expose provider diagnostics',()=>{
  const common=api.authMessage({code:'auth/invalid-credential'});
  assert.equal(api.authMessage({code:'auth/wrong-password'}),common);
  assert.equal(api.authMessage({code:'auth/user-not-found'}),common);
  assert.doesNotMatch(api.authMessage({code:'auth/unknown',message:'private provider response'}),/private/);
  assert.match(api.authMessage({code:'auth/invalid-verification-code'}),/incorrect or expired/);
});

test('new account CSRF cookies take precedence over the legacy anonymous cookie',()=>{
  const previous=globalThis.document;
  try{globalThis.document={cookie:'pk_csrf=old; bindr_csrf=dev; __Host-bindr_csrf=secure'};assert.equal(api.accountCsrf(),'secure');globalThis.document.cookie='pk_csrf=old';assert.equal(api.accountCsrf(),'');}finally{globalThis.document=previous;}
});

test('account writes use credentialed no-store transport and never automatically retry',async()=>{
  const previousFetch=globalThis.fetch,previousDocument=globalThis.document;let count=0;
  globalThis.document={cookie:'__Host-bindr_csrf=session-bound-token'};
  globalThis.fetch=async(url,options)=>{count++;assert.equal(url,'/api/v1/auth/preferences');assert.equal(options.credentials,'include');assert.equal(options.cache,'no-store');assert.equal(options.method,'PUT');assert.equal(options.headers['X-CSRF-Token'],'session-bound-token');return Response.json({error:{code:'VERSION_CONFLICT',message:'Review the latest settings.'}},{status:409});};
  try{await assert.rejects(()=>api.accountRequest('/preferences',{expected_version:1},'PUT'),e=>e.status===409&&e.code==='VERSION_CONFLICT');assert.equal(count,1);}finally{globalThis.fetch=previousFetch;globalThis.document=previousDocument;}
});
