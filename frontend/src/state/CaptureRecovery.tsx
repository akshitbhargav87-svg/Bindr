import {useEffect,useRef,useState,type ReactNode} from 'react';
import {useAuth} from './Auth';
import {CaptureProvider,useCapture} from './Capture';
import {CaptureDraftController} from '../api/capture-draft';
import {DraftAutosave,V2Client} from '../api/v2';
function CloudCaptureAutosave({account}:{account:string|null}){
  const {session}=useCapture(),controllers=useRef(new Map<string,CaptureDraftController>());
  const [status,setStatus]=useState('');
  useEffect(()=>setStatus(''),[account]);
  const {text,company,title,communicationDate,step}=session;
  useEffect(()=>{
    // Explicit activation after A's capture-draft response profile is reviewed.
    if(import.meta.env.VITE_ENABLE_V2_CAPTURE!=='true' || !account || account==='demo' || !text || step==='saved')return;
    if(!controllers.current.has(account))controllers.current.set(account,new CaptureDraftController(new DraftAutosave(new V2Client(),account),account));
    let live=true;const timer=setTimeout(()=>{setStatus('Saving capture draft…');void controllers.current.get(account)!.save(session).then(()=>{if(live)setStatus('Capture draft saved to your account.');}).catch(()=>{if(live)setStatus('Cloud autosave was not confirmed. Your capture is still in this tab.');});},800);
    return()=>{live=false;clearTimeout(timer);};
  },[account,text,company,title,communicationDate,step]);
  return account && text && step!=='saved' && status ? <p role="status" className="capture-meta">{status}</p> : null;
}
export function AccountCaptureProvider({children}:{children:ReactNode}) {
  const auth=useAuth();
  const account=auth.status==='demo' ? 'demo' : auth.status==='signed-in' ? auth.info?.account.id ?? null : null;
  return <CaptureProvider account={account}><CloudCaptureAutosave account={account}/>{children}</CaptureProvider>;
}
