import {test} from 'node:test';import assert from 'node:assert/strict';import {createServer} from 'node:http';import {build} from 'esbuild';
async function runtime(origin){const code=(await build({stdin:{contents:"export {httpApi,downloadHttpEvidence} from './src/api/http'; export {createMockApi} from './src/api/mock-mutations'; export {prepareCapture} from './src/api/capture';",resolveDir:process.cwd()},bundle:true,format:'esm',platform:'node',write:false,define:{'import.meta.env':JSON.stringify({VITE_USE_MOCK:'false',VITE_API_URL:origin})}})).outputFiles[0].text;return import(`data:text/javascript;base64,${Buffer.from(code).toString('base64')}#http-${crypto.randomUUID()}`);}
const session={session_id:'contract-test',user_id:'anonymous-test',csrf_token:'contract-csrf'};
const envelope=(code,message)=>({error:{code,message,details:[],request_id:'contract-test'}});

test('real HTTP transport completes create/upload/extract/review/revision/draft/download/resolve against a local contract server',async()=>{
  let domain,origin;const audit=[];
  const server=createServer(async(req,res)=>{
    const send=(status,value)=>{res.writeHead(status,{'Content-Type':'application/json'});res.end(JSON.stringify(value));};
    try{
      assert.match(req.headers.cookie ?? '',/pk_session=contract-test/);
      if(req.method==='POST')assert.equal(req.headers['x-csrf-token'],'contract-csrf');
      if(req.url==='/api/v1/auth/session')return send(200,session);
      const path=new URL(req.url,origin).pathname;const parts=path.split('/').filter(Boolean);assert.equal(parts[0],'api');assert.equal(parts[1],'v1');assert.equal(parts[2],'cases');
      let payload,form;
      if(req.method==='POST'){const chunks=[];for await(const chunk of req)chunks.push(chunk);const body=Buffer.concat(chunks);if(req.headers['content-type']?.startsWith('multipart/form-data')){form=await new Request(origin+path,{method:'POST',headers:req.headers,body}).formData();assert.deepEqual([...form.keys()].sort(),['expected_version','file']);}else payload=JSON.parse(body.toString('utf8'));}
      audit.push({method:req.method,path,keys:payload ? Object.keys(payload).sort() : []});
      const id=parts[3];
      if(!id)return send(req.method==='POST' ? 201 : 200,req.method==='POST' ? await domain.createCase(payload) : await domain.listCases());
      if(parts.length===4)return send(200,await domain.getCase(id));
      if(parts[4]==='evidence' && req.method==='POST')return send(201,await domain.uploadEvidence(id,form.get('file'),Number(form.get('expected_version'))));
      if(parts[4]==='evidence' && parts[6]==='content'){
        const detail=await domain.getCase(id);const source=detail.evidence.find(e=>e.id===parts[5]);const file=source && domain.getEvidenceFile(source.id);if(!file)return send(404,envelope('NOT_FOUND','Source not found.'));
        res.writeHead(200,{'Content-Type':file.type,'Cache-Control':'private, no-store','X-Content-Type-Options':'nosniff','Content-Disposition':'attachment; filename="original.txt"'});res.end(Buffer.from(await file.arrayBuffer()));return;
      }
      if(parts[4]==='extractions' && parts[6]==='review')return send(200,await domain.review(id,parts[5],payload));
      if(parts[4]==='extractions')return send(201,await domain.extract(id,payload.evidence_ids,payload.expected_version));
      if(parts[4]==='complaint-draft')return send(200,await domain.complaint(id,payload.expected_version,payload.requested_remedy));
      if(parts[4]==='resolve')return send(200,await domain.resolve(id,payload.expected_version,payload.resolution_note));
      return send(404,envelope('NOT_FOUND','Route not found.'));
    }catch(cause){send(cause.status ?? 500,cause.error ? {error:cause.error} : envelope('CONTRACT_TEST_FAILURE',cause.message));}
  });
  await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));origin=`http://127.0.0.1:${server.address().port}`;
  const m=await runtime(origin);domain=m.createMockApi([],[],'2026-11-14');
  const originalFetch=globalThis.fetch,originalDocument=globalThis.document;globalThis.document={cookie:'pk_csrf=contract-csrf'};
  // Simulate browser cookie transport for Node fetch. This is not production auth/CORS verification.
  globalThis.fetch=(url,options)=>{assert.equal(options.credentials,'include');assert.equal(options.cache,'no-store');const headers=new Headers(options.headers);headers.set('Cookie','pk_session=contract-test');return originalFetch(url,{...options,headers});};
  try{
    const api=m.httpApi;const made=await api.createCase({title:'Refund for returned order',merchant_name:'Contract Test Shop'});const id=made.case.id;
    const text='We will refund INR 4999 for the returned order by 2026-11-18.';const upload=await api.uploadEvidence(id,new File([text],'original.txt',{type:'text/plain'}),made.case.version);
    const extraction=await api.extract(id,[upload.evidence.id],upload.case_version);assert.equal((await api.getCase(id)).commitments.length,0);
    const candidate=extraction.extraction.candidates[0];
    const reviewed=await api.review(id,extraction.extraction.id,{expected_version:extraction.case_version,decision:'approve',items:[{candidate_id:candidate.candidate_id,action:'new',supersedes_id:null,terms:candidate.terms,evidence_ids:[upload.evidence.id]}]});
    const second=await api.uploadEvidence(id,new File(['We will refund INR 4999 by 2026-11-20.'],'revised.txt',{type:'text/plain'}),reviewed.case_version);
    const next=await api.extract(id,[second.evidence.id],second.case_version);const proposed=next.extraction.candidates[0];const payload={expected_version:next.case_version,decision:'approve',items:[{candidate_id:proposed.candidate_id,action:'revision',supersedes_id:reviewed.commitments[0].id,terms:proposed.terms,evidence_ids:[upload.evidence.id,second.evidence.id]}]};
    const revised=await api.review(id,next.extraction.id,payload);await assert.rejects(()=>api.review(id,next.extraction.id,payload),e=>e.status===409);
    const detail=await api.getCase(id);assert.equal(detail.commitments.length,2);assert.equal(detail.commitments[0].status,'superseded');assert.equal(detail.commitments[1].supersedes_id,detail.commitments[0].id);assert.equal(detail.commitments[0].due_at,'2026-11-18T18:29:59Z');
    const draft=await api.complaint(id,revised.case_version,'Complete the outstanding refund.');assert.equal(draft.case_version,revised.case_version);assert.match(draft.draft.body,/18 Nov 2026/);assert.match(draft.draft.body,/20 Nov 2026/);
    assert.equal(await (await m.downloadHttpEvidence(upload.evidence)).text(),text);
    const resolved=await api.resolve(id,revised.case_version,'Received in full.');assert.equal(resolved.case.status,'resolved');assert.equal((await api.listCases()).cases[0].status,'resolved');assert.equal((await api.getCase(id)).commitments[0].status,'superseded');
    assert.deepEqual(audit.find(a=>a.path.endsWith('/complaint-draft')).keys,['expected_version','requested_remedy']);assert.ok(audit.every(a=>!a.path.includes('send') && !a.path.includes('notify')));
  }finally{globalThis.fetch=originalFetch;if(originalDocument===undefined)delete globalThis.document;else globalThis.document=originalDocument;await new Promise(resolve=>{server.close(resolve);server.closeAllConnections();});}
});

test('an invalid successful response is uncertain and cannot trigger another create request',async()=>{
  const m=await runtime('http://localhost:8000/api/v1/');const oldFetch=globalThis.fetch,oldDocument=globalThis.document;let calls=0,job;globalThis.document={cookie:''};globalThis.fetch=async url=>{if(url.endsWith('/auth/session'))return Response.json(session);calls++;return Response.json({unexpected:'response'});};
  const input={company:'Test Shop',title:'Refund',sources:[{key:'one',file:new File(['We will refund INR 100 by 2026-11-20.'],'message.txt',{type:'text/plain'}),communicationDate:'2026-11-14',error:null}]};
  try{await assert.rejects(()=>m.prepareCapture(input,null,value=>{job=value;}),/could not be verified/);assert.equal(job.state,'needs-reconciliation');await assert.rejects(()=>m.prepareCapture(input,job,()=>{}),/latest case state/);assert.equal(calls,1);}finally{globalThis.fetch=oldFetch;if(oldDocument===undefined)delete globalThis.document;else globalThis.document=oldDocument;}
});
test('HTML auth errors stay typed and malformed CSRF cookies block mutations before transport',async()=>{
  const m=await runtime('http://localhost:8000');const oldFetch=globalThis.fetch,oldDocument=globalThis.document;let calls=0;globalThis.document={cookie:''};globalThis.fetch=async()=>{calls++;return new Response('<html>Internal session details</html>',{status:401});};
  try{await assert.rejects(()=>m.httpApi.listCases(),e=>e.status===401 && !e.message.includes('Internal'));globalThis.document.cookie='other=value;pk_csrf=%ZZ';await assert.rejects(()=>m.httpApi.createCase({title:'Refund',merchant_name:'Test'}),e=>e.status===403);assert.equal(calls,2);}finally{globalThis.fetch=oldFetch;if(oldDocument===undefined)delete globalThis.document;else globalThis.document=oldDocument;}
});
test('cross-case children in a successful detail response are rejected',async()=>{
  const m=await runtime('http://localhost:8000');const domain=m.createMockApi([],[],'2026-11-14');const made=await domain.createCase({title:'Refund',merchant_name:'Test Shop'});await domain.uploadEvidence(made.case.id,new File(['Source'],'message.txt',{type:'text/plain'}),1);const detail=await domain.getCase(made.case.id);detail.evidence[0].case_id=crypto.randomUUID();
  const oldFetch=globalThis.fetch,oldDocument=globalThis.document;globalThis.document={cookie:''};globalThis.fetch=async url=>Response.json(url.endsWith('/auth/session') ? session : detail);
  try{await assert.rejects(()=>m.httpApi.getCase(made.case.id),/could not be verified/);}finally{globalThis.fetch=oldFetch;if(oldDocument===undefined)delete globalThis.document;else globalThis.document=oldDocument;}
});


test('a new browser session is created once, without a caller-selected identity, before concurrent domain reads',async()=>{
  const m=await runtime('http://localhost:8000');const oldFetch=globalThis.fetch,oldDocument=globalThis.document;const calls=[];let established=false;globalThis.document={cookie:''};
  globalThis.fetch=async(url,options)=>{calls.push({url,options});if(url.endsWith('/auth/session')){if(options.method==='POST'){assert.deepEqual(JSON.parse(options.body),{});established=true;globalThis.document.cookie='pk_csrf=contract-csrf';return Response.json(session,{status:201});}return new Response('',{status:401});}assert.equal(established,true);return Response.json({cases:[]});};
  try{await Promise.all([m.httpApi.listCases(),m.httpApi.listCases()]);assert.equal(calls.filter(call=>call.url.endsWith('/auth/session')).length,2);assert.equal(calls.filter(call=>call.options.method==='POST').length,1);await m.httpApi.listCases();assert.equal(calls.filter(call=>call.url.endsWith('/auth/session')).length,2);}finally{globalThis.fetch=oldFetch;if(oldDocument===undefined)delete globalThis.document;else globalThis.document=oldDocument;}
});
