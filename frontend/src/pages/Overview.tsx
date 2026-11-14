import { Link } from 'react-router-dom';
import { ArrowRight, CalendarClock, CheckCircle2, FileText, Plus } from 'lucide-react';
import { useWorkspace } from '../state/Workspace';
import { CaseList, CompanyMark } from '../components/workspace/CaseList';
import { AddPromise, EmptyWorkspace, PageHeading, Welcome, WorkspaceGate } from '../components/workspace/WorkspaceStates';
import { date, money } from '../lib/format';
import { summarizeCases } from '../lib/cases';
import { usePreferences } from '../state/Preferences';

export default function Overview() {
  const w = useWorkspace();
  const preferences=usePreferences();
  if (!w.introduced) return <Welcome/>;
  const cases = w.data?.cases ?? [];
  const totals = summarizeCases(cases);
  const urgent = cases.filter(c => c.status === 'Overdue' || c.status === 'Due today');
  const upcoming = cases.filter(c => c.status === 'Active' && c.dueAt).sort((a,b) => a.dueAt!.localeCompare(b.dueAt!));
  const resolved = cases.filter(c => c.status === 'Resolved');
  return <><PageHeading title="A little less chasing." description="Your promises, deadlines, and next steps—in one place."><AddPromise/></PageHeading><WorkspaceGate>
    {!cases.length ? <EmptyWorkspace/> : <>
    {preferences.preferences.deadlinePrompts && urgent.length>0 && <div className="overview-deadline-prompt" role="status"><CalendarClock size={22}/><div><strong>{urgent.length} {urgent.length===1 ? 'promise needs' : 'promises need'} a check-in.</strong><span>Confirm what arrived, or keep the latest reply on record.</span></div><Link className="workspace-text-link" to="/app/agenda">View deadlines <ArrowRight size={17}/></Link></div>}
    <section className="summary-strip" aria-label="Workspace summary"><Link to="/app/cases?status=Open"><span>Open cases <ArrowRight size={16}/></span><strong>{totals.open}</strong><small>Promises still to follow through</small></Link><Link to="/app/cases?status=Open"><span>Awaiting amount <ArrowRight size={16}/></span><strong>{money(totals.outstandingMinor)}</strong><small>Across confirmed monetary promises</small></Link><Link to="/app/cases?status=Overdue"><span>Overdue <ArrowRight size={16}/></span><strong className={totals.overdue ? 'overdue-number' : ''}>{totals.overdue.toString().padStart(2, '0')}</strong><small>{totals.overdue === 1 ? 'Promise past its confirmed date' : 'Promises past their confirmed dates'}</small></Link></section>
    <section className="urgent-section"><div className="section-heading"><div><h2>Needs your attention <span className="section-count">{urgent.length}</span></h2><p>{urgent.length ? 'A deadline has arrived. Keep the next step on record.' : 'No overdue or due-today status is currently reported.'}</p></div><Link to="/app/cases" className="workspace-text-link">All cases <ArrowRight size={17}/></Link></div>
    {urgent.length ? <CaseList cases={urgent} timezone={w.data?.timezone}/> : <div className="quiet-empty"><CheckCircle2 size={23}/><span>No overdue promises or deadlines due today.</span></div>}</section>
    <div className="overview-lower"><section className="upcoming-section"><div className="section-heading"><div><h2>Coming up next</h2><p>Confirmed deadlines, in order.</p></div><CalendarClock size={22}/></div>{upcoming.length ? <ul className="upcoming-list">{upcoming.slice(0,4).map(item => <li key={item.id}><Link to={`/app/cases/${item.id}`}><span className="deadline-date"><CalendarClock size={19}/>{date(item.dueAt, w.data?.timezone)}</span><div><strong>{item.company}</strong><span>{item.title}</span></div><ArrowRight size={17}/></Link></li>)}</ul> : <div className="quiet-empty"><CalendarClock size={22}/><p>No upcoming dates. Add a promise when you have one.</p></div>}<p className="calendar-note">Date-only deadlines end at 23:59 in {w.data?.timezone ?? 'Asia/Kolkata'}.</p></section>
    <section className="record-reminder"><div className="reminder-art" aria-hidden="true"><div><img src="/bindr-mark.svg" alt=""/><span/><span/></div><span className="reminder-link"><FileText size={22}/></span></div><h2>The date changed?<br/><span>Keep the original.</span></h2><p>A new message belongs with the whole story. Your earlier promise stays on record.</p><Link to="/app/upload" className="workspace-text-link">Add a communication <Plus size={17}/></Link></section></div>
    {resolved.length > 0 && <section className="resolved-section"><div className="section-heading"><div><h2>Follow-through, recorded.</h2><p>Outcomes you’ve confirmed.</p></div><Link to="/app/cases?status=Resolved" className="workspace-text-link">Resolved cases <ArrowRight size={17}/></Link></div>{resolved.slice(0,2).map(item => <Link key={item.id} to={`/app/cases/${item.id}`} className="resolved-row"><CompanyMark name={item.company}/><div><strong>{item.company}</strong><span>{item.title}</span></div><span className="resolved-amount">{money(item.amountMinor, item.currency ?? 'INR')}</span><span className="resolved-confirmed"><CheckCircle2 size={17}/> Received {date(item.resolvedAt, w.data?.timezone)}</span><ArrowRight size={17}/></Link>)}</section>}
    </>}
  </WorkspaceGate></>;
}
