import { useCallback,useEffect,useRef,useState } from 'react';
import { Link,useSearchParams } from 'react-router-dom';
import { Archive,ArrowLeft,ArrowRight,FileText,FolderOpen,LoaderCircle,RefreshCw,Search } from 'lucide-react';
import { Button } from '../components/ui';
import { CaseList } from '../components/workspace/CaseList';
import { PageHeading } from '../components/workspace/WorkspaceStates';
import EvidenceViewer from '../components/workspace/EvidenceViewer';
import { listEvidence,loadEvidenceFile,type CaseView } from '../api/case-service';
import { ApiError,type Evidence } from '../api/types';
import { useWorkspace } from '../state/Workspace';
import { date } from '../lib/format';
import '../record-library.css';

function useLibrary() {
  const w=useWorkspace();const [views,setViews]=useState<CaseView[]|null>(null),[loading,setLoading]=useState(true),[error,setError]=useState<string|null>(null);const sequence=useRef(0);
  const reload=useCallback(async()=>{const current=++sequence.current;setLoading(true);setError(null);try {
    if(w.offline)throw new Error('Reconnect to load your files. Your records have not changed.');
    if(w.isMock && w.view==='error')throw new Error('The records could not load. Try again to reconnect.');
    const result=await listEvidence();if(current===sequence.current)setViews(w.isMock && w.view==='empty' ? result.filter(v=>!v.row.demoSeed) : result);
  }catch(cause){if(current===sequence.current)setError(cause instanceof Error ? cause.message : 'Your files could not load.');}finally{if(current===sequence.current)setLoading(false);}},[w.offline,w.isMock,w.view]);
  useEffect(()=>{void reload();return()=>{sequence.current++;};},[reload]);return {views,loading,error,reload,w};
}
const missingPreview=async()=>{throw new ApiError(404,{code:'NOT_FOUND',message:'This original file is unavailable.',details:[],request_id:''});};
export default function EvidenceLibrary() {
  const {views,loading,error,reload,w}=useLibrary();const [params,setParams]=useSearchParams();const [search,setSearch]=useState('');const [selected,setSelected]=useState<Evidence|null>(null);const [previewMissing,setPreviewMissing]=useState(false);
  const missingRequested=w.isMock && params.get('missing')==='1';
  useEffect(()=>{if(missingRequested && views?.some(v=>v.detail.evidence.length)){setSelected(views.find(v=>v.detail.evidence.length)!.detail.evidence[0]);setPreviewMissing(true);}},[missingRequested,views]);
  const all=views?.flatMap(v=>v.detail.evidence.map(e=>({e,view:v}))) ?? [];
  const needle=search.trim().toLowerCase();const matches=all.filter(({e,view})=>`${e.filename} ${view.row.company} ${view.row.title}`.toLowerCase().includes(needle));
  function close(){setSelected(null);setPreviewMissing(false);if(missingRequested)setParams({}, {replace:true});}
  return <><PageHeading title="The proof. In one place." description="Original communications, always linked to their case."/>
    {error && <div className="library-error" role="alert"><p>{error} {views && 'Previously loaded file references are shown.'}</p><Button variant="secondary" disabled={w.offline || loading} onClick={()=>{if(w.isMock && w.view==='error')w.chooseView('sample');else void reload();}}><RefreshCw size={17}/>Retry</Button></div>}
    {loading && !views ? <div className="library-empty" role="status"><LoaderCircle className="spin" size={28}/><h2>Opening the evidence index…</h2></div> : !error && !all.length ? <div className="library-empty"><FileText size={36}/><h2>The first source starts the story.</h2><p>Add a company message or document. Its original will stay linked to the case.</p><Link className="button button-primary" to="/app/upload">Add evidence <ArrowRight size={17}/></Link></div> : views && <section className="record-library"><div className="library-toolbar"><label><Search size={19}/><span className="sr-only">Search evidence by filename, company or case</span><input type="search" placeholder="Search file, company or case" value={search} onChange={e=>setSearch(e.target.value)}/></label><span>{matches.length} {matches.length===1 ? 'file' : 'files'}</span></div>
      {matches.length ? <ul className="library-files">{matches.map(({e,view})=><li key={e.id}><button className="library-open-file" disabled={w.offline} onClick={()=>{setPreviewMissing(false);setSelected(e);}}><span className="library-file-icon"><FileText size={24}/></span><span><strong>{e.filename}</strong><span>{e.media_type==='application/pdf' ? 'PDF' : e.media_type.startsWith('image/') ? 'Image' : 'Text'} · {new Intl.NumberFormat('en-IN',{maximumFractionDigits:1}).format(e.size_bytes/1024)} KB · Added {date(e.created_at)}</span></span><ArrowRight size={18}/></button><Link className="library-case-link" to={`/app/cases/${view.detail.case.id}`}><span>{view.row.company}{view.meta.archived && ' · Archived'}</span><small>{view.row.title}</small></Link></li>)}</ul> : <div className="library-empty" role="status"><Search size={30}/><h2>No files match that search.</h2><p>Try a filename, company or word from the case.</p><Button variant="secondary" onClick={()=>setSearch('')}>Clear search</Button></div>}
    </section>}
    <EvidenceViewer evidence={selected} loadFile={previewMissing ? missingPreview : loadEvidenceFile} onClose={close}/>
  </>;
}
export function ArchivedCases() {
  const {views,loading,error,reload,w}=useLibrary();const archived=views?.filter(v=>v.meta.archived) ?? [];
  return <><Link className="workspace-back" to="/app/cases"><ArrowLeft size={17}/> All cases</Link><PageHeading title="Set aside. Still on record." description="Archived cases keep their promises and evidence together."/>
    {error && <div className="library-error" role="alert"><p>{error}</p><Button variant="secondary" disabled={w.offline} onClick={()=>void reload()}>Retry</Button></div>}
    {loading && !views ? <div className="library-empty" role="status"><LoaderCircle className="spin" size={28}/><h2>Loading archived records…</h2></div> : archived.length ? <><p className="archive-guidance"><Archive size={18}/>Open a case to restore it to your workspace.</p><CaseList cases={archived.map(v=>v.row)}/></> : <div className="library-empty"><FolderOpen size={36}/><h2>No cases set aside.</h2><p>{w.isMock ? 'Archived cases will appear here. Their evidence stays available.' : 'Archive and restore need backend support before they can be used here.'}</p><Link className="button button-secondary" to="/app/cases">Back to your cases <ArrowRight size={17}/></Link></div>}
  </>;
}
