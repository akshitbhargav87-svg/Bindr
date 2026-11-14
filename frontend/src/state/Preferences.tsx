import { createContext,useContext,useState,type ReactNode } from 'react';
import { defaultPreferences,parsePreferences,persistPreferences,PREFERENCE_KEY,type Preferences } from '../api/preferences';
const Context=createContext<{preferences:Preferences;save:(value:Preferences)=>boolean;readIds:Set<string>;markRead:(ids:string[])=>void}|null>(null);
export function PreferencesProvider({children}:{children:ReactNode}) {
  const [preferences,setPreferences]=useState(()=>{try{return parsePreferences(localStorage.getItem(PREFERENCE_KEY));}catch{return defaultPreferences();}});
  const [readIds,setReadIds]=useState(new Set<string>());
  function save(value:Preferences){const clean={deadlinePrompts:Boolean(value.deadlinePrompts),caseUpdates:Boolean(value.caseUpdates)};setPreferences(clean);try{return persistPreferences(localStorage,clean);}catch{return false;}}
  function markRead(ids:string[]){setReadIds(previous=>new Set([...previous,...ids]));}
  return <Context.Provider value={{preferences,save,readIds,markRead}}>{children}</Context.Provider>;
}
export function usePreferences(){const context=useContext(Context);if(!context)throw new Error('PreferencesProvider is required');return context;}
