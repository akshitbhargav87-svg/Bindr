import { createContext,useCallback,useContext,useEffect,useState,type ReactNode } from 'react';
import { Navigate,useLocation,Outlet } from 'react-router-dom';
import type { User } from '@firebase/auth';
import { isMock } from '../api';
import { resetHttpSession } from '../api/http';
import { accountRequest,firebaseAuth,type AuthConfig,type AccountInfo } from '../api/account';
type Status='loading'|'signed-in'|'signed-out'|'unavailable'|'demo';
function useAuthState(){
  const [status,setStatus]=useState<Status>(isMock ? 'demo' : 'loading'),[config,setConfig]=useState<AuthConfig|null>(null),[info,setInfo]=useState<AccountInfo|null>(null),[error,setError]=useState('');
  const refresh=useCallback(async()=>{if(isMock)return;try{const me=await accountRequest<AccountInfo>('/me');setInfo(me);setStatus('signed-in');}catch(cause){setInfo(null);if((cause as {status?:number}).status===401){setStatus('signed-out');return;}throw cause;}},[]);
  useEffect(()=>{if(isMock)return;let active=true;(async()=>{try{const c=await accountRequest<AuthConfig>('/config');if(!active)return;setConfig(c);if(c.provider==='anonymous'){setStatus('demo');return;}if(!c.configured){setStatus('unavailable');setError('Account sign-in is being set up. Please try again later.');return;}if(active)await refresh();}catch{if(active){setStatus('unavailable');setError('Could not reach the sign-in service. Please check your connection.');}}})();return()=>{active=false;};},[refresh]);
  useEffect(()=>{const ended=()=>{resetHttpSession();setInfo(null);setStatus('signed-out');};window.addEventListener('bindr:session-ended',ended);return()=>window.removeEventListener('bindr:session-ended',ended);},[]);
  async function complete(user:User){
    if(!user.emailVerified)throw new Error('Verify your email address before opening your workspace.');
    const nonce=await accountRequest<{csrf_token:string}>('/csrf');
    await accountRequest('/login',{id_token:await user.getIdToken(true)},'POST',{'X-CSRF-Token':nonce.csrf_token});resetHttpSession();await refresh();
  }
  async function logout(everywhere=false){await accountRequest(everywhere ? '/sign-out-everywhere' : '/logout',{});resetHttpSession();setInfo(null);setStatus('signed-out');if(config){try{const auth=await firebaseAuth(config);await (await import('@firebase/auth')).signOut(auth);}catch{/* Server session is already revoked; a missing SDK must not prevent logout. */}}}
  return {status,config,info,error,refresh,complete,logout};
}
const Context=createContext<ReturnType<typeof useAuthState>|null>(null);
export function AuthProvider({children}:{children:ReactNode}){return <Context.Provider value={useAuthState()}>{children}</Context.Provider>;}
export function useAuth(){const c=useContext(Context);if(!c)throw new Error('AuthProvider is required');return c;}
export function AccountGate(){const auth=useAuth(),location=useLocation();if(auth.status==='loading')return <main className="auth-loading" role="status">Opening your secure workspace…</main>;if(auth.status==='unavailable')return <main className="auth-loading"><h1>Let’s reconnect.</h1><p role="alert">{auth.error}</p><button className="button button-primary" onClick={()=>window.location.reload()}>Try again</button></main>;if(auth.status==='signed-out')return <Navigate to={`/login?returnTo=${encodeURIComponent(location.pathname+location.search)}`} replace/>;return <Outlet/>;}
