import { useRef, useState, type FormEvent } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { ArrowLeft, ArrowRight, Check, CheckCircle2, CircleAlert, CloudUpload, FileCheck2, FileText, Link2, LoaderCircle, Plus, RefreshCw, X } from 'lucide-react';
import { Button } from '../components/ui';
import { PageHeading } from '../components/workspace/WorkspaceStates';
import CaptureSource from '../components/workspace/CaptureSource';
import { useWorkspace } from '../state/Workspace';
import { newCapture, useCapture } from '../state/Capture';
import type { CaptureInput, CaptureJob, CaptureSource as Source, ReviewFields, Scenario } from '../api/capture-model';
import { captureError, captureSample, confirmCapture, deadlineSummary, manualFields, prepareCapture, reconcileCapture, retainEvidence, reviewFields, sampleOptions, supportingFragment, validateFile } from '../api/capture';
import { termsFromFields, validDay } from '../api/capture-validation';
import { ApiError } from '../api/types';

export default function Capture() {
  const {session:s,setSession,reset}=useCapture();const w=useWorkspace();const navigate=useNavigate();
  const inputRef=useRef<HTMLInputElement>(null);const replaceKey=useRef<string|null>(null);const inFlight=useRef(false);
  const [mobileTab,setMobileTab]=useState<'fields'|'source'>('fields');const [sourceIndex,setSourceIndex]=useState(0);const [dragging,setDragging]=useState(false);
  const patch=(values:Partial<typeof s>)=>setSession(previous=>({...previous,...values}));
  const updateJob=(job:CaptureJob,progress:string)=>setSession(previous=>({...previous,job,progress}));
  const uploads=s.sources.filter(source=>!source.key.startsWith('paste:'));
  const reviewSources=s.sources.filter(source=>s.job?.uploadedKeys.includes(source.key));

  function receiveFiles(files:FileList|File[]|null) {
    if(!files || s.pending) return;
    const incoming=Array.from(files).map(file=>({key:crypto.randomUUID(),file,communicationDate:'',error:validateFile(file,w.isMock)}));
    const prior=s.sources;
    if(replaceKey.current) {
      const replacement=incoming[0];if(replacement){const old=prior.find(source=>source.key===replaceKey.current);replacement.communicationDate=old?.communicationDate ?? '';patch({sources:prior.map(source=>source.key===replaceKey.current ? replacement : source),error:null});}replaceKey.current=null;
    } else {
      const room=10-uploads.length;
      patch({sources:[...prior,...incoming.slice(0,Math.max(0,room))],error:incoming.length>room ? 'Choose at most 10 files per capture. Extra files were not added.' : null});
    }
    if(inputRef.current)inputRef.current.value='';
  }
  function useSample(scenario:Scenario) {
    const sample=captureSample(scenario);
    setSession({...newCapture(),...sample,scenario,tab:'paste'});setMobileTab('fields');
  }
  async function buildInput():Promise<CaptureInput> {
    const errors:Record<string,string>={};
    if(!s.company.trim())errors.company='Enter the company that made the promise.';
    if(s.company.trim().length>200)errors.company='Use at most 200 characters.';
    if(s.communicationDate && !validDay(s.communicationDate))errors.communicationDate='Choose a valid communication date.';
    let sources=uploads;
    if(s.tab==='paste') {
      if(!s.text.trim())errors.text='Paste the original company message.';
      if(s.text.length>50000)errors.text='Use at most 50,000 characters.';
      let source:Source|undefined;
      for(const item of s.sources.filter(i=>i.key.startsWith('paste:')))if(await item.file.text()===s.text){source={...item,communicationDate:s.communicationDate};break;}
      source ??= {key:`paste:${crypto.randomUUID()}`,file:new File([s.text],'company-message.txt',{type:'text/plain'}),communicationDate:s.communicationDate,error:null};
      sources=[source];patch({sources:[...uploads,source]});
    } else {
      if(!uploads.length)errors.sources='Choose a source file, or switch to Paste a message.';
      if(uploads.some(source=>source.error))errors.sources='Replace or remove the files that need attention.';
      if(uploads.some(source=>source.communicationDate && !validDay(source.communicationDate)))errors.sources='Review the communication dates.';
    }
    patch({formErrors:errors});
    if(Object.keys(errors).length)throw new Error('Review the marked fields before continuing.');
    return {company:s.company,title:s.title.trim() || `Promise from ${s.company.trim()}`.slice(0,200),sources};
  }
  async function analyze(manual=false) {
    if(s.pending || w.offline || inFlight.current)return;
    inFlight.current=true;patch({pending:true});
    try {
      const input=await buildInput();patch({pending:true,step:'processing',error:null,confirmed:false,progress:'Preparing your evidence'});
      const job=await prepareCapture(input,s.job,updateJob,w.isMock && s.scenario==='ai-error' && !manual,manual);
      patch({job,step:'review',pending:false,manual,fields:manual ? manualFields() : reviewFields(job.candidates),error:null,allowDuplicate:false});navigate('/app/review');
    } catch(cause) {patch({pending:false,step:'capture',error:captureError(cause),scenario:s.scenario==='ai-error' ? 'standard' : s.scenario});}finally{inFlight.current=false;}
  }
  function enterManual() {
    if(s.step==='review' && s.job?.caseId && s.job.evidenceIds.length && s.job.state==='ready') {patch({step:'review',fields:manualFields(),manual:true,error:null,confirmed:false});navigate('/app/review');}
    else void analyze(true);
  }
  async function reloadLatest() {
    if(!s.job)return;patch({pending:true,error:null,confirmed:false});
    try {const job=await reconcileCapture(s.job);patch({job,error:'Latest case state loaded. Your entered values are preserved; review them before confirming.',step:job.candidates.length ? 'review' : s.step,fields:s.fields.length ? s.fields : reviewFields(job.candidates)});}
    catch(cause){patch({error:captureError(cause)});await w.refresh();}finally{patch({pending:false});}
  }
  async function save(event:FormEvent) {
    event.preventDefault();if(s.pending || w.offline)return;
    const chosen=s.fields.filter(field=>field.selected);const errors:Record<string,string>={};
    if(!s.company.trim())errors.company='Enter the company that made the promise.';
    for(const field of chosen) {try {termsFromFields(field);}catch(cause){errors[field.id]=captureError(cause);}}
    if(!chosen.length)errors.selection='Choose at least one promise.';
    if(!s.confirmed)errors.confirmed='Confirm that you reviewed the selected promises.';
    if(s.job?.duplicateId && !s.allowDuplicate)errors.duplicate='Open the existing case or explicitly choose to create separately.';
    patch({formErrors:errors});if(Object.keys(errors).length || !s.job)return;
    patch({pending:true,error:null,scenario:s.scenario==='save-error' ? 'standard' : s.scenario});
    try {
      await confirmCapture(s.job,s.fields,s.manual,w.isMock && s.scenario==='save-error',{company:s.company,title:s.title.trim() || chosen[0].description.slice(0,200)});
      patch({step:'saved',savedId:s.job.caseId,savedDescription:chosen.map(f=>f.description).join(' · '),evidenceOnly:false,confirmed:false});w.markIntroduced();await w.refresh();
    } catch(cause) {
      const uncertain=!(cause instanceof ApiError) && !s.manual || cause instanceof ApiError && cause.status===409;
      patch({error:captureError(cause),confirmed:false,...(uncertain ? {job:{...s.job,state:'needs-reconciliation'}} : {})});
    } finally {patch({pending:false});}
  }
  async function keepEvidence() {
    if(!s.job || s.pending || w.offline)return;patch({pending:true,error:null});
    try{await retainEvidence(s.job);patch({step:'saved',evidenceOnly:true,savedId:s.job.caseId});w.markIntroduced();await w.refresh();}
    catch(cause){patch({error:captureError(cause),...(!(cause instanceof ApiError) || cause.status===409 ? {job:{...s.job,state:'needs-reconciliation'}} : {})});}finally{patch({pending:false});}
  }
  function editField(id:string, values:Partial<ReviewFields>) {patch({fields:s.fields.map(field=>field.id===id ? {...field,...values} : field),confirmed:false,formErrors:{}});}
  function viewQuote(field:ReviewFields) {
    const evidenceId=s.job?.candidates.find(c=>c.candidate_id===field.id)?.sources[0]?.evidence_id;
    const sourceKey=evidenceId && s.job?.uploadedKeys[s.job.evidenceIds.indexOf(evidenceId)];
    const index=reviewSources.findIndex(source=>source.key===sourceKey);setSourceIndex(Math.max(0,index));setMobileTab('source');
  }
  const failure=s.error && <div className="capture-error" role="alert"><CircleAlert size={21}/><div><strong>{s.step==='review' ? 'Your reviewed values are still here.' : 'Your input is still here.'}</strong><p>{s.error}</p>{s.job?.state==='needs-reconciliation' && <Button variant="secondary" onClick={()=>void reloadLatest()} disabled={s.pending}>Check latest case state</Button>}</div></div>;

  if(s.step==='saved')return <section className="capture-saved"><span className="saved-mark"><CheckCircle2 size={35}/></span><h1>{s.evidenceOnly ? 'Evidence kept. No promise tracked.' : 'The promise is on record.'}</h1><p>{s.evidenceOnly ? 'The original is attached to its case. No deadline or commitment was created.' : s.savedDescription}</p><div className="saved-facts"><span><FileCheck2 size={18}/>{s.evidenceOnly ? 'No AI suggestion was confirmed' : 'Confirmed by you'}</span><span><Link2 size={18}/> Original evidence linked</span></div><div className="capture-actions">{!s.evidenceOnly && <Link className="button button-primary" to={`/app/cases/${s.savedId}`}>View case <ArrowRight size={18}/></Link>}<Link className="button button-secondary" to="/app/cases">All cases</Link><Button variant="text" onClick={()=>{reset();navigate('/app/upload');}}>Add another promise <Plus size={17}/></Button></div></section>;
  if(s.step==='processing')return <section className="capture-processing" role="status" aria-live="polite"><div className="processing-art"><FileText size={40}/><span/><LoaderCircle size={24}/></div><h1>Keeping the words<br/><span>with the promise.</span></h1><p>{s.progress}</p><ol><li><Check size={17}/> Original evidence</li><li><LoaderCircle size={17}/> Supporting quotations</li><li><FileCheck2 size={17}/> Your review comes next</li></ol><p className="capture-meta">Nothing is tracked until you confirm it.</p></section>;
  if(s.step==='review')return <>
    <button type="button" className="workspace-back" disabled={s.pending} onClick={()=>{patch({step:'capture',confirmed:false,error:null});navigate('/app/upload');}}><ArrowLeft size={17}/> Back to capture</button>
    <PageHeading title={s.manual ? 'Your words. Your confirmation.' : s.fields.length>1 ? 'Choose what belongs on record.' : 'Is this what they promised?'} description="Review the details against the original before tracking them."/>
    {failure}
    {s.job?.duplicateId && <div className="duplicate-notice"><h2>This may already be on record.</h2><p>A case with this company and title exists. Check it before creating a second record.</p><Link to={`/app/cases/${s.job.duplicateId}`} className="workspace-text-link">View existing case <ArrowRight size={17}/></Link><label className="capture-check"><input type="checkbox" checked={s.allowDuplicate} onChange={e=>patch({allowDuplicate:e.target.checked,confirmed:false})}/> Create a separate case anyway.</label>{s.formErrors.duplicate && <p className="field-error">{s.formErrors.duplicate}</p>}</div>}
    {!s.fields.length ? <section className="capture-no-promise"><FileText size={32}/><h2>No clear promise was found.</h2><p>You can keep the communication as evidence, or enter a promise manually.</p><div className="capture-actions"><Button onClick={enterManual} disabled={s.pending}>Enter manually</Button><Button variant="secondary" onClick={()=>void keepEvidence()} disabled={s.pending || w.offline || s.job?.state==='needs-reconciliation'}>Keep evidence only</Button></div></section> : <>
    <div className="review-mobile-tabs" role="group" aria-label="Review view"><button aria-pressed={mobileTab==='fields'} onClick={()=>setMobileTab('fields')}>Fields</button><button aria-pressed={mobileTab==='source'} onClick={()=>setMobileTab('source')}>Source</button></div>
    <div className={`capture-review review-show-${mobileTab}`}><div className="review-source-column"><CaptureSource sources={reviewSources} selected={sourceIndex} select={setSourceIndex}/></div>
      <form className="capture-review-form" onSubmit={event=>void save(event)} noValidate>
        <fieldset disabled={s.pending}><label className="capture-label review-company">Company<input value={s.company} maxLength={200} readOnly={!w.isMock} onChange={e=>patch({company:e.target.value,confirmed:false})}/>{s.formErrors.company && <span className="field-error" role="alert">{s.formErrors.company}</span>}{!w.isMock && <span className="capture-meta">Company is fixed for this capture. Start a different capture to change it.</span>}</label>
        {s.fields.map((field,index)=><section className={`promise-review-card ${!field.selected ? 'promise-unselected' : ''}`} key={field.id}>
          <div className="promise-review-heading"><h2>{s.manual ? 'Manual promise' : `Promise ${index+1}`}</h2>{s.fields.length>1 && <label className="capture-check"><input type="checkbox" checked={field.selected} onChange={e=>editField(field.id,{selected:e.target.checked})}/>Track this</label>}</div>
          <fieldset disabled={!field.selected} className="promise-fields">
            <label className="capture-label">Promise type<select value={field.kind} onChange={e=>editField(field.id,{kind:e.target.value as ReviewFields['kind']})}><option value="refund">Refund</option><option value="replacement">Replacement</option><option value="service">Service credit</option><option value="other">Delivery / other</option></select></label>
            <label className="capture-label">What was promised?<textarea rows={3} value={field.description} maxLength={2000} onChange={e=>editField(field.id,{description:e.target.value})}/></label>
            {field.quote ? <div className="field-quote"><Link2 size={16}/><div><q>{field.quote}</q><button type="button" onClick={()=>viewQuote(field)}>View supporting source <ArrowRight size={14}/></button></div></div> : <p className="capture-meta">Entered by you. No supporting quotation was extracted.</p>}
            <div className="review-field-pair"><label className="capture-label">Amount (INR)<span className="label-optional">{field.kind==='refund' ? 'Required for refunds' : 'Optional'}</span><input inputMode="decimal" type="text" value={field.amount} placeholder="e.g. 3299" onChange={e=>editField(field.id,{amount:e.target.value})}/>{supportingFragment(field,'amount') && <span className="field-source-fragment">“{supportingFragment(field,'amount')}”</span>}</label><label className="capture-label">Confirmed deadline<span className="label-optional">Leave unset if unclear</span><input type="date" value={field.deadline} onChange={e=>editField(field.id,{deadline:e.target.value})}/>{supportingFragment(field,'deadline') && <span className="field-source-fragment">“{supportingFragment(field,'deadline')}”</span>}</label></div>
            <p className={`deadline-explanation ${!field.deadline || field.warnings.length ? 'needs-review-note' : ''}`}><CircleAlert size={17}/><span>{field.warnings.length ? field.warnings.join(' ') : field.explanation} {deadlineSummary(field)}</span></p>
            {s.formErrors[field.id] && <p className="field-error" role="alert">{s.formErrors[field.id]}</p>}
          </fieldset>
        </section>)}
        {s.formErrors.selection && <p className="field-error" role="alert">{s.formErrors.selection}</p>}
        <label className="capture-check confirm-facts"><input type="checkbox" checked={s.confirmed} onChange={e=>patch({confirmed:e.target.checked})}/><span>I’ve reviewed the selected promises, amounts and deadlines against the source.</span></label>
        {s.formErrors.confirmed && <p className="field-error" role="alert">{s.formErrors.confirmed}</p>}
        {s.manual && !w.isMock && <p className="needs-review-note">Manual saving isn’t available on the connected backend yet. Your values are preserved here. Retry extraction to use the supported confirmation flow.</p>}
        <div className="review-submit"><Button type="submit" disabled={s.pending || !s.confirmed || w.offline || s.manual && !w.isMock || s.job?.state==='needs-reconciliation'}>{s.pending ? <LoaderCircle className="spin" size={18}/> : <Check size={18}/>} {s.pending ? 'Saving your promise…' : 'Confirm & track'}</Button><span>No complaint is sent or filed.</span></div>
        </fieldset>
      </form></div></>}
  </>;
  return <><PageHeading title="Start with what they said." description="Bring the original. We’ll keep the promise beside it."/>
    {failure}
    <div className="capture-layout"><form className="capture-entry" onSubmit={event=>{event.preventDefault();void analyze();}}>
      <fieldset disabled={s.pending}><div className="capture-case-fields"><label className="capture-label">Company<input value={s.company} maxLength={200} disabled={Boolean(s.job?.caseId)} placeholder="Who made the promise?" onChange={e=>patch({company:e.target.value})}/>{s.formErrors.company && <span className="field-error">{s.formErrors.company}</span>}</label><label className="capture-label">Case title<span className="label-optional">Optional</span><input value={s.title} maxLength={200} disabled={Boolean(s.job?.caseId)} placeholder="e.g. Refund for returned order" onChange={e=>patch({title:e.target.value})}/></label></div>
      <div className="capture-tabs" role="group" aria-label="Evidence input method"><button type="button" aria-pressed={s.tab==='upload'} onClick={()=>patch({tab:'upload',error:null})}><CloudUpload size={18}/>Upload files</button><button type="button" aria-pressed={s.tab==='paste'} onClick={()=>patch({tab:'paste',error:null})}><FileText size={18}/>Paste a message</button></div>
      <input className="sr-only" ref={inputRef} type="file" aria-label="Choose evidence files" multiple accept={w.isMock ? 'image/png,image/jpeg,application/pdf,text/plain' : 'application/pdf,text/plain'} onChange={event=>receiveFiles(event.target.files)}/>
      {s.tab==='upload' ? <><div className={`capture-drop ${dragging ? 'is-dragging' : ''}`} onDragOver={event=>{event.preventDefault();setDragging(true);}} onDragLeave={()=>setDragging(false)} onDrop={event=>{event.preventDefault();setDragging(false);receiveFiles(event.dataTransfer.files);}}><CloudUpload size={36}/><h2>Drop the original right here.</h2><p>{w.isMock ? 'Screenshots, PDFs, or a company message saved as text.' : 'Text-layer PDFs or a company message saved as text.'}</p><Button type="button" onClick={()=>{replaceKey.current=null;inputRef.current?.click();}}>Choose files <Plus size={17}/></Button><span className="capture-meta">Up to 10 MB each · maximum 10 files</span></div>
      {uploads.length>0 && <ul className="capture-file-queue">{uploads.map(source=><li key={source.key} className={source.error ? 'file-has-error' : ''}><div className="queue-file-name"><FileText size={19}/><div><strong>{source.file.name}</strong><span>{(source.file.size/1024).toFixed(1)} KB</span></div><button type="button" aria-label={`Remove ${source.file.name}`} onClick={()=>patch({sources:s.sources.filter(item=>item.key!==source.key)})}><X size={18}/></button></div>{source.error ? <div className="file-error"><p>{source.error}</p><Button type="button" variant="text" onClick={()=>{replaceKey.current=source.key;inputRef.current?.click();}}>Replace</Button><Button type="button" variant="text" onClick={()=>patch({tab:'paste'})}>Paste instead</Button></div> : <label className="capture-label queue-date">Communication date<input type="date" value={source.communicationDate} onChange={e=>patch({sources:s.sources.map(item=>item.key===source.key ? {...item,communicationDate:e.target.value} : item)})}/></label>}</li>)}</ul>}
      {s.formErrors.sources && <p className="field-error" role="alert">{s.formErrors.sources}</p>}</> : <div className="paste-entry"><label className="capture-label">Original company message<textarea rows={8} maxLength={50000} placeholder="Paste the words exactly as the company sent them…" value={s.text} onChange={e=>patch({text:e.target.value})}/>{s.formErrors.text && <span className="field-error">{s.formErrors.text}</span>}</label><label className="capture-label">Communication date<span className="label-optional">Use the message date, not the upload date</span><input type="date" value={s.communicationDate} onChange={e=>patch({communicationDate:e.target.value})}/>{s.formErrors.communicationDate && <span className="field-error">{s.formErrors.communicationDate}</span>}</label></div>}
      {!w.isMock && <p className="capture-meta">The connected backend accepts text-layer PDF and UTF-8 text. Screenshots need a readable pasted message. Communication dates are kept in this review; the current backend does not store that field.</p>}
      <div className="capture-actions"><Button type="submit" disabled={w.offline || s.job?.state==='needs-reconciliation'}>{s.error && s.job?.caseId ? 'Retry extraction' : 'Review the promise'} {s.error && s.job?.caseId ? <RefreshCw size={18}/> : <ArrowRight size={18}/>}</Button><Button type="button" variant="text" onClick={enterManual} disabled={w.offline || s.job?.state==='needs-reconciliation'}>Enter manually</Button></div>
      </fieldset></form>
      <aside className="capture-guidance"><span className="capture-guide-mark"><FileCheck2 size={29}/></span><h2>A clear promise<br/>has three things.</h2><ol><li><span>1</span><div><strong>Who made it?</strong><p>The company or service provider.</p></div></li><li><span>2</span><div><strong>What will happen?</strong><p>A refund, replacement, delivery or credit.</p></div></li><li><span>3</span><div><strong>By when?</strong><p>A date or a clear time window.</p></div></li></ol><p>You’ll review every extracted field before anything is tracked.</p>{w.isMock && <details className="capture-samples"><summary>Try a sample communication</summary><p>Local demo extraction reads text. Uploaded images and PDFs can be previewed and entered manually.</p><label className="capture-label">Example<select value={s.scenario} disabled={s.pending} onChange={e=>useSample(e.target.value as Scenario)}>{sampleOptions().map(([id,label])=><option value={id} key={id}>{label}</option>)}</select></label><Button type="button" variant="secondary" disabled={s.pending} onClick={()=>useSample(s.scenario)}>Use this sample</Button></details>}</aside>
    </div>
    {s.job?.caseId && <button type="button" className="workspace-text-link" disabled={s.pending} onClick={()=>{if(window.confirm('Discard the unsaved review in this tab? Uploaded evidence may already be kept with the draft case.')){reset();navigate('/app/upload');}}}>Start a different capture</button>}
  </>;
}
