import { createContext,useCallback,useContext,useEffect,useRef,useState,type ReactNode } from 'react';
import type { ComplaintSession,SavedComplaint } from '../api/complaint-model';
import { useAuth } from './Auth';
import { accountRequest } from '../api/account';
import { loadCase } from '../api/case-service';
import { restoreCloudDraft,type CloudDraft } from '../api/cloud-drafts';
const Context=createContext<{sessions:Record<string,ComplaintSession>;saved:Record<string,SavedComplaint>;update:(id:string,change:(prior:ComplaintSession|undefined)=>ComplaintSession)=>void;save:(id:string)=>Promise<void>;remove:(id:string)=>void;error:string|null;ready:boolean}|null>(null);
export function ComplaintsProvider({children}:{children:ReactNode}) {
  const [sessions,setSessions]=useState<Record<string,ComplaintSession>>({});const [saved,setSaved]=useState<Record<string,SavedComplaint>>({});
  const removed=useRef(new Set<string>());
  const auth=useAuth(),cloud=auth.status==='signed-in';const versions=useRef<Record<string,number>>({});const [error,setError]=useState<string|null>(null),[ready,setReady]=useState(!cloud);const saving=useRef(false);
  useEffect(()=>{if(!cloud)return;let active=true;(async()=>{try{const data=await accountRequest<{drafts:CloudDraft[]}>('/drafts');const entries=await Promise.all(data.drafts.map(async d=>{const view=await loadCase(d.case_id);return [d.case_id,restoreCloudDraft(d,view),d.version] as const;}));if(active){setSaved(Object.fromEntries(entries.map(([id,saved])=>[id,saved])));setSessions(previous=>{const next={...previous};for(const [id,saved] of entries)if(!next[id] || (!next[id].body && !next[id].busy && !next[id].dirty))next[id]=structuredClone(saved.session);return next;});versions.current=Object.fromEntries(entries.map(([id,,v])=>[id,v]));setReady(true);}}catch{if(active)setError('Saved cloud drafts could not be loaded. Reload before saving a replacement.');}})();return()=>{active=false;};},[cloud]);
  const update=useCallback((id:string,change:(prior:ComplaintSession|undefined)=>ComplaintSession)=>setSessions(previous=>removed.current.has(id) ? previous : {...previous,[id]:change(previous[id])}),[]);
  async function save(id:string){const session=sessions[id];if(!session?.snapshot)return;if(saving.current)throw new Error('A draft is already being saved.');if(cloud&&!ready)throw new Error('Reload to load your saved cloud drafts first.');if(session.needsRefresh)throw new Error('Review the latest case facts before saving this wording.');saving.current=true;try{if(cloud){const result=await accountRequest<{version:number}>(`/drafts/${encodeURIComponent(id)}`,{expected_version:versions.current[id] ?? 0,case_version:session.snapshot.detail.case.version,subject:session.subject,body:session.body},'PUT');versions.current[id]=result.version;}setSaved(previous=>({...previous,[id]:{caseId:id,company:session.snapshot!.row.company,title:session.snapshot!.row.title,subject:session.subject,session:structuredClone({...session,dirty:false,busy:false})}}));update(id,previous=>({...previous!,dirty:previous?.subject!==session.subject || previous?.body!==session.body}));setError(null);}finally{saving.current=false;}}
  function remove(id:string){removed.current.add(id);setSessions(previous=>{const next={...previous};delete next[id];return next;});setSaved(previous=>{const next={...previous};delete next[id];return next;});}
  const hasWork=Object.values(sessions).some(s=>s.dirty || s.busy);
  useEffect(()=>{if(!hasWork)return;const warn=(event:BeforeUnloadEvent)=>{event.preventDefault();event.returnValue='';};window.addEventListener('beforeunload',warn);return()=>window.removeEventListener('beforeunload',warn);},[hasWork]);
  return <Context.Provider value={{sessions,saved,update,save,remove,error,ready}}>{children}</Context.Provider>;
}
export function useComplaints(){const value=useContext(Context);if(!value)throw new Error('ComplaintsProvider is required');return value;}
