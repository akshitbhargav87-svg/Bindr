import {useEffect,useRef,useState} from 'react';
import {Button} from '../ui';
import {sourceDiff,reviewedAmount,formatAuthoritativeMoney} from '../../api/workflow';
import {validDay} from '../../api/capture-validation';
import {validateTerms,type Proposal,type V2Terms,type ReviewDecision,type ReviewDraft} from '../../api/v2';

interface Props {proposal:Proposal;previous?:Record<string,V2Terms>;busy:boolean;onConfirm:(items:ReviewDecision[])=>Promise<void>;onSource?:(id:string,quote:string)=>void;initialDraft?:ReviewDraft;onDraftChange?:(draft:ReviewDraft)=>void}
export default function ProposalReview({proposal,previous={},busy,onConfirm,onSource,initialDraft,onDraftChange}:Props){
  const [selected,setSelected]=useState<Record<string,boolean>>(initialDraft?.selected ?? {});
  const [edits,setEdits]=useState<Record<string,V2Terms>>(initialDraft?.edits ?? {});
  const [amounts,setAmounts]=useState<Record<string,string>>(initialDraft?.amounts ?? {});
  const [predecessors,setPredecessors]=useState<Record<string,string>>(initialDraft?.predecessors ?? {});
  const [dates,setDates]=useState<Record<string,string>>(initialDraft?.dates ?? {});
  const [reasons,setReasons]=useState<Record<string,string>>(initialDraft?.reasons ?? {});
  const draftWriter=useRef(onDraftChange);draftWriter.current=onDraftChange;
  useEffect(()=>draftWriter.current?.({selected,edits,amounts,predecessors,dates,reasons}),[selected,edits,amounts,predecessors,dates,reasons]);
  const [reviewed,setReviewed]=useState(false),[error,setError]=useState(''),[saving,setSaving]=useState(false);
  const guard=useRef(false);
  function edit(id:string,value:Partial<V2Terms>){const original=proposal.candidates.find(c=>c.candidate_id===id)!.terms;setEdits({...edits,[id]:{...(edits[id] ?? original),...value}});setReviewed(false);}
  async function confirm(){
    if(guard.current || busy)return;guard.current=true;
    try{
      if(!reviewed || !proposal.candidates.some(c=>selected[c.candidate_id]))throw new Error('Select and review the proposals to confirm.');
      const items:ReviewDecision[]=proposal.candidates.map(c=>{
        const id=c.candidate_id,terms={...(edits[id] ?? c.terms)};
        if(!selected[id])return {candidate_id:id,selected:false,terms:c.terms,predecessor_ids:[]};
        if(terms.currency!==c.terms.currency && amounts[id]===undefined)throw new Error('Enter the reviewed amount when correcting its currency.');
        if(amounts[id]!==undefined){terms.amount_minor=reviewedAmount(amounts[id],terms.currency ?? 'INR');if(terms.amount_minor===null)terms.currency=null;}
        const predecessor=predecessors[id] ?? c.relation.predecessor_id;
        const decision:ReviewDecision={candidate_id:id,selected:selected[id] ?? false,terms,predecessor_ids:predecessor ? [predecessor] : []};
        if(c.relation.kind==='cancellation' || c.relation.kind==='corroboration'){
          if(!predecessor)throw new Error('Select the active predecessor for this cancellation or corroboration.');
          decision.action=c.relation.kind==='cancellation' ? 'cancel' : 'corroborate';
        }
        if(dates[id]){if(!validDay(dates[id]) || !reasons[id]?.trim())throw new Error('Review the date override and explain why it matches the source.');decision.deadline_override={date:dates[id],timezone:'Asia/Kolkata',precision:'date'};decision.reason=reasons[id];terms.due_at=null;}
        if(decision.selected)validateTerms(terms);return decision;
      });
      setSaving(true);await onConfirm(items);
    }catch(e){setError(e instanceof Error ? e.message : 'Review could not be saved.');}finally{guard.current=false;setSaving(false);}
  }
  return <section className="workflow-section"><h2>Review each proposed obligation</h2><p>Nothing is tracked until you confirm. Unselected proposals remain outside confirmed totals.</p>{proposal.document_warnings.map((w,i)=><p role="status" key={i}>{w}</p>)}
    {proposal.candidates.map(c=>{const id=c.candidate_id,terms=edits[id] ?? c.terms,predecessor=predecessors[id] ?? c.relation.predecessor_id;return <article className="workflow-obligation" key={id}>
      <label><input type="checkbox" checked={selected[id] ?? false} onChange={e=>{setSelected({...selected,[id]:e.target.checked});setReviewed(false);}}/> Track this proposal</label>
      <label className="capture-label">Promise<textarea value={terms.description} maxLength={2000} onChange={e=>edit(id,{description:e.target.value})}/></label>
      <label>Kind<select value={terms.kind} onChange={e=>edit(id,{kind:e.target.value as V2Terms['kind']})}><option value="refund">Refund</option><option value="replacement">Replacement</option><option value="service">Service</option><option value="other">Other</option></select></label>
      <p>Proposed amount: {terms.amount_minor!==null && terms.currency ? formatAuthoritativeMoney({amount_minor:terms.amount_minor,currency:terms.currency}) : 'Non-monetary or unknown'}</p>
      <label>Edited amount (leave unchanged unless correcting)<input inputMode="decimal" value={amounts[id] ?? ''} onChange={e=>{setAmounts({...amounts,[id]:e.target.value});setReviewed(false);}}/></label>
      <label>Currency<input maxLength={3} value={terms.currency ?? ''} onChange={e=>edit(id,{currency:e.target.value.toUpperCase() || null})}/></label>
      <p>{c.relation.kind}: {c.relation.explanation}</p>
      {Object.keys(previous).length>0 && <label>Compare with an earlier obligation<select value={predecessor ?? ''} onChange={e=>{setPredecessors({...predecessors,[id]:e.target.value});setReviewed(false);}}><option value="">Keep as a separate promise</option>{Object.entries(previous).map(([key,t])=><option key={key} value={key}>{t.description}</option>)}</select></label>}
      <dl>{sourceDiff(c,predecessor ? previous[predecessor] : undefined).map(d=><div key={d.label}><dt>{d.label}</dt><dd>{String(d.before ?? 'Unknown')} → {String(d.after ?? 'Unknown')}</dd></div>)}</dl>
      {c.condition.trigger && <p role="status">Condition: {c.condition.trigger} · {c.condition.status}. A fixed date needs confirmation of the trigger.</p>}
      <p>Date wording: {c.temporal.wording ?? 'No date'} · {c.temporal.parse_status}</p><p>Communication anchor: {c.temporal.anchor ?? 'Unknown'}</p>
      <label>Confirmed date override (Asia/Kolkata)<input type="date" value={dates[id] ?? ''} onChange={e=>{setDates({...dates,[id]:e.target.value});setReviewed(false);}}/></label>
      {dates[id] && <label>Why this date?<input maxLength={1000} value={reasons[id] ?? ''} onChange={e=>{setReasons({...reasons,[id]:e.target.value});setReviewed(false);}}/></label>}
      {c.warnings.map((w,i)=><p role="status" key={i}>{w}</p>)}{c.sources.map((s,i)=><blockquote key={i}><p>{s.quote}</p><cite>{s.evidence_id}{s.page ? ` · page ${s.page}` : ''}{s.message_id ? ` · message ${s.message_id}` : ''}{s.start_ms!=null ? ` · ${s.start_ms/1000}–${(s.end_ms ?? s.start_ms)/1000}s` : ''}</cite>{onSource && <Button variant="text" onClick={()=>onSource(s.evidence_id,s.quote)}>View original source</Button>}</blockquote>)}
    </article>;})}
    <label><input type="checkbox" checked={reviewed} onChange={e=>setReviewed(e.target.checked)}/> I reviewed the selected terms, dates and original sources.</label>{error && <p role="alert">{error}</p>}<Button disabled={busy || saving || !reviewed} onClick={()=>void confirm()}>Confirm selected proposals</Button>
  </section>;
}
