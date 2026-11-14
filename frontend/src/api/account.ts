import type { Auth } from '@firebase/auth';
export interface Account {id:string;email:string;display_name:string;provider_uid:string}
export interface AccountInfo {account:Account;csrf_token:string;mfa_enabled:boolean;legacy_case_count:number;expires_at:number}
export interface AuthConfig {provider:string;configured:boolean;firebase:{apiKey:string;authDomain:string;projectId:string;appId:string}|null}
const root=(import.meta.env.VITE_API_URL || '/api/v1').replace(/\/+$/,'');
export const apiBase=root.endsWith('/api/v1') ? root : `${root}/api/v1`;
export function accountCsrf(){const cookies=document.cookie.split(/;\s*/);return (cookies.find(s=>s.startsWith('__Host-bindr_csrf=')) ?? cookies.find(s=>s.startsWith('bindr_csrf=')))?.split('=').slice(1).join('=') ?? '';}
export async function accountRequest<T>(path:string,body?:object,method=body ? 'POST' : 'GET',extra:Record<string,string>={}):Promise<T> {
  const response=await fetch(`${apiBase}/auth${path}`,{method,credentials:'include',cache:'no-store',headers:{...(body ? {'Content-Type':'application/json','X-CSRF-Token':accountCsrf()} : {}),...extra},body:body ? JSON.stringify(body) : undefined});
  let data;try{data=await response.json();}catch{throw new Error('The server could not complete this request. Please try again.');}
  if(!response.ok)throw Object.assign(new Error(data?.error?.message || 'The request could not finish. Please try again.'),{code:data?.error?.code,status:response.status});
  return data as T;
}
let authReady:Promise<Auth>|null=null;
export async function firebaseAuth(config:AuthConfig):Promise<Auth>{
  if(!config.configured || !config.firebase)throw new Error('Account sign-in is not configured yet. Please try again later.');
  if(!authReady)authReady=(async()=>{const [{initializeApp,getApps},{getAuth,setPersistence,inMemoryPersistence}]=await Promise.all([import('@firebase/app'),import('@firebase/auth')]);const auth=getAuth(getApps().find(a=>a.name==='bindr') ?? initializeApp(config.firebase!,'bindr'));await setPersistence(auth,inMemoryPersistence);auth.languageCode='en';return auth;})().catch(cause=>{authReady=null;throw cause;});
  return authReady;
}
export function safeReturnTo(raw:string|null){return raw && /^\/app(?:[/?]|$)/.test(raw) && !raw.includes('\\') ? raw : '/app';}
export function authMessage(cause:unknown):string {
  const code=(cause as {code?:string})?.code;
  const messages:Record<string,string>={
    'auth/invalid-credential':'The email or password is incorrect. Please try again.',
    'auth/wrong-password':'The email or password is incorrect. Please try again.',
    'auth/user-not-found':'The email or password is incorrect. Please try again.',
    'auth/email-already-in-use':'We could not create this account. Try signing in or resetting your password.',
    'auth/weak-password':'Choose a stronger password with at least 12 characters.',
    'auth/password-does-not-meet-requirements':'Choose a password that meets the requirements below.',
    'auth/too-many-requests':'Too many attempts. Please wait a little before trying again.',
    'auth/popup-closed-by-user':'Google sign-in was closed. You can try again.',
    'auth/popup-blocked':'Allow the Google sign-in popup for Bindr, then try again.',
    'auth/account-exists-with-different-credential':'Sign in using the method you originally used for this email. You can connect Google in Settings.',
    'auth/invalid-verification-code':'That code is incorrect or expired. Enter the current code from your authenticator.',
    'auth/invalid-totp-code':'That code is incorrect or expired. Enter the current code from your authenticator.',
    'auth/code-expired':'This code has expired. Start again to receive a fresh one.',
    'auth/expired-action-code':'This link has expired. Request a new email and try again.',
    'auth/invalid-action-code':'This link is invalid or has already been used. Request a new email.',
    'auth/requires-recent-login':'Sign in again before changing your account security.',
    'auth/user-token-expired':'Your security settings changed. Sign in again to continue.',
    'auth/network-request-failed':'Could not reach the sign-in service. Check your connection and try again.',
    'auth/operation-not-allowed':'This sign-in method is not enabled yet. Please try again later.',
    'auth/unauthorized-domain':'Sign-in is not configured for this website address yet.',
  };
  return code && messages[code] ? messages[code] : code?.startsWith('auth/') ? 'Sign-in could not finish. Please try again.' : cause instanceof Error ? cause.message : 'Something went wrong. Please try again.';
}
