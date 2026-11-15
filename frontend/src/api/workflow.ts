import {V2Client,operation,validateTerms,snapshot,type Operation,type CaseSnapshot,type ProposalCandidate,type V2Terms,type ReviewDecision} from './v2';

/** Operation objects are owned by the form, retained after uncertain transport errors. */
export class Workflow<T=CaseSnapshot> {
  constructor(readonly client=new V2Client(),private mutationDecode:(value:unknown)=>T=snapshot as unknown as (value:unknown)=>T){}
  review(id:string,body:{expected_version:number;proposal_id:string;decisions:ReviewDecision[]},op:Operation){
    if(!body.decisions.some(d=>d.selected))throw new Error('Select at least one proposal for review.');
    body.decisions.filter(d=>d.selected).forEach(d=>validateTerms(d.terms));
    return this.client.mutate(`/cases/${encodeURIComponent(id)}/reviews`,body,op,this.mutationDecode);
  }
  outcome(id:string,body:{expected_version:number;kind:'partial'|'full'|'pending'|'company_claim'|'correction';allocations:{obligation_id:string;amount_minor:number|null;currency:string|null}[];received_at:string|null;note:string;source_ids:string[]},op:Operation){
    if(!body.note.trim())throw new Error('Add a note describing the outcome.');
    if(body.kind==='pending' || body.kind==='company_claim'){if(body.allocations.some(a=>a.amount_minor!==null))throw new Error('Waiting and company claims cannot record received money.');}
    for(const a of body.allocations)if(a.amount_minor!==null && (!Number.isSafeInteger(a.amount_minor) || a.amount_minor<=0 || !a.currency || !/^[A-Z]{3}$/.test(a.currency)))throw new Error('Review the receipt allocation.');
    return this.client.mutate(`/cases/${encodeURIComponent(id)}/outcomes`,body,op,this.mutationDecode);
  }
}
export function reviewedAmount(value:string,currency:string):number|null {
  if(!value.trim())return null;
  if(!/^[A-Z]{3}$/.test(currency))throw new Error('Review the ISO currency.');
  const digits=new Intl.NumberFormat('en',{style:'currency',currency}).resolvedOptions().maximumFractionDigits ?? 2;
  if(!new RegExp(`^\\d+(?:\\.\\d{1,${Math.max(1,digits)}})?$`).test(value) || (digits===0 && value.includes('.')))throw new Error(`This currency uses ${digits} decimal places.`);
  const [whole,fraction='']=value.split('.');const amount=BigInt(whole)*10n**BigInt(digits)+BigInt(fraction.padEnd(digits,'0') || '0');
  if(amount>BigInt(Number.MAX_SAFE_INTEGER))throw new Error('This amount is too large.');return Number(amount);
}

export function sourceDiff(candidate:ProposalCandidate,previous?:V2Terms){return [
  {label:'Description',before:previous?.description ?? 'No predecessor selected',after:candidate.terms.description},
  {label:'Amount',before:previous?.amount_minor!=null && previous.currency ? formatAuthoritativeMoney({amount_minor:previous.amount_minor,currency:previous.currency}) : 'Unknown or non-monetary',after:candidate.terms.amount_minor!==null && candidate.terms.currency ? formatAuthoritativeMoney({amount_minor:candidate.terms.amount_minor,currency:candidate.terms.currency}) : 'Unknown or non-monetary'},
  {label:'Currency',before:previous?.currency ?? null,after:candidate.terms.currency},
  {label:'Date',before:previous?.due_at ?? null,after:candidate.terms.due_at ?? candidate.temporal.wording ?? 'Unknown'},
];}
export function formatAuthoritativeMoney(m:{amount_minor:number;currency:string}) {
  // The contract expresses minor units; use the ISO currency's actual exponent.
  const fmt=new Intl.NumberFormat('en-IN',{style:'currency',currency:m.currency});
  const digits=fmt.resolvedOptions().maximumFractionDigits ?? 2;
  return fmt.format(m.amount_minor/(10**digits));
}
export function caseHealth(snapshot:CaseSnapshot){return {status:snapshot.projection.status,asOf:snapshot.projection.as_of,timezone:snapshot.projection.timezone};}
export function reviewedDraft(note:string,company:string){return {subject:'Please confirm our conversation in writing',body:`Hello ${company},\n\nMy note of our conversation is:\n${note}\n\nPlease confirm or correct the terms, amount and expected date in writing.\nThank you.`,sent:false};}
export interface Aggregate {eligible:number;fulfilled:number;minimum_sample:number;period:string;method:string;currency_totals:{currency:string;amount_minor:number}[];privacy_reviewed:boolean}
export function aggregateDisplay(a:Aggregate){
  if(!a.privacy_reviewed || !Number.isSafeInteger(a.eligible) || !Number.isSafeInteger(a.fulfilled) || !Number.isSafeInteger(a.minimum_sample) || a.minimum_sample<1 || a.eligible<a.minimum_sample || a.fulfilled<0 || a.fulfilled>a.eligible)return {suppressed:true,label:'Insufficient reviewed sample',rate:null};
  return {suppressed:false,label:`${a.fulfilled} of ${a.eligible} participating cases · ${a.period} · ${a.method}`,rate:a.fulfilled/a.eligible};
}
export function preserveOperation(previous:Operation|undefined,body:unknown){if(!previous || previous.payload!==JSON.stringify(body))return operation(body);return previous;}

/** Local verification does not upload originals and makes no authorship/legal claim. */
export async function verifyManifest(files:File[],manifest:{files:{name:string;sha256:string;size:number}[]}) {
  if(!Array.isArray(manifest.files) || manifest.files.length>1000)throw new Error('Invalid manifest.');
  const entries=new Set<string>();
  for(const entry of manifest.files){if(!entry.name || entries.has(entry.name) || !/^[a-f0-9]{64}$/.test(entry.sha256) || !Number.isSafeInteger(entry.size) || entry.size<0)throw new Error('Invalid manifest entry.');entries.add(entry.name);}
  if(files.reduce((n,f)=>n+f.size,0)>512*1024*1024 || files.some(f=>f.size>100*1024*1024))throw new Error('Local verification supports up to 512 MiB total and 100 MiB per original.');
  const results:{name:string;verified:boolean}[]=[];
  for(const entry of manifest.files){
    const matching=files.filter(f=>{const path=f.webkitRelativePath || f.name;return path===entry.name || Boolean(f.webkitRelativePath && path.split('/').slice(1).join('/')===entry.name);});
    if(matching.length!==1 || matching[0].size!==entry.size){results.push({name:entry.name,verified:false});continue;}
    const digest=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',await matching[0].arrayBuffer()))).map(v=>v.toString(16).padStart(2,'0')).join('');
    results.push({name:entry.name,verified:digest===entry.sha256});
  }
  return results;
}
