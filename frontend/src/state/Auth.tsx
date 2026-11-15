import { createContext,useCallback,useContext,useEffect,useRef,useState,type ReactNode } from 'react';
import { Navigate,useLocation,Outlet } from 'react-router-dom';
import type { User } from '@firebase/auth';
import { isMock } from '../api';
import { resetHttpSession } from '../api/http';
import { setAccountContext } from '../api/account-context';
import { accountRequest,firebaseAuth,type AuthConfig,type AccountInfo } from '../api/account';
type Status='loading'|'signed-in'|'signed-out'|'unavailable'|'demo';
function useAuthState(){
  const [status,setStatus]=useState<Status>(isMock ? 'demo' : 'loading'),[config,setConfig]=useState<AuthConfig|null>(null),[info,setInfo]=useState<AccountInfo|null>(null),[error,setError]=useState('');
  const sequence=useRef(0),identity=useRef<string|null>(null),channel=useRef<BroadcastChannel|null>(null);
  const clear=useCallback((next:Status)=>{sequence.current++;identity.current=null;setAccountContext(null);resetHttpSession();setInfo(null);setStatus(next);},[]);
  const refresh=useCallback(async()=>{
    if(isMock)return false;
    const requestId=++sequence.current;
    try{
      const me=await accountRequest<AccountInfo>('/me');
      if(requestId!==sequence.current)return false;
      if(identity.current!==me.account.id)resetHttpSession();
      identity.current=me.account.id;setAccountContext(me.account.id);setInfo(me);setStatus('signed-in');setError('');return true;
    }catch(cause){
      if(requestId!==sequence.current)return false;
      if((cause as {status?:number}).status===401){clear('signed-out');return false;}
      clear('unavailable');setError('Could not reach the sign-in service. Please check your connection.');throw cause;
    }
  },[clear]);
  useEffect(()=>{
    if(isMock)return;let active=true;
    (async()=>{try{const c=await accountRequest<AuthConfig>('/config');if(!active)return;setConfig(c);
      if(c.provider==='anonymous'){
        // Server-advertised development mode only. Deployed startup forbids it.
        // Open the existing browser workspace before v2 requests need its identity.
        if(import.meta.env.VITE_ENABLE_V2_CAPTURE==='true'){
          const {api}=await import('../api');await api.listCases();
          const session=await accountRequest<{user_id:string}>('/session');
          if(!active)return;
          if(typeof session.user_id!=='string' || !session.user_id)throw new Error('Workspace identity unavailable.');
          setAccountContext(session.user_id);
        }
        setStatus('demo');return;
      }
      if(!c.configured){clear('unavailable');setError('Account sign-in is being set up. Please try again later.');return;}
      await refresh();
    }catch{if(active){clear('unavailable');setError('Could not reach the sign-in service. Please check your connection.');}}})();
    return()=>{active=false;sequence.current++;};
  },[refresh,clear]);
  useEffect(()=>{
    if(isMock)return;
    const ended=()=>clear('signed-out');
    window.addEventListener('bindr:session-ended',ended);
    return()=>window.removeEventListener('bindr:session-ended',ended);
  },[clear]);
  useEffect(()=>{
    if(isMock || config?.provider!=='firebase' || !config.configured)return;
    const check=()=>{if(document.visibilityState==='visible')void refresh().catch(()=>{});};
    const changed=()=>{clear('loading');void refresh().catch(()=>{});};
    window.addEventListener('focus',check);document.addEventListener('visibilitychange',check);
    if(typeof BroadcastChannel!=='undefined'){channel.current=new BroadcastChannel('bindr-account');channel.current.onmessage=changed;}
    return()=>{window.removeEventListener('focus',check);document.removeEventListener('visibilitychange',check);channel.current?.close();channel.current=null;};
  },[config,clear,refresh]);
  useEffect(()=>{if(!info)return;const timer=window.setTimeout(()=>clear('signed-out'),Math.max(0,info.expires_at*1000-Date.now()));return()=>window.clearTimeout(timer);},[info,clear]);
  async function complete(user:User){
    if(!user.emailVerified)throw new Error('Verify your email address before opening your workspace.');
    const nonce=await accountRequest<{csrf_token:string}>('/csrf');
    await accountRequest('/login',{id_token:await user.getIdToken(true)},'POST',{'X-CSRF-Token':nonce.csrf_token});
    resetHttpSession();
    if(!await refresh())throw new Error('Please sign in again to open your account.');
    channel.current?.postMessage('changed');
  }
  async function logout(everywhere=false){
    await accountRequest(everywhere ? '/sign-out-everywhere' : '/logout',{});
    clear('signed-out');channel.current?.postMessage('changed');
    if(config){try{await (await import('@firebase/auth')).signOut(await firebaseAuth(config));}catch{/* The server session is already revoked. */}}
  }
  return {status,config,info,error,refresh,complete,logout};
}
const Context=createContext<ReturnType<typeof useAuthState>|null>(null);
export function AuthProvider({children}:{children:ReactNode}){return <Context.Provider value={useAuthState()}>{children}</Context.Provider>;}
export function useAuth(){const c=useContext(Context);if(!c)throw new Error('AuthProvider is required');return c;}
export function AccountGate(){const auth=useAuth(),location=useLocation();if(auth.status==='loading')return <main className="auth-loading" role="status">Opening your secure workspace…</main>;if(auth.status==='unavailable')return <main className="auth-loading"><h1>Let’s reconnect.</h1><p role="alert">{auth.error}</p><button className="button button-primary" onClick={()=>window.location.reload()}>Try again</button></main>;if(auth.status==='signed-out')return <Navigate to={`/login?returnTo=${encodeURIComponent(location.pathname+location.search)}`} replace/>;return <Outlet/>;}
