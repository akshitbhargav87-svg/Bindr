import { useSearchParams } from 'react-router-dom';
import { Search, SlidersHorizontal, X } from 'lucide-react';
import { useWorkspace } from '../state/Workspace';
import { AddPromise, EmptyWorkspace, PageHeading, WorkspaceGate } from '../components/workspace/WorkspaceStates';
import { CaseList, NoCases } from '../components/workspace/CaseList';
import { filterCases, filters, type CaseFilter } from '../lib/cases';

export default function Cases() {
  const w = useWorkspace(); const [params, setParams] = useSearchParams();
  const search = params.get('q') ?? '';
  const selected = filters.includes(params.get('status') as CaseFilter) ? params.get('status') as CaseFilter : 'All';
  const cases = w.data?.cases ?? []; const matches = filterCases(cases, search, selected);
  function update(key: string, value: string) {setParams(previous => {const next = new URLSearchParams(previous); if (value && value !== 'All') next.set(key,value); else next.delete(key); return next;}, {replace: true});}
  const clear = () => setParams({}, {replace: true});
  return <><PageHeading title="All your promises. On record." description="Find a case, check the date, and keep the story together."><AddPromise/></PageHeading><WorkspaceGate>
    {!cases.length ? <EmptyWorkspace/> : <section className="cases-surface" aria-label="All cases"><div className="cases-search-row"><label className="cases-search"><Search size={19}/><span className="sr-only">Search cases by company or promise</span><input value={search} type="search" placeholder="Search company or promise" onChange={e => update('q', e.target.value)}/></label><span className="case-total">{cases.length} cases</span></div><div className="case-filter-bar"><SlidersHorizontal size={17} aria-hidden="true"/><div className="status-filters" role="group" aria-label="Filter cases by status">{filters.map(status => <button key={status} onClick={() => update('status',status)} aria-pressed={selected === status} className={selected === status ? 'selected' : ''}>{status}<span>{filterCases(cases,'',status).length}</span></button>)}</div></div>
    {(selected !== 'All' || search) && <div className="active-filters"><span>Showing {matches.length} of {cases.length}</span>{selected !== 'All' && <button onClick={() => update('status','All')} aria-label={`Remove ${selected} filter`}>{selected} <X size={14}/></button>}{search && <button onClick={() => update('q','')} aria-label="Clear search">“{search}” <X size={14}/></button>}<button className="clear-all" onClick={clear}>Clear all</button></div>}
    <p className="sr-only" role="status" aria-live="polite">{matches.length} matching {matches.length === 1 ? 'case' : 'cases'}</p>
    {matches.length ? <CaseList cases={matches} timezone={w.data?.timezone}/> : <NoCases search={search} filtered={selected !== 'All'} clear={clear}/>}
    <div className="cases-footer"><span>{matches.length} {matches.length === 1 ? 'case' : 'cases'}</span><span>Deadlines in {w.data?.timezone ?? 'Asia/Kolkata'}</span></div></section>}
  </WorkspaceGate></>;
}
