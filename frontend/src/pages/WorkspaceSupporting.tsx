import { Link, useParams } from 'react-router-dom';
import { ArrowLeft, ArrowRight, CalendarClock, FileText, FolderOpen, HelpCircle, Link2 } from 'lucide-react';
import { useWorkspace } from '../state/Workspace';
import { PageHeading, WorkspaceGate } from '../components/workspace/WorkspaceStates';
import { CompanyMark } from '../components/workspace/CaseList';
import { StatusLabel, type Status } from '../components/ui';
import { date, money } from '../lib/format';

export function CaseSummary() {
  const w = useWorkspace(); const {caseId} = useParams(); const item = w.data?.cases.find(c => c.id === caseId);
  return <WorkspaceGate><Link to="/app/cases" className="workspace-back"><ArrowLeft size={17}/> All cases</Link>{item ? <><PageHeading title={item.company} description={item.title}/><section className="case-summary"><div className="case-summary-brand"><CompanyMark name={item.company}/><span>Case summary</span><StatusLabel status={item.status}/></div><dl><div><dt>Promise</dt><dd>{item.title}</dd></div><div><dt>Amount</dt><dd>{money(item.amountMinor, item.currency ?? 'INR')}</dd></div><div><dt>Confirmed deadline</dt><dd>{date(item.dueAt, w.data?.timezone)}</dd></div><div><dt>Revisions preserved</dt><dd>{item.revisionCount}</dd></div><div><dt>Linked evidence</dt><dd>{item.evidenceCount} {item.evidenceCount === 1 ? 'file' : 'files'}</dd></div></dl><p>Deadlines use {w.data?.timezone ?? 'Asia/Kolkata'}. A company claiming fulfilment doesn’t close the case; you confirm the outcome.</p><Link to="/app/help" className="workspace-text-link">Understand case statuses <ArrowRight size={17}/></Link></section></> : <div className="workspace-empty"><FolderOpen size={34}/><h1>That case isn’t in this workspace.</h1><p>Return to your cases to pick an available record.</p><Link className="button button-primary" to="/app/cases">View cases <ArrowRight size={17}/></Link></div>}</WorkspaceGate>;
}
export function CaptureCheckpoint() {
  // GAP: Phase 3 implements capture/review. Do not simulate a save or accept real files here.
  return <><PageHeading title="Start with what they said." description="Keep the message and the promise together."/><section className="capture-checkpoint"><div className="capture-checkpoint-art" aria-hidden="true"><FileText size={36}/><span/><Link2 size={22}/></div><h2>Evidence capture is being prepared.</h2><p>Uploading and reviewing evidence aren’t available in this build yet. No files have been uploaded and no promises have been saved.</p><Link className="button button-primary" to="/app/cases">Explore your cases <ArrowRight size={17}/></Link></section></>;
}
export function ReservedWorkspacePage({kind}: {kind: 'evidence' | 'settings'}) {
  // GAP: Dedicated evidence viewer arrives in Phase 4; persisted preferences in Phase 6.
  const evidence = kind === 'evidence'; const w = useWorkspace();
  return <><PageHeading title={evidence ? 'The proof belongs with the promise.' : 'Your workspace, your calendar.'} description={evidence ? 'Original communications stay connected to their case.' : 'The assumptions behind your deadlines.'}/><section className="support-panel">{evidence ? <><FileText size={30}/><h2>Evidence stays with each case.</h2><p>Find the linked-file count in a case summary. Original file viewing is being prepared for this build.</p><Link className="button button-secondary" to="/app/cases">Find a case <ArrowRight size={17}/></Link></> : <><CalendarClock size={30}/><h2>Calendar</h2><dl className="calendar-settings"><div><dt>Timezone</dt><dd>{w.data?.timezone ?? 'Asia/Kolkata'}</dd></div><div><dt>Date-only deadlines</dt><dd>End at 23:59</dd></div><div><dt>Business days</dt><dd>Monday to Friday</dd></div><div><dt>Holidays</dt><dd>Not automatically excluded</dd></div></dl><p>Calendar and notification preferences are read-only in this build. Bindr does not send background reminders.</p><Link to="/app/help" className="workspace-text-link">Help & definitions <ArrowRight size={17}/></Link></>}</section></>;
}
const definitions: {status: Status; text: string}[] = [
  {status: 'Overdue', text: 'A confirmed deadline has passed and you have not confirmed fulfilment.'},
  {status: 'Due today', text: 'The confirmed deadline falls today in the case timezone.'},
  {status: 'Active', text: 'The promise is open. Check its confirmed date for the next step.'},
  {status: 'Resolved', text: 'You have confirmed that the promise was fulfilled.'},
  {status: 'Needs a date', text: 'The promise has no confirmed deadline. A missing date never means overdue.'},
];
export function WorkspaceHelp() {return <><PageHeading title="A clear record starts with clear terms." description="What each case status means."/><section className="definitions">{definitions.map(({status,text}) => <div key={status}><StatusLabel status={status}/><p>{text}</p></div>)}</section><div className="help-note"><HelpCircle size={23}/><p>Every extracted promise needs your review. A revised promise adds a new entry and preserves the original. A complaint draft is yours to edit; Bindr does not send or file it.</p></div></>;}
