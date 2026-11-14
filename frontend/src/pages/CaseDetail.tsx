import { useCallback,useEffect,useRef,useState } from 'react';
import { Link,useNavigate,useParams } from 'react-router-dom';
import { Archive,ArrowLeft,ArrowRight,CheckCircle2,ChevronRight,CircleAlert,FileText,History,Link2,LoaderCircle,MoreHorizontal,Plus,RefreshCw } from 'lucide-react';
import { Button,StatusLabel } from '../components/ui';
import { CompanyMark } from '../components/workspace/CaseList';
import EvidenceViewer from '../components/workspace/EvidenceViewer';
import OutcomeDialog,{type OutcomeInput} from '../components/workspace/OutcomeDialog';
import CaseActionDialog from '../components/workspace/CaseActionDialog';
import { caseReference,caseTimeline,loadCase,loadEvidenceFile,manageCase,recordCaseOutcome,sourceQuotes,type CaseView } from '../api/case-service';
import { ApiError,type Evidence } from '../api/types';
import { useWorkspace } from '../state/Workspace';
import { useComplaints } from '../state/Complaints';
import { newCapture,useCapture } from '../state/Capture';
import { reviewFields } from '../api/capture';
import { date,money } from '../lib/format';
import '../case-detail.css';

type Action='edit'|'reopen'|'archive'|'restore'|'delete';
export default function CaseDetail() {
  const {caseId=''}=useParams();const w=useWorkspace();const navigate=useNavigate();const complaints=useComplaints();const capture=useCapture();
  const [view,setView]=useState<CaseView|null>(null),[loading,setLoading]=useState(true),[loadError,setLoadError]=useState<string|null>(null);
  const [selected,setSelected]=useState<{evidence:Evidence;quote?:string}|null>(null);
  const [outcome,setOutcome]=useState(false),[action,setAction]=useState<Action|null>(null),[pending,setPending]=useState(false),[error,setError]=useState<string|null>(null),[notice,setNotice]=useState<string|null>(null),[needsRecheck,setNeedsRecheck]=useState(false);
  const sequence=useRef(0),inFlight=useRef(false);
  const reload=useCallback(async()=>{
    const current=++sequence.current;setLoading(true);setLoadError(null);
    try {
      if(w.offline)throw new Error('Reconnect to load the latest case.');
      if(w.isMock && w.view==='error')throw new Error('The case could not be loaded. Try again when the connection is restored.');
      const result=await loadCase(caseId);if(current===sequence.current)setView(result);return result;
    }catch(cause){if(current===sequence.current)setLoadError(cause instanceof ApiError && cause.status===404 ? 'This case is unavailable or has been removed.' : cause instanceof Error ? cause.message : 'This case could not load.');return null;}
    finally{if(current===sequence.current)setLoading(false);}
  },[caseId,w.offline,w.isMock,w.view]);
  useEffect(()=>{void reload();return()=>{sequence.current++;};},[reload]);
  function openSource(id:string,quote?:string) {
    const evidence=view?.detail.evidence.find(e=>e.id===id);
    // Missing references remain inspectable without inventing original content.
    setSelected({evidence:evidence ?? {id,case_id:caseId,filename:'Unavailable source',media_type:'',size_bytes:0,sha256:'',created_at:view!.detail.case.created_at,download_path:''},quote});
  }
  function begin(){if(inFlight.current || w.offline || loading || loadError || needsRecheck)return false;inFlight.current=true;setPending(true);setError(null);setNotice(null);return true;}
  function failed(cause:unknown){setError(cause instanceof Error ? cause.message : 'The change could not be saved. Your input is preserved.');if(!(cause instanceof ApiError) || cause.status===409)setNeedsRecheck(true);}
  async function checkLatest(){
    if(inFlight.current)return;inFlight.current=true;setPending(true);
    const fresh=await reload();
    if(fresh){setNeedsRecheck(false);setError(null);setNotice('Latest case loaded. Review its current state before saving again.');if(fresh.detail.case.status==='resolved')setOutcome(false);if(action==='archive' && fresh.meta.archived || action==='restore' && !fresh.meta.archived)setAction(null);}
    inFlight.current=false;setPending(false);await w.refresh();
  }
  async function saveOutcome(input:OutcomeInput){if(!view || !begin())return;try{await recordCaseOutcome(view,input);setOutcome(false);setNotice(input.kind==='full' ? 'Receipt confirmed. Your history and original evidence are preserved.' : input.kind==='partial' ? 'Partial receipt recorded. The remaining promise stays open.' : 'Check-in saved. The promise stays open.');await reload();await w.refresh();}catch(cause){failed(cause);}finally{inFlight.current=false;setPending(false);}}
  async function saveAction(data:{note?:string;company?:string;title?:string;confirmation?:string}) {
    if(!view || !action || !begin())return;
    try{await manageCase(view,action,data);setAction(null);if(action==='delete'){complaints.remove(caseId);await w.refresh();navigate('/app/cases');return;}setNotice('Your change is on record.');await reload();await w.refresh();}catch(cause){failed(cause);}finally{inFlight.current=false;setPending(false);}
  }
  async function resumeReview() {
    if(!view || !begin())return;
    try {
      const fresh=await loadCase(caseId);
      const draft=fresh.detail.extractions.filter(item=>item.status==='pending_review').at(-1);
      if(!draft)throw new Error('This draft has already been reviewed. Reload the current case.');
      const evidence=fresh.detail.evidence.filter(item=>draft.evidence_ids.includes(item.id));
      const sources=await Promise.all(evidence.map(async item=>({key:item.id,file:new File([await loadEvidenceFile(item)],item.filename,{type:item.media_type}),communicationDate:'',error:null})));
      capture.setSession({...newCapture(),company:fresh.detail.case.merchant_name,title:fresh.detail.case.title,sources,step:'review',fields:reviewFields(draft.candidates),job:{caseId,version:fresh.detail.case.version,evidenceIds:evidence.map(item=>item.id),uploadedKeys:evidence.map(item=>item.id),reviewEvidenceIds:draft.evidence_ids,extractionId:draft.id,candidates:draft.candidates,duplicateId:null,state:'ready'}});
      navigate('/app/review');
    }catch(cause){failed(cause);}finally{inFlight.current=false;setPending(false);}
  }
  const back=<Link className="workspace-back" to="/app/cases"><ArrowLeft size={17}/> All cases</Link>;
  if(!view)return <>{back}<section className="case-detail-empty" role={loadError ? 'alert' : 'status'}>{loading ? <LoaderCircle size={30} className="spin"/> : <FileText size={32}/>}<h1>{loading ? 'Opening the record…' : 'This case couldn’t load.'}</h1>{loadError && <><p>{loadError}</p><Button disabled={w.offline} onClick={()=>void reload()}><RefreshCw size={17}/>Try again</Button></>}</section></>;
  const {detail,row,meta}=view;const active=detail.commitments.filter(c=>c.status==='active');const resolved=detail.case.status==='resolved';
  const items=caseTimeline(view);const revisions=detail.commitments.filter(c=>c.supersedes_id);const original=detail.commitments.find(c=>!c.supersedes_id);const latest=revisions.at(-1);
  const disabled=pending || loading || w.offline || Boolean(loadError) || needsRecheck;
  const beginAction=(next:Action)=>{setError(null);setAction(next);};
  return <article className="case-detail">
    {back}
    {loadError && <div className="case-message case-message-warning" role="alert"><CircleAlert size={20}/><div><strong>Showing the last loaded record.</strong><p>{loadError}</p><Button variant="text" disabled={w.offline || loading} onClick={()=>void reload()}>Retry loading</Button></div></div>}
    {notice && <div className="case-message case-message-success" role="status"><CheckCircle2 size={20}/><p>{notice}</p></div>}
    {error && !outcome && !action && <div className="case-message case-message-warning" role="alert"><CircleAlert size={20}/><div><p>{error}</p>{needsRecheck && <Button variant="secondary" disabled={pending || w.offline} onClick={()=>void checkLatest()}>Check latest case state</Button>}</div></div>}
    <header className="case-detail-header"><div className="case-detail-identity"><CompanyMark name={row.company}/><div><div className="case-detail-reference"><span>{caseReference(caseId)}</span><ChevronRight size={14}/><span>{meta.archived ? 'Archived record' : 'Your promise record'}</span></div><h1>{row.company}</h1><p>{row.title}</p></div></div><div className="case-header-actions">
      {meta.archived ? <Button disabled={disabled || !w.isMock} onClick={()=>beginAction('restore')}><Archive size={18}/>Restore case</Button> : resolved ? <Button variant="secondary" disabled={disabled || !w.isMock} onClick={()=>beginAction('reopen')}><RefreshCw size={18}/>Reopen case</Button> : <><Link className={`button button-secondary ${disabled ? 'case-action-disabled' : ''}`} aria-disabled={disabled} tabIndex={disabled ? -1 : 0} to={`/app/cases/${caseId}/update`} onClick={e=>{if(disabled)e.preventDefault();}}><Plus size={18}/>Add communication</Link><Button disabled={disabled || !active.length} onClick={()=>{setError(null);setOutcome(true);}}><CheckCircle2 size={18}/>Record outcome</Button></>}
      <details className="case-more"><summary aria-label="More case actions"><MoreHorizontal size={23}/></summary><div><button disabled={disabled || !w.isMock || meta.archived} onClick={e=>{e.currentTarget.closest('details')?.removeAttribute('open');beginAction('edit');}}>Edit case details</button><button disabled={disabled || !w.isMock} onClick={e=>{e.currentTarget.closest('details')?.removeAttribute('open');beginAction(meta.archived ? 'restore' : 'archive');}}>{meta.archived ? 'Restore case' : 'Archive case'}</button><button className="case-danger-link" disabled={disabled || !w.isMock} onClick={e=>{e.currentTarget.closest('details')?.removeAttribute('open');beginAction('delete');}}>Delete case</button>{!w.isMock && <p>Case management needs backend support.</p>}</div></details>
    </div></header>
    {!active.length && !resolved && detail.extractions.some(item=>item.status==='pending_review') && <section className="case-message case-message-warning"><FileText size={22}/><div><h2>Your extracted promise needs review.</h2><p>No promise or amount is tracked until you confirm the terms against the original.</p><Button disabled={disabled} onClick={()=>void resumeReview()}>Continue review <ArrowRight size={17}/></Button></div></section>}
    <div className={`case-state-strip ${meta.archived ? 'case-state-archived' : resolved ? 'case-state-resolved' : row.status==='Overdue' ? 'case-state-overdue' : ''}`}><StatusLabel status={row.status}/><p>{meta.archived ? 'Archived. The evidence stays with this record. Restore it to resume tracking.' : resolved ? 'You confirmed fulfilment. The full history stays on record.' : meta.partiallyFulfilled ? 'Partially fulfilled. The remaining promise and its deadline stay open.' : row.status==='Overdue' ? 'The confirmed deadline has passed. Receipt is still unconfirmed.' : row.status==='Due today' ? 'Due today in Asia/Kolkata. Confirm the outcome when it arrives.' : row.status==='Needs review' ? 'Evidence retained. No promise is tracked until its terms are confirmed.' : row.status==='Needs a date' ? 'No confirmed deadline. This promise is never marked overdue without a date.' : 'The promise is open. Keep the next update with the original.'}</p></div>
    <dl className="case-facts-strip"><div><dt>{resolved ? 'Confirmed amount' : meta.receivedMinor ? 'Still awaiting' : 'Promised amount'}</dt><dd>{row.multipleCurrencies ? 'Multiple currencies' : money(resolved ? view.totalMinor : view.outstandingMinor,row.currency ?? 'INR')}</dd>{meta.receivedMinor>0 && <p>{money(meta.receivedMinor)} received · {money(view.totalMinor,row.currency ?? 'INR')} original total</p>}{view.totalMinor===null && <p>{row.status==='Needs review' ? 'Not confirmed yet' : row.multipleCurrencies ? 'See the amount on each promise' : 'Non-monetary promise'}</p>}</div><div><dt>Current deadline</dt><dd className="case-fact-date">{date(row.dueAt)}</dd><p>{row.dueAt ? 'Asia/Kolkata · see each promise below' : 'Needs your confirmation'}</p></div><div><dt>On the record</dt><dd>{detail.evidence.length}<span> {detail.evidence.length===1 ? 'source' : 'sources'}</span></dd><p>{row.revisionCount} {row.revisionCount===1 ? 'revision' : 'revisions'} preserved</p></div></dl>
    {original && latest && <section className="case-revision-summary" aria-label="Original and revised deadlines"><History size={22}/><div><h2>The date moved. The proof stayed.</h2><p>Every confirmed version is preserved below.</p></div><div><span>Original deadline</span><strong>{date(original.due_at)}</strong></div><ArrowRight size={20}/><div><span>Latest revision</span><strong>{date(latest.due_at)}</strong></div></section>}
    <div className="case-detail-columns"><section className="case-history" aria-labelledby="history-heading"><div className="case-section-heading"><h2 id="history-heading">The full story.</h2><span><History size={17}/>{items.length} events</span></div>
      {!items.length ? <div className="case-history-empty"><FileText size={30}/><h3>Start the record with a communication.</h3><p>Sources can stay here even before a promise is confirmed.</p></div> : <ol className="case-timeline">{items.map(item=>{const commitment=item.commitment;const quotes=commitment ? sourceQuotes(detail,commitment.id) : [];return <li key={item.id} className={`case-event case-event-${item.kind} ${commitment?.status==='superseded' ? 'case-event-superseded' : ''}`}><span className="case-event-marker" aria-hidden="true"/><div className="case-event-head"><h3>{item.title}</h3><time dateTime={item.at}>{date(item.at)}</time></div><p className="case-event-note">{item.note}</p>{commitment && <><div className="case-event-terms"><span>{commitment.amount_minor!==null ? money(commitment.amount_minor,commitment.currency ?? 'INR') : 'Non-monetary promise'}</span><span>Due {date(commitment.due_at)}</span><span className={`case-promise-state ${commitment.status}`}>{commitment.status==='superseded' ? 'Earlier version retained' : commitment.status==='fulfilled' ? 'Fulfilled' : 'Current promise'}</span></div>{quotes.length ? quotes.map(source=><div className="case-source-quotation" key={source.evidence_id}><q>{source.quote}</q><button className="workspace-text-link" onClick={()=>openSource(source.evidence_id,source.quote)}><Link2 size={16}/>View original source <ArrowRight size={16}/></button></div>) : <p className="case-no-quote">User-confirmed terms. No extracted quotation is available for this entry.</p>}</>}{item.amountMinor!=null && <strong className="case-event-amount">{money(item.amountMinor)} received</strong>}{item.evidenceIds.length>0 && <div className="case-event-sources">{item.evidenceIds.map(id=><button key={id} onClick={()=>openSource(id)}><FileText size={15}/>{detail.evidence.find(e=>e.id===id)?.filename ?? 'Unavailable source'}</button>)}</div>}</li>;})}</ol>}
    </section><aside className="case-record-sidebar"><section className="case-source-index"><div className="case-section-heading"><h2>Linked evidence</h2><FileText size={21}/></div>{!detail.evidence.length ? <p>No files are attached yet.</p> : <ul>{detail.evidence.map((e,index)=><li key={e.id}><button onClick={()=>openSource(e.id)}><span className="case-source-number">{String(index+1).padStart(2,'0')}</span><span><strong>{e.filename}</strong><small>Added {date(e.created_at)}</small></span><ArrowRight size={17}/></button></li>)}</ul>}<Link className="workspace-text-link" to="/app/evidence">All evidence <ArrowRight size={17}/></Link></section>
      <section className="case-record-details"><h2>Record details</h2><dl><div><dt>Created</dt><dd>{date(detail.case.created_at)}</dd></div><div><dt>Timezone</dt><dd>Asia/Kolkata</dd></div><div><dt>Calendar</dt><dd>Mon–Fri · no holiday exclusion</dd></div><div><dt>Outcome</dt><dd>{resolved ? 'Confirmed by you' : meta.partiallyFulfilled ? 'Partial fulfilment confirmed' : 'Awaiting your confirmation'}</dd></div></dl><details><summary>Full case ID</summary><code>{caseId}</code></details></section>
      {!resolved && !meta.archived && active.length>0 && <section className="case-next-step"><FileText size={23}/><h2>Make your follow-up count.</h2><p>Prepare an editable complaint from your confirmed promise, preserved revisions and original sources.</p><Link className={`button button-primary ${disabled ? 'case-action-disabled' : ''}`} aria-disabled={disabled} tabIndex={disabled ? -1 : 0} to={`/app/cases/${caseId}/complaint`} onClick={e=>{if(disabled)e.preventDefault();}}>Prepare complaint <ArrowRight size={17}/></Link></section>}
    </aside></div>
    <EvidenceViewer evidence={selected?.evidence ?? null} quote={selected?.quote} loadFile={loadEvidenceFile} onClose={()=>setSelected(null)}/>
    <OutcomeDialog open={outcome} currency={row.currency ?? 'INR'} monetary={view.totalMinor!==null} outstandingMinor={view.outstandingMinor} allowExtended={w.isMock} busy={pending} blocked={needsRecheck || w.offline || loading || Boolean(loadError)} error={error} onReload={()=>void checkLatest()} onClose={()=>{if(!pending)setOutcome(false);}} onSubmit={input=>void saveOutcome(input)}/>
    <CaseActionDialog action={action} caseId={caseId} company={row.company} title={row.title} busy={pending} blocked={needsRecheck || w.offline || loading || Boolean(loadError)} error={error} onReload={()=>void checkLatest()} onClose={()=>{if(!pending)setAction(null);}} onSubmit={data=>void saveAction(data)}/>
  </article>;
}
