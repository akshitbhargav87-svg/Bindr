import { useEffect, useId, useRef, useState, type FormEvent } from 'react';
import { Check, CheckCircle2, CircleAlert, Clock3, LoaderCircle, PieChart, X } from 'lucide-react';
import { Button } from '../ui';
import { money } from '../../lib/format';
import '../../outcome-dialog.css';

export interface OutcomeInput {kind:'full'|'partial'|'pending';note:string;amount:string}
interface Props {
  open:boolean; monetary:boolean; outstandingMinor:number|null; allowExtended:boolean;
  busy:boolean; error:string|null; blocked?:boolean; onReload?:()=>void; onClose:()=>void; onSubmit:(input:OutcomeInput)=>void;
}

export default function OutcomeDialog({open,monetary,outstandingMinor,allowExtended,busy,error,blocked=false,onReload,onClose,onSubmit}:Props) {
  const dialogRef=useRef<HTMLDialogElement>(null);
  const [input,setInput]=useState<OutcomeInput>({kind:'full',note:'',amount:''});
  const [confirmed,setConfirmed]=useState(false);
  const [errors,setErrors]=useState<Record<string,string>>({});
  const baseId=useId();
  const partialAvailable=allowExtended && (!monetary || outstandingMinor!==null && outstandingMinor>0);

  useEffect(()=>{
    const dialog=dialogRef.current;
    if(open) {if(dialog && !dialog.open)dialog.showModal();}
    else {
      if(dialog?.open)dialog.close();
      setInput({kind:'full',note:'',amount:''});setConfirmed(false);setErrors({});
    }
  },[open]);
  useEffect(()=>{if(error)setConfirmed(false);},[error]);

  function update(values:Partial<OutcomeInput>) {setInput(previous=>({...previous,...values}));setConfirmed(false);setErrors({});}
  function submit(event:FormEvent) {
    event.preventDefault();if(busy || blocked)return;
    const next:Record<string,string>={};
    if(!input.note.trim() || input.note.trim().length>2000)next.note='Add a note in 1–2000 characters.';
    if(input.kind==='partial') {
      if(!partialAvailable)next.amount='A partial receipt is not available for this case.';
      else if(monetary) {
        const parts=input.amount.trim().match(/^(\d+)(?:\.(\d{1,2}))?$/);
        const minor=parts ? Number(parts[1])*100+Number((parts[2] ?? '').padEnd(2,'0')) : NaN;
        if(!Number.isSafeInteger(minor) || minor<=0)next.amount='Enter a positive INR amount with up to two decimals.';
        else if(minor>=outstandingMinor!)next.amount=`Enter less than the outstanding ${money(outstandingMinor)}, or choose Received in full.`;
      }
    }
    if(input.kind==='pending' && !allowExtended)next.selection='Pending notes are not available on the connected backend.';
    if(!confirmed)next.confirmed=input.kind==='pending' ? 'Confirm that this records a note only.' : 'Confirm that you actually received this outcome.';
    setErrors(next);
    if(Object.keys(next).length)return;
    onSubmit({...input,note:input.note.trim(),amount:input.amount.trim()});
  }

  const choices=[
    {kind:'full' as const,Icon:CheckCircle2,title:'Received in full',description:monetary ? 'I received all of the remaining amount.' : 'The company fulfilled what it promised.',disabled:false},
    {kind:'partial' as const,Icon:PieChart,title:'Received part of it',description:monetary ? 'Record the amount received. Keep the rest open.' : 'Describe what was fulfilled and what remains.',disabled:!partialAvailable},
    {kind:'pending' as const,Icon:Clock3,title:'Still waiting',description:'Add a note without closing the case.',disabled:!allowExtended},
  ];
  return <dialog ref={dialogRef} className="outcome-dialog" aria-labelledby={`${baseId}-title`} aria-describedby={`${baseId}-intro`} onCancel={event=>{event.preventDefault();if(!busy)onClose();}} onClose={()=>{if(open && !busy)onClose();}}>
    <form onSubmit={submit} noValidate aria-busy={busy}>
      <header className="outcome-dialog-header"><div><span className="outcome-dialog-kicker">Your confirmation</span><h2 id={`${baseId}-title`}>What came through?</h2></div><button type="button" className="outcome-close" aria-label="Close record outcome" disabled={busy} onClick={onClose}><X size={21}/></button></header>
      <div className="outcome-dialog-body">
        <p id={`${baseId}-intro`} className="outcome-intro">Record what you actually received. A company saying it sent something doesn’t confirm receipt.</p>
        {monetary && outstandingMinor!==null && <div className="outcome-outstanding"><span>Still awaiting</span><strong>{money(outstandingMinor)}</strong></div>}
        <fieldset className="outcome-choices" disabled={busy}><legend className="sr-only">Choose the outcome</legend>{choices.map(({kind,Icon,title,description,disabled})=><label key={kind} className={`outcome-choice ${input.kind===kind ? 'is-selected' : ''} ${disabled ? 'is-unavailable' : ''}`}>
          <input type="radio" name={`${baseId}-outcome`} value={kind} checked={input.kind===kind} disabled={disabled} onChange={()=>update({kind})}/><Icon size={21}/><span><strong>{title}</strong><span>{description}</span></span>
        </label>)}</fieldset>
        {!allowExtended && <p className="outcome-help">The connected backend supports full receipt only. Partial receipts and pending notes need backend support.</p>}
        {allowExtended && !monetary && <p className="outcome-help">For a partial outcome, explain what you received and what you’re still waiting for.</p>}
        {errors.selection && <p className="outcome-field-error" role="alert">{errors.selection}</p>}
        <fieldset className="outcome-fields" disabled={busy}>
          {input.kind==='partial' && monetary && <label className="outcome-label" htmlFor={`${baseId}-amount`}>Amount received (INR)<input id={`${baseId}-amount`} autoComplete="off" inputMode="decimal" type="text" value={input.amount} placeholder="e.g. 1500" aria-invalid={Boolean(errors.amount)} aria-describedby={errors.amount ? `${baseId}-amount-error` : `${baseId}-amount-help`} onChange={event=>update({amount:event.target.value})}/>{errors.amount ? <span id={`${baseId}-amount-error`} className="outcome-field-error" role="alert">{errors.amount}</span> : <span id={`${baseId}-amount-help`} className="outcome-help">The original total and deadline stay on record.</span>}</label>}
          <label className="outcome-label" htmlFor={`${baseId}-note`}>{input.kind==='pending' ? 'What’s the latest?' : input.kind==='partial' && !monetary ? 'What was fulfilled, and what remains?' : 'Add a receipt note'}<textarea id={`${baseId}-note`} rows={3} maxLength={2000} value={input.note} placeholder={input.kind==='pending' ? 'What are you still waiting for?' : input.kind==='partial' && !monetary ? 'Describe what arrived and what is still missing.' : 'What did you receive, and when?'} aria-invalid={Boolean(errors.note)} aria-describedby={errors.note ? `${baseId}-note-error` : undefined} onChange={event=>update({note:event.target.value})}/>{errors.note && <span id={`${baseId}-note-error`} className="outcome-field-error" role="alert">{errors.note}</span>}</label>
          <label className="outcome-confirm"><input type="checkbox" checked={confirmed} onChange={event=>{setConfirmed(event.target.checked);setErrors(previous=>({...previous,confirmed:''}));}} aria-describedby={errors.confirmed ? `${baseId}-confirm-error` : undefined}/><span>{input.kind==='pending' ? 'I understand this records a note and keeps the case open.' : input.kind==='partial' ? monetary ? 'I confirm I actually received this amount.' : 'I confirm the partial fulfilment described above.' : 'I confirm every active promise in this case has been fulfilled.'}</span></label>
          {errors.confirmed && <p id={`${baseId}-confirm-error`} className="outcome-field-error" role="alert">{errors.confirmed}</p>}
        </fieldset>
        {(error || blocked) && <div className="outcome-save-error" role="alert"><CircleAlert size={19}/><div><strong>Your entered values are still here.</strong><p>{error || 'Check the latest case state before saving again.'}</p>{blocked && onReload && <Button type="button" variant="secondary" disabled={busy} onClick={onReload}>Check latest case state</Button>}</div></div>}
      </div>
      <footer className="outcome-dialog-footer"><Button variant="secondary" type="button" disabled={busy} onClick={onClose}>Cancel</Button><Button type="submit" disabled={busy || blocked || !confirmed}>{busy ? <LoaderCircle size={18} className="spin"/> : <Check size={18}/>} {busy ? 'Saving outcome…' : input.kind==='full' ? 'Confirm full receipt' : input.kind==='partial' ? 'Record partial receipt' : 'Save pending note'}</Button></footer>
    </form>
  </dialog>;
}
