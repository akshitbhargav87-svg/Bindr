import DateField from '../components/ui/DateField';
import {useRef,useState} from 'react';
import {Link} from 'react-router-dom';
import {useCapture} from '../state/Capture';
import {Button} from '../components/ui';
import ProposalReview from '../components/workspace/ProposalReview';
import {operation,prepareEvidenceUpload,uploadResult,createdCase,extractionResponse,type Communication,type Operation} from '../api/v2';
import {Workflow} from '../api/workflow';
import {PlatformClient,mutationResult} from '../api/platform';
import {minorUnits,validDay} from '../api/capture-validation';
import type {V2CaptureState} from '../api/capture-model';
import '../workflow.css';
const client=new PlatformClient(),workflow=new Workflow(client,mutationResult);
const fresh=():V2CaptureState=>({caseId:null,version:0,evidenceIds:[],uploadedKeys:[],proposal:null,job:null,operations:{}});
export default function IntelligenceCapture(){
  const {session:s,setSession,reset}=useCapture(),guard=useRef(false);
  const [notice,setNotice]=useState('');
  const state=s.v2 ?? fresh(),manual=state.manualDescription ?? '',amount=state.manualAmount ?? '',enabled=import.meta.env.VITE_ENABLE_V2_CAPTURE==='true';
  const patch=(values:Partial<typeof s>)=>setSession(old=>({...old,...values}));
  const keep=(value:V2CaptureState)=>setSession(old=>({...old,v2:{...value}}));
  function opFor(state:V2CaptureState,name:string,body:unknown):Operation{const op=state.operations[name] ?? operation(body);if(op.payload!==JSON.stringify(body))throw new Error('This request changed after an uncertain result. Reconcile the previous request before starting again.');state.operations[name]=op;keep(state);return op;}
  async function prepare(){
    if(guard.current || !enabled)return;guard.current=true;patch({pending:true,error:null});const current=s.v2 ?? fresh();keep(current);
    try{
      if(!s.company.trim())throw new Error('Enter the company that made the promise.');
      if(s.sources.length+(s.text.trim() ? 1 : 0)>10)throw new Error('Choose at most ten sources, including a pasted message.');
      if(s.sources.some(source=>!source.file.size || source.file.size>10*1024*1024))throw new Error('Choose nonempty originals up to 10 MiB each.');
      if(s.text.length>50000 || (!s.text.trim() && !s.sources.length))throw new Error('Paste a message up to 50,000 characters or attach an original.');
      if(s.sources.some(source=>source.communicationDate && !validDay(source.communicationDate)) || s.communicationDate && !validDay(s.communicationDate))throw new Error('Review the communication date.');
      const today=new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Kolkata',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date());
      if([s.communicationDate,...s.sources.map(source=>source.communicationDate)].some(date=>date>today) && !confirm('The communication date is in the future. Keep this date for review?'))throw new Error('Review the source date before continuing.');
      if(!current.caseId){const body={title:s.title.trim() || `Promise from ${s.company.trim()}`.slice(0,200),merchant_name:s.company.trim()};const created=await client.mutate('/cases',body,opFor(current,'create',body),createdCase);current.caseId=created.id;current.version=created.version;keep(current);}
      const sources=[...s.sources];
      if(s.text.trim() && !sources.some(f=>f.key==='v2-paste'))sources.push({key:'v2-paste',file:new File([s.text],'company-message.txt',{type:'text/plain'}),communicationDate:s.communicationDate,error:null});
      if(sources.length>10)throw new Error('Choose at most ten sources.');
      for(const source of sources){
        if(current.uploadedKeys.includes(source.key))continue;
        const date=source.key==='v2-paste' ? s.communicationDate || null : source.communicationDate || null;
        const communication:Communication={date,time:null,timezone:'Asia/Kolkata',precision:date ? 'date' : 'unknown',provenance:'user_confirmed',original_wording:null};
        const upload=await prepareEvidenceUpload(source.file,current.version,communication,current.operations[source.key]);current.operations[source.key]=upload.operation;keep(current);
        const result=await client.request(`/cases/${encodeURIComponent(current.caseId)}/evidence`,uploadResult,{method:'POST',...upload});
        if(!current.evidenceIds.includes(result.evidence.id))current.evidenceIds.push(result.evidence.id);current.uploadedKeys.push(source.key);current.version=result.case_version;keep(current);
        if(result.duplicate_of)setNotice('A matching original already exists in this case. Review the evidence reference before continuing.');
      }
      if(current.proposal || current.job){setNotice('The previous extraction is retained. Review it or check its job status.');return;}
      const body={expected_version:current.version,evidence_ids:current.evidenceIds};
      const result=await client.mutate(`/cases/${encodeURIComponent(current.caseId)}/extractions`,body,opFor(current,'extract',body),extractionResponse);
      current.proposal=result.proposal;current.job=result.job;
      if(result.case_version!==null)current.version=result.case_version;
      keep(current);
    }catch(e){patch({error:e instanceof Error ? e.message : 'Capture could not be confirmed. Your source is still here.'});}finally{guard.current=false;patch({pending:false});}
  }
  async function confirmReview(decisions:Parameters<Workflow['review']>[1]['decisions']){if(!state.caseId || !state.proposal || guard.current || !enabled)return;guard.current=true;patch({pending:true,error:null});try{const body={expected_version:state.version,proposal_id:state.proposal.proposal_id,decisions};const saved=await workflow.review(state.caseId,body,opFor(state,'review',body));state.version=saved.case_version;keep(state);patch({step:'saved',savedId:state.caseId});}finally{guard.current=false;patch({pending:false});}}
  async function saveManual(){if(!state.caseId || guard.current || !enabled)return;guard.current=true;patch({pending:true,error:null});try{const amount_minor=minorUnits(amount);const body={expected_version:state.version,terms:{kind:amount_minor===null ? 'other' : 'refund',description:manual,amount_minor,currency:amount_minor===null ? null : 'INR',due_at:null},source_ids:state.evidenceIds,origin:state.evidenceIds.length ? 'source_backed' : 'user_attested'};const saved=await client.mutate(`/cases/${encodeURIComponent(state.caseId)}/manual-promises`,body,opFor(state,'manual',body),mutationResult);state.version=saved.case_version;keep(state);patch({step:'saved',savedId:state.caseId});}catch(e){patch({error:e instanceof Error ? e.message : 'Manual entry could not be saved.'});}finally{guard.current=false;patch({pending:false});}}
  return <section className="workflow"><h1>Capture and review every promise</h1>{!enabled && <p role="status">Capture is unavailable on this release. You can still open your saved cases.</p>}<Link to="/app">Back to workspace</Link>{s.error && <p role="alert">{s.error}</p>}{notice && <p role="status">{notice}</p>}{s.step==='saved' ? <><h2>Saved</h2><Link to={`/app/cases/${encodeURIComponent(s.savedId ?? '')}/workflow`}>Open saved case</Link><Button onClick={reset}>Start another capture</Button></> : <><fieldset disabled={s.pending}><label>Company<input readOnly={Boolean(state.caseId)} maxLength={200} value={s.company} onChange={e=>patch({company:e.target.value})}/></label><label>Case title (optional)<input readOnly={Boolean(state.caseId)} maxLength={200} value={s.title} onChange={e=>patch({title:e.target.value})}/></label><label>Original message<textarea readOnly={Boolean(state.caseId)} maxLength={50000} value={s.text} onChange={e=>patch({text:e.target.value})}/></label><label>Communication date<DateField label="Communication date" readOnly={Boolean(state.caseId)}  value={s.communicationDate} onChange={dateValue=>patch({communicationDate:dateValue})}/></label><label>Original files<input disabled={Boolean(state.caseId)} type="file" multiple accept=".png,.jpg,.jpeg,.pdf,.txt,.eml,.msg,.wav,.mp3,.m4a,.ogg" onChange={e=>{const incoming=Array.from(e.target.files ?? []).map(file=>({key:crypto.randomUUID(),file,communicationDate:s.communicationDate,error:null}));patch({sources:[...s.sources,...incoming].slice(0,10),error:s.sources.length+incoming.length>10 ? 'At most ten files are retained. Extra selections were not added.' : null});}}/></label><ul>{s.sources.map(source=><li key={source.key}>{source.file.name} · {source.file.size} bytes<label>Source communication date<DateField label="Communication date"  disabled={Boolean(state.caseId)} value={source.communicationDate} onChange={dateValue=>patch({sources:s.sources.map(item=>item.key===source.key ? {...item,communicationDate:dateValue} : item)})}/></label></li>)}</ul><p>Email, scanned PDF, MSG and audio imports depend on the configured server processors. Original files and unconfirmed dates remain distinct from AI suggestions.</p><Button disabled={!enabled} onClick={()=>void prepare()}>{s.pending ? 'Processing…' : 'Extract all proposals'}</Button></fieldset>{state.proposal && <ProposalReview key={state.proposal.proposal_id} proposal={state.proposal} initialDraft={state.reviewDraft?.proposal_id===state.proposal.proposal_id ? state.reviewDraft.values : undefined} onDraftChange={values=>setSession(old=>({...old,v2:{...(old.v2 ?? fresh()),reviewDraft:{proposal_id:state.proposal!.proposal_id,values}}}))} busy={s.pending || !enabled} onConfirm={confirmReview}/>} {state.job && <div role="status"><p>{state.job.status} · {state.job.stage}</p><Button onClick={()=>void client.job(state.job!.id).then(value=>{state.job=value;keep(state);}).catch(e=>patch({error:e.message}))}>Check extraction status</Button><p>A completed queued job needs the platform's authorized proposal retrieval response before review can open.</p></div>}{state.caseId && <section><h2>Manual entry when extraction is unavailable</h2><label>Promise recorded by you<textarea maxLength={2000} value={manual} onChange={e=>keep({...state,manualDescription:e.target.value})}/></label><label>Refund amount in INR, or leave blank for a non-monetary promise<input inputMode="decimal" value={amount} onChange={e=>keep({...state,manualAmount:e.target.value})}/></label><Button disabled={!enabled || !manual.trim()} onClick={()=>void saveManual()}>Save reviewed manual entry</Button><p>No quotation or AI extraction is invented for manual entries.</p></section>}</>}</section>;
}
