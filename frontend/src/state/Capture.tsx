import { createContext, useContext, useEffect, useState, type Dispatch, type ReactNode, type SetStateAction } from 'react';
import type { CaptureSession } from '../api/capture-model';
export function newCapture(): CaptureSession {return {tab:'upload',company:'',title:'',text:'',communicationDate:'',sources:[],scenario:'standard',step:'capture',job:null,fields:[],manual:false,confirmed:false,allowDuplicate:false,error:null,progress:'',savedId:null,evidenceOnly:false,savedDescription:'',formErrors:{},pending:false};}
const Context=createContext<{session:CaptureSession;setSession:Dispatch<SetStateAction<CaptureSession>>;reset:()=>void}|null>(null);
export function CaptureProvider({children}:{children:ReactNode}) {
  const [session,setSession]=useState(newCapture);
  const dirty=session.step!=='saved' && Boolean(session.text || session.sources.length || session.job?.caseId);
  useEffect(()=>{if(!dirty)return;const warn=(event:BeforeUnloadEvent)=>{event.preventDefault();event.returnValue='';};window.addEventListener('beforeunload',warn);return()=>window.removeEventListener('beforeunload',warn);},[dirty]);
  return <Context.Provider value={{session,setSession,reset:()=>setSession(newCapture())}}>{children}</Context.Provider>;
}
export function useCapture(){const value=useContext(Context);if(!value)throw new Error('CaptureProvider is required');return value;}
