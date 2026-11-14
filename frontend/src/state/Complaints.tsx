import { createContext,useCallback,useContext,useEffect,useRef,useState,type ReactNode } from 'react';
import type { ComplaintSession,SavedComplaint } from '../api/complaint-model';
const Context=createContext<{sessions:Record<string,ComplaintSession>;saved:Record<string,SavedComplaint>;update:(id:string,change:(prior:ComplaintSession|undefined)=>ComplaintSession)=>void;save:(id:string)=>void;remove:(id:string)=>void}|null>(null);
export function ComplaintsProvider({children}:{children:ReactNode}) {
  const [sessions,setSessions]=useState<Record<string,ComplaintSession>>({});const [saved,setSaved]=useState<Record<string,SavedComplaint>>({});
  const removed=useRef(new Set<string>());
  const update=useCallback((id:string,change:(prior:ComplaintSession|undefined)=>ComplaintSession)=>setSessions(previous=>removed.current.has(id) ? previous : {...previous,[id]:change(previous[id])}),[]);
  function save(id:string){const session=sessions[id];if(!session?.snapshot)return;setSaved(previous=>({...previous,[id]:{caseId:id,company:session.snapshot!.row.company,title:session.snapshot!.row.title,subject:session.subject,session:structuredClone({...session,dirty:false,busy:false})}}));update(id,previous=>({...previous!,dirty:false}));}
  function remove(id:string){removed.current.add(id);setSessions(previous=>{const next={...previous};delete next[id];return next;});setSaved(previous=>{const next={...previous};delete next[id];return next;});}
  const hasWork=Object.values(sessions).some(s=>Boolean(s.body) || s.dirty || s.busy);
  useEffect(()=>{if(!hasWork)return;const warn=(event:BeforeUnloadEvent)=>{event.preventDefault();event.returnValue='';};window.addEventListener('beforeunload',warn);return()=>window.removeEventListener('beforeunload',warn);},[hasWork]);
  return <Context.Provider value={{sessions,saved,update,save,remove}}>{children}</Context.Provider>;
}
export function useComplaints(){const value=useContext(Context);if(!value)throw new Error('ComplaintsProvider is required');return value;}
