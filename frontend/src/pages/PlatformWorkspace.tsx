import {useCallback,useEffect,useRef,useState} from 'react';
import {Link,useLocation,useSearchParams} from 'react-router-dom';
import {ArrowRight,CheckCircle2,FolderOpen,RefreshCw,Search} from 'lucide-react';
import {PlatformClient,platformSnapshot} from '../api/platform';
import {snapshot,type CaseSnapshot} from '../api/v2';
import type {CaseRow} from '../api/mapper';
import {Button} from '../components/ui';
import {CaseList,NoCases} from '../components/workspace/CaseList';
import {AddPromise,EmptyWorkspace,LoadingWorkspace,PageHeading} from '../components/workspace/WorkspaceStates';
import {useWorkspace} from '../state/Workspace';
import {filterCases,filters,type CaseFilter} from '../lib/cases';

const client=new PlatformClient();
const workflowLink=(item:CaseRow)=>`/app/cases/${encodeURIComponent(item.id)}/workflow`;
function row(c:CaseSnapshot):CaseRow {
  const active=c.obligations.filter(o=>!['superseded','revoked','cancelled'].includes(o.semantic_status));
  const balances=c.projection.money_by_currency;
  const dueAt=active.map(o=>o.terms.due_at).filter((d):d is string=>Boolean(d)).sort()[0] ?? null;
  return {id:c.id,company:c.merchant_name ?? '',title:c.title ?? 'Untitled case',version:c.version,
    status:c.projection.status==='resolved' ? 'Resolved' : c.projection.status==='overdue' ? 'Overdue' : !active.length ? 'Needs review' : active.every(o=>!o.terms.due_at) ? 'Needs a date' : 'Active',
    amountMinor:balances.length===1 ? balances[0].amount_minor : null,
    currency:balances.length===1 ? balances[0].currency : null,multipleCurrencies:balances.length>1,
    partial:active.some(o=>o.terms.amount_minor!==null && o.balance.some(m=>m.amount_minor>0 && m.amount_minor<o.terms.amount_minor!)),
    dueAt,revisionCount:c.obligations.filter(o=>o.semantic_status==='superseded').length,
    evidenceCount:c.evidence?.length ?? 0,resolvedAt:null};
}

export default function PlatformWorkspace(){
  const previous=useWorkspace(),location=useLocation(),[params,setParams]=useSearchParams();
  const [cases,setCases]=useState<CaseSnapshot[]|null>(null),[error,setError]=useState(''),[loading,setLoading]=useState(true);
  const generation=useRef(0);
  const load=useCallback(async()=>{
    const seq=++generation.current;setLoading(true);setError('');
    try{const result=await client.request('/workspace',v=>{
      const envelope=v as {cases:unknown[]};
      if(!Array.isArray(envelope.cases))throw new Error('Invalid workspace response.');
      return envelope.cases.map(v=>snapshot(platformSnapshot(v)));
    });if(seq===generation.current)setCases(result);}
    catch{if(seq===generation.current)setError('Your records could not load. Please try again.');}
    finally{if(seq===generation.current)setLoading(false);}
  },[]);
  useEffect(()=>{void load();return()=>{generation.current++;};},[load]);
  const allCases=location.pathname==='/app/cases';
  const rows=(cases ?? []).filter(c=>c.obligations.length>0 || !c.legacy_commitments?.length).map(row);
  const earlierIds=new Set((cases ?? []).filter(c=>!c.obligations.length && c.legacy_commitments?.length).map(c=>c.id));
  const earlier=(previous.data?.cases ?? []).filter(c=>earlierIds.has(c.id));
  const search=params.get('q') ?? '';
  const selected=filters.includes(params.get('status') as CaseFilter) ? params.get('status') as CaseFilter : 'All';
  const matches=filterCases(rows,search,selected),earlierMatches=filterCases(earlier,search,selected);
  const urgent=rows.filter(c=>c.status==='Overdue' || c.status==='Needs review');
  function update(key:string,value:string){setParams(old=>{const next=new URLSearchParams(old);if(value && value!=='All')next.set(key,value);else next.delete(key);return next;},{replace:true});}
  return <>
    <PageHeading title={allCases ? 'All your promises. On record.' : 'A little less chasing.'}
      description={allCases ? 'Find a case, check the date, and keep the story together.' : 'Your promises, deadlines, and next steps—in one place.'}><AddPromise/></PageHeading>
    {error && <section className="workspace-empty error-state" role="alert"><FolderOpen size={36}/><h2>Your records couldn’t load.</h2><p>{error}</p><Button onClick={()=>void load()}><RefreshCw size={17}/> Try again</Button></section>}
    {loading && !cases && <LoadingWorkspace/>}
    {cases && !cases.length && !error && <EmptyWorkspace/>}
    {cases && cases.length>0 && <>
      {!allCases && <section className="summary-strip" aria-label="Workspace summary">
        <Link to="/app/cases?status=Open"><span>Open cases <ArrowRight size={16}/></span><strong>{rows.filter(c=>c.status!=='Resolved').length+earlier.filter(c=>c.status!=='Resolved').length}</strong><small>Promises still to follow through</small></Link>
        <Link to="/app/cases"><span>Cases on record <ArrowRight size={16}/></span><strong>{cases.length}</strong><small>Your saved company communications</small></Link>
        <Link to="/app/cases?status=Overdue"><span>Overdue <ArrowRight size={16}/></span><strong className={rows.some(c=>c.status==='Overdue') || earlier.some(c=>c.status==='Overdue') ? 'overdue-number' : ''}>{rows.filter(c=>c.status==='Overdue').length+earlier.filter(c=>c.status==='Overdue').length}</strong><small>Past their confirmed dates</small></Link>
      </section>}
      {allCases ? <section className="cases-surface" aria-label="All cases">
        <div className="cases-search-row"><label className="cases-search"><Search size={19}/><span className="sr-only">Search cases</span><input type="search" value={search} placeholder="Search company or promise" onChange={e=>update('q',e.target.value)}/></label><span className="case-total">{cases.length} cases</span></div>
        <div className="case-filter-bar"><div className="status-filters" role="group" aria-label="Filter cases by status">{filters.map(status=><button key={status} aria-pressed={selected===status} className={selected===status ? 'selected' : ''} onClick={()=>update('status',status)}>{status}<span>{filterCases([...rows,...earlier],'',status).length}</span></button>)}</div></div>
        {matches.length>0 && <CaseList cases={matches} caseLink={workflowLink}/>}
        {earlierMatches.length>0 && <><div className="cases-footer"><span>Earlier records</span><span>Open a case for its saved promises</span></div><CaseList cases={earlierMatches}/></>}
        {!matches.length && !earlierMatches.length && !previous.loading && <NoCases search={search} filtered={selected!=='All'} clear={()=>setParams({})}/>}
      </section> : <>
        <section className="urgent-section"><div className="section-heading"><div><h2>Needs your attention <span className="section-count">{urgent.length}</span></h2><p>{urgent.length ? 'Keep the next step on record.' : 'Your latest promises and receipts.'}</p></div><Link to="/app/cases" className="workspace-text-link">All cases <ArrowRight size={17}/></Link></div>
          {rows.length>0 ? <CaseList cases={urgent.length ? urgent : rows.slice(0,5)} caseLink={workflowLink}/> : <div className="quiet-empty"><CheckCircle2 size={23}/><span>Your earlier promises are saved below.</span></div>}
        </section>
        {earlier.length>0 && <section className="resolved-section"><div className="section-heading"><div><h2>Earlier records</h2><p>Your saved promises and original evidence.</p></div></div><CaseList cases={earlier}/></section>}
      </>}
      {earlierIds.size>0 && previous.loading && <LoadingWorkspace/>}
      {earlierIds.size>0 && previous.error && <div className="workspace-inline-error" role="alert"><span>Earlier records could not load.</span><Button variant="secondary" onClick={()=>void previous.refresh()}>Retry</Button></div>}
    </>}
  </>;
}
