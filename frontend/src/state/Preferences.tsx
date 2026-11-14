import { createContext,useContext,useEffect,useRef,useState,type ReactNode } from 'react';
import { defaultPreferences,parsePreferences,persistPreferences,PREFERENCE_KEY,type Preferences } from '../api/preferences';
import { accountRequest } from '../api/account';
import { useAuth } from './Auth';
const Context=createContext<{preferences:Preferences;save:(value:Preferences)=>Promise<boolean>;readIds:Set<string>;markRead:(ids:string[])=>void;error:string|null;ready:boolean}|null>(null);
export function PreferencesProvider({children}:{children:ReactNode}) {
  const auth=useAuth(),cloud=auth.status==='signed-in';
  const [preferences,setPreferences]=useState(()=>{if(cloud)return defaultPreferences();try{return parsePreferences(localStorage.getItem(PREFERENCE_KEY));}catch{return defaultPreferences();}}),[readIds,setReadIds]=useState(new Set<string>()),[error,setError]=useState<string|null>(null),[ready,setReady]=useState(!cloud);
  const version=useRef(0),writing=useRef(false),readRef=useRef(readIds);readRef.current=readIds;
  useEffect(()=>{if(!cloud)return;let active=true;accountRequest<{version:number;preferences:{deadline_prompts:boolean;case_updates:boolean;read_ids:string[]}}>('/preferences').then(data=>{if(active){version.current=data.version;setPreferences({deadlinePrompts:data.preferences.deadline_prompts,caseUpdates:data.preferences.case_updates});setReadIds(new Set(data.preferences.read_ids));setReady(true);}}).catch(()=>{if(active)setError('Cloud preferences could not be loaded. Reload before changing them.');});return()=>{active=false;};},[cloud]);
  async function persist(value:Preferences,ids:Set<string>){if(writing.current)throw new Error('Please wait for the current save to finish.');if(!ready)throw new Error('Reload to load your cloud preferences first.');writing.current=true;try{const result=await accountRequest<{version:number}>('/preferences',{expected_version:version.current,deadline_prompts:value.deadlinePrompts,case_updates:value.caseUpdates,read_ids:[...ids].slice(-2000)},'PUT');version.current=result.version;}finally{writing.current=false;}}
  async function save(value:Preferences){const clean={deadlinePrompts:Boolean(value.deadlinePrompts),caseUpdates:Boolean(value.caseUpdates)};if(cloud){try{await persist(clean,readRef.current);setPreferences(clean);setError(null);return true;}catch(cause){setError(cause instanceof Error ? cause.message : 'Cloud preferences could not be saved.');return false;}}setPreferences(clean);try{return persistPreferences(localStorage,clean);}catch{return false;}}
  function markRead(ids:string[]){const next=new Set([...readRef.current,...ids]);if(cloud){void persist(preferences,next).then(()=>{setReadIds(next);setError(null);}).catch(cause=>setError(cause instanceof Error ? cause.message : 'Read markers could not be saved.'));}else setReadIds(next);}
  return <Context.Provider value={{preferences,save,readIds,markRead,error,ready}}>{children}</Context.Provider>;
}
export function usePreferences(){const context=useContext(Context);if(!context)throw new Error('PreferencesProvider is required');return context;}
