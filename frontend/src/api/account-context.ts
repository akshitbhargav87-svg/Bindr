// The tab's account is independent of cookies that other tabs can replace.
let currentId:string|null=null;
let generation=0;
export function accountContext(){return {id:currentId,generation};}
export function setAccountContext(id:string|null){if(currentId!==id){currentId=id;generation++;}}
export function accountHeaders():Record<string,string>{return currentId ? {'X-Bindr-Account':currentId} : {};}
export function sessionEnded(){setAccountContext(null);if(typeof window!=='undefined')window.dispatchEvent(new Event('bindr:session-ended'));}
export function assertAccountContext(prior:ReturnType<typeof accountContext>){if(prior.generation!==generation)throw new Error('The account changed while this request was running. Reopen the workspace.');}
