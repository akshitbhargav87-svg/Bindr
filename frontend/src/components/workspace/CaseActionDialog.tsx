import { useEffect, useId, useRef, useState, type FormEvent } from 'react';
import { Archive, Check, CircleAlert, LoaderCircle, Pencil, RotateCcw, Trash2, X } from 'lucide-react';
import { Button } from '../ui';
import '../../case-action-dialog.css';

type Action='edit'|'reopen'|'archive'|'restore'|'delete';
export interface CaseActionInput {note?:string;company?:string;title?:string;confirmation?:string}
interface Props {action:Action|null;caseId:string;company:string;title:string;busy:boolean;error:string|null;blocked?:boolean;onReload?:()=>void;onClose:()=>void;onSubmit:(data:CaseActionInput)=>void}
const labels={edit:'Edit case details',reopen:'Reopen this case',archive:'Archive this case',restore:'Restore this case',delete:'Delete this case'};
const icons={edit:Pencil,reopen:RotateCcw,archive:Archive,restore:RotateCcw,delete:Trash2};

export default function CaseActionDialog({action,caseId,company,title,busy,error,blocked=false,onReload,onClose,onSubmit}:Props) {
  const dialogRef=useRef<HTMLDialogElement>(null);
  const [values,setValues]=useState({company,title,note:'',confirmation:''});
  const [confirmed,setConfirmed]=useState(false);
  const [errors,setErrors]=useState<Record<string,string>>({});
  const id=useId();
  const activeAction=useRef<Action|null>(null);
  useEffect(()=>{
    const dialog=dialogRef.current;
    if(action) {
      if(activeAction.current!==action){setValues({company,title,note:'',confirmation:''});setConfirmed(false);setErrors({});activeAction.current=action;}
      if(dialog && !dialog.open)dialog.showModal();
    } else {if(dialog?.open)dialog.close();activeAction.current=null;setConfirmed(false);setErrors({});}
  },[action,company,title]);
  useEffect(()=>{if(error)setConfirmed(false);},[error]);
  const change=(patch:Partial<typeof values>)=>{setValues(previous=>({...previous,...patch}));setConfirmed(false);setErrors({});};
  function submit(event:FormEvent) {
    event.preventDefault();if(!action || busy || blocked)return;
    const next:Record<string,string>={};
    if(action==='edit') {
      if(!values.company.trim() || values.company.trim().length>200)next.company='Enter the company in 1–200 characters.';
      if(!values.title.trim() || values.title.trim().length>200)next.title='Enter a case title in 1–200 characters.';
    }
    if((action==='edit' || action==='reopen') && (!values.note.trim() || values.note.trim().length>2000))next.note='Add a reason in 1–2000 characters.';
    if(action==='delete' && values.confirmation!==caseId)next.confirmation='Type the complete case ID exactly as shown.';
    if(action!=='edit' && !confirmed)next.confirmed='Confirm this change before continuing.';
    setErrors(next);if(Object.keys(next).length)return;
    onSubmit({...(action==='edit' ? {company:values.company.trim(),title:values.title.trim()} : {}),...(['edit','reopen'].includes(action) ? {note:values.note.trim()} : {}),...(action==='delete' ? {confirmation:values.confirmation} : {})});
  }
  const Icon=action ? icons[action] : Pencil;
  return <dialog ref={dialogRef} className="case-action-dialog" aria-labelledby={`${id}-heading`} onCancel={event=>{event.preventDefault();if(!busy)onClose();}} onClose={()=>{if(action && !busy)onClose();}}>
    <form onSubmit={submit} noValidate aria-busy={busy}>
      <header className="case-action-header"><div><Icon size={22}/><h2 id={`${id}-heading`}>{action ? labels[action] : 'Case details'}</h2></div><button className="case-action-close" type="button" onClick={onClose} disabled={busy} aria-label="Close case action"><X size={21}/></button></header>
      <div className="case-action-body">
        {action==='edit' && <p className="case-action-description">Update the company or case title. Confirmed promises, deadlines and original evidence stay on record.</p>}
        {action==='reopen' && <p className="case-action-description">The earlier resolution stays in the timeline. Reopening makes the full promise outstanding again; the original deadline still applies.</p>}
        {action==='archive' && <p className="case-action-description">Move this case out of your active workspace. Its promises and evidence are kept, and you can restore it later.</p>}
        {action==='restore' && <p className="case-action-description">Return this case to your workspace with its history and evidence intact. Its existing deadline and outcome still apply.</p>}
        {action==='delete' && <div className="case-action-danger-note"><Trash2 size={21}/><p>Remove this case and its attached files from this workspace. This cannot be undone in this session.</p></div>}
        <fieldset disabled={busy} className="case-action-fields">
          {action==='edit' && <><label className="case-action-label" htmlFor={`${id}-company`}>Company<input id={`${id}-company`} value={values.company} maxLength={200} onChange={event=>change({company:event.target.value})} aria-invalid={Boolean(errors.company)} aria-describedby={errors.company ? `${id}-company-error` : undefined}/>{errors.company && <span id={`${id}-company-error`} className="case-action-error" role="alert">{errors.company}</span>}</label><label className="case-action-label" htmlFor={`${id}-title`}>Case title<input id={`${id}-title`} value={values.title} maxLength={200} onChange={event=>change({title:event.target.value})} aria-invalid={Boolean(errors.title)} aria-describedby={errors.title ? `${id}-title-error` : undefined}/>{errors.title && <span id={`${id}-title-error`} className="case-action-error" role="alert">{errors.title}</span>}</label></>}
          {(action==='edit' || action==='reopen') && <label className="case-action-label" htmlFor={`${id}-reason`}>{action==='reopen' ? 'Why are you reopening it?' : 'Reason for this correction'}<textarea id={`${id}-reason`} rows={3} maxLength={2000} placeholder={action==='reopen' ? 'What is still unresolved?' : 'What needed correcting?'} value={values.note} onChange={event=>change({note:event.target.value})} aria-invalid={Boolean(errors.note)} aria-describedby={errors.note ? `${id}-note-error` : undefined}/>{errors.note && <span id={`${id}-note-error`} className="case-action-error" role="alert">{errors.note}</span>}</label>}
          {action==='delete' && <label className="case-action-label" htmlFor={`${id}-confirmation`}>Type this case ID to confirm<code className="case-action-id">{caseId}</code><input id={`${id}-confirmation`} autoComplete="off" autoCapitalize="none" spellCheck={false} placeholder="Complete case ID" value={values.confirmation} onChange={event=>change({confirmation:event.target.value})} aria-invalid={Boolean(errors.confirmation)} aria-describedby={errors.confirmation ? `${id}-confirmation-error` : undefined}/>{errors.confirmation && <span id={`${id}-confirmation-error`} className="case-action-error" role="alert">{errors.confirmation}</span>}</label>}
          {action && action!=='edit' && <label className="case-action-confirm"><input type="checkbox" checked={confirmed} onChange={event=>{setConfirmed(event.target.checked);setErrors(previous=>({...previous,confirmed:''}));}} aria-describedby={errors.confirmed ? `${id}-confirm-error` : undefined}/><span>{action==='delete' ? 'I understand this removes the case and its attached files from this workspace.' : action==='reopen' ? 'I understand the full promise becomes outstanding again and the earlier resolution is preserved.' : action==='archive' ? 'Archive this case and keep its history and evidence.' : 'Restore this case with its existing history and outcome.'}</span></label>}
          {errors.confirmed && <p id={`${id}-confirm-error`} className="case-action-error" role="alert">{errors.confirmed}</p>}
        </fieldset>
        {(error || blocked) && <div className="case-action-save-error" role="alert"><CircleAlert size={19}/><div><strong>Your entered values are still here.</strong><p>{error || 'Check the latest case state before saving again.'}</p>{blocked && onReload && <Button type="button" variant="secondary" disabled={busy} onClick={onReload}>Check latest case state</Button>}</div></div>}
      </div>
      <footer className="case-action-footer"><Button type="button" variant="secondary" disabled={busy} onClick={onClose}>Cancel</Button><Button type="submit" className={action==='delete' ? 'case-delete-button' : ''} disabled={busy || blocked || action!=='edit' && !confirmed}>{busy ? <LoaderCircle size={18} className="spin"/> : action==='delete' ? <Trash2 size={18}/> : <Check size={18}/>} {busy ? 'Saving change…' : action==='edit' ? 'Save correction' : action==='reopen' ? 'Reopen case' : action==='archive' ? 'Archive case' : action==='restore' ? 'Restore case' : 'Delete case'}</Button></footer>
    </form>
  </dialog>;
}
