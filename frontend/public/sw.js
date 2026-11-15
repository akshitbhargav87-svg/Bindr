// Install support only. Never cache private APIs, authenticated HTML or evidence.
self.addEventListener('install',()=>self.skipWaiting());
self.addEventListener('activate',event=>event.waitUntil(self.clients.claim()));
const shares=new Map();
// POST content stays out of URLs, caches and the login screen. The memory-only
// handoff is bound to the resulting browser client and expires after ten minutes.
self.addEventListener('fetch',event=>{
  const url=new URL(event.request.url);
  if(url.origin!==self.location.origin || url.pathname!=='/app/share' || event.request.method!=='POST')return;
  event.respondWith((async()=>{
    try{
      if(!event.resultingClientId)throw new Error('No client');
      const form=await event.request.formData(),files=form.getAll('files').filter(f=>f instanceof File);
      const text=[form.get('text'),form.get('url')].filter(v=>typeof v==='string').join('\n');
      if(text.length>50000 || files.length>10 || files.reduce((n,f)=>n+f.size,0)>10*1024*1024)throw new Error('Share too large');
      for(const [id,value] of shares)if(value.expires<Date.now())shares.delete(id);
      if(shares.size>=10)throw new Error('Too many pending shares');
      shares.set(event.resultingClientId,{text,title:String(form.get('title') ?? '').slice(0,200),files,expires:Date.now()+600000});
      return await fetch('/');
    }catch{return Response.redirect(self.location.origin+'/app/share#unavailable',303);}
  })());
});
self.addEventListener('message',event=>{
  if(event.data?.type!=='bindr:take-share' || !event.source?.id || !event.ports[0])return;
  const value=shares.get(event.source.id);shares.delete(event.source.id);
  event.ports[0].postMessage(value && value.expires>Date.now() ? value : null);
});
