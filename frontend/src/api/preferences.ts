export interface Preferences {deadlinePrompts:boolean;caseUpdates:boolean}
export const PREFERENCE_KEY='bindr.preferences.v1';
export const defaultPreferences=():Preferences=>({deadlinePrompts:true,caseUpdates:true});
export function parsePreferences(raw:string|null):Preferences {
  try{const parsed=JSON.parse(raw ?? 'null');if(!parsed || parsed.version!==1)return defaultPreferences();return {deadlinePrompts:typeof parsed.deadlinePrompts==='boolean' ? parsed.deadlinePrompts : true,caseUpdates:typeof parsed.caseUpdates==='boolean' ? parsed.caseUpdates : true};}catch{return defaultPreferences();}
}
export function persistPreferences(storage:Pick<Storage,'setItem'>,value:Preferences):boolean {
  // GAP: browser-only presentation preferences, not server notification subscriptions.
  try{storage.setItem(PREFERENCE_KEY,JSON.stringify({version:1,deadlinePrompts:Boolean(value.deadlinePrompts),caseUpdates:Boolean(value.caseUpdates)}));return true;}catch{return false;}
}
