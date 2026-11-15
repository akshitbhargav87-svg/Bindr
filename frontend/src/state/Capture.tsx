import { createContext, useContext, useEffect, useRef, useReducer, type Dispatch, type ReactNode, type SetStateAction } from 'react';
import type { CaptureSession } from '../api/capture-model';
export function newCapture(): CaptureSession {return {tab:'upload',company:'',title:'',text:'',communicationDate:'',sources:[],scenario:'standard',step:'capture',job:null,fields:[],manual:false,confirmed:false,allowDuplicate:false,error:null,progress:'',savedId:null,evidenceOnly:false,savedDescription:'',formErrors:{},pending:false};}
const Context=createContext<{session:CaptureSession;setSession:Dispatch<SetStateAction<CaptureSession>>;reset:()=>void}|null>(null);
export function CaptureProvider({children,account='demo'}:{children:ReactNode;account?:string|null}) {
  // Mounted outside the keyed auth subtree. Never persist sensitive drafts in browser storage.
  const drafts=useRef(new Map<string,CaptureSession>());
  const active=useRef(account),epoch=useRef(0);
  if(active.current!==account){active.current=account;epoch.current++;}
  const writerEpoch=epoch.current;
  const [,render]=useReducer(n=>n+1,0);
  if(account && !drafts.current.has(account))drafts.current.set(account,newCapture());
  const session=account ? drafts.current.get(account)! : newCapture();
  const setSession:Dispatch<SetStateAction<CaptureSession>>=update=>{
    if(!account || active.current!==account || epoch.current!==writerEpoch)return;
    const before=drafts.current.get(account) ?? newCapture();
    drafts.current.set(account,typeof update==='function' ? update(before) : update);render();
  };
  useEffect(()=>()=>{
    if(!account)return;
    const previous=drafts.current.get(account);
    if(previous && previous.step!=='saved' && (previous.text || previous.sources.length || previous.job))drafts.current.set(account,{...previous,pending:false,confirmed:false,
      step:previous.pending ? 'capture' : previous.step,
      error:previous.pending ? 'Your session changed during a request. Review the latest case state before retrying.' : 'Your capture stayed in this tab. Review it before confirming after sign-in.',
      job:previous.pending && previous.job ? {...previous.job,state:'needs-reconciliation'} : previous.job});
  },[account]);
  const dirty=session.step!=='saved' && Boolean(session.text || session.sources.length || session.job?.caseId);
  useEffect(()=>{if(!dirty)return;const warn=(event:BeforeUnloadEvent)=>{event.preventDefault();event.returnValue='';};window.addEventListener('beforeunload',warn);return()=>window.removeEventListener('beforeunload',warn);},[dirty]);
  return <Context.Provider value={{session,setSession,reset:()=>setSession(newCapture())}}>{children}</Context.Provider>;
}
export function useCapture(){const value=useContext(Context);if(!value)throw new Error('CaptureProvider is required');return value;}
