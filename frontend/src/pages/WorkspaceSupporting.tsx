import { Link, useParams } from 'react-router-dom';
import { ArrowLeft, ArrowRight, CalendarClock, FileText, FolderOpen, HelpCircle } from 'lucide-react';
import { useWorkspace } from '../state/Workspace';
import { PageHeading, WorkspaceGate } from '../components/workspace/WorkspaceStates';
import { CompanyMark } from '../components/workspace/CaseList';
import { StatusLabel, type Status } from '../components/ui';
import { date, money } from '../lib/format';

export function CaseSummary() {
  const w = useWorkspace(); const {caseId} = useParams(); const item = w.data?.cases.find(c => c.id === caseId);
  return <WorkspaceGate><Link to="/app/cases" className="workspace-back"><ArrowLeft size={17}/> All cases</Link>{item ? <><PageHeading title={item.company} description={item.title}/><section className="case-summary"><div className="case-summary-brand"><CompanyMark name={item.company}/><span>Case summary</span><StatusLabel status={item.status}/></div><dl><div><dt>Promise</dt><dd>{item.title}</dd></div><div><dt>Amount</dt><dd>{money(item.amountMinor, item.currency ?? 'INR')}</dd></div><div><dt>Confirmed deadline</dt><dd>{date(item.dueAt, w.data?.timezone)}</dd></div><div><dt>Revisions preserved</dt><dd>{item.revisionCount}</dd></div><div><dt>Linked evidence</dt><dd>{item.evidenceCount} {item.evidenceCount === 1 ? 'file' : 'files'}</dd></div></dl><p>Deadlines use {w.data?.timezone ?? 'Asia/Kolkata'}. A company claiming fulfilment doesn’t close the case; you confirm the outcome.</p><Link to="/app/help" className="workspace-text-link">Understand case statuses <ArrowRight size={17}/></Link></section></> : <div className="workspace-empty"><FolderOpen size={34}/><h1>That case isn’t in this workspace.</h1><p>Return to your cases to pick an available record.</p><Link className="button button-primary" to="/app/cases">View cases <ArrowRight size={17}/></Link></div>}</WorkspaceGate>;
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
export function WorkspaceHelp() {
  const w=useWorkspace();
  const topics=[
    ['What can I add?',w.isMock ? 'Paste a company message or attach UTF-8 text, PNG/JPEG or PDF. Text extraction reads pasted/plain text locally; images and PDFs can be viewed, kept as evidence and entered manually. Files are limited to 10 MB each.' : 'Paste a company message, upload UTF-8 plain text or a PDF with a readable text layer. Scanned PDFs and screenshots need a pasted message. Files are limited to 10 MB each.'],
    ['How are deadlines counted?','The communication date is day zero. Counting starts on the following day. Business days skip Saturday and Sunday; holidays are not automatically excluded. Ranges use their final day for overdue. Date-only deadlines end at 23:59 in Asia/Kolkata. Confirm uncertain wording during review.'],
    ['What if the company changes its promise?','Add its communication to the existing case. Confirm whether it revises an earlier promise, adds a separate one or belongs as evidence only. A revision preserves the earlier terms and their sources. A conflicting date is your choice to confirm, never an automatic replacement.'],
    ['Does “refund processed” close my case?','No. That is a company claim. The case stays open until you confirm what you actually received. A partial outcome keeps the remaining promise and its original deadline open.'],
    ['Will Bindr send my complaint?','No. Edit the draft, review the facts and choose the export contents. You can copy text or download a text file. The evidence index lists source filenames; original files are not attached automatically.'],
    ['Where do drafts and preferences stay?','In the connected workspace, saved complaint drafts, preferences and read markers are kept in your cloud account. Unsaved edits remain in memory until you save. The separate demo uses temporary tab data and browser preferences.'],
    ['What do activity preferences change?','They control deadline prompts on Overview and the activity items displayed inside Bindr. They never alter case status, confirmed deadlines or full case history. No push, email or background reminders are sent.'],
  ];
  return <><PageHeading title="A clear record starts with clear terms." description="Understand the promise, the date and your next step."/><section className="definitions">{definitions.map(({status,text})=><div key={status}><StatusLabel status={status}/><p>{text}</p></div>)}</section><div className="help-note"><HelpCircle size={23}/><p>Every extracted promise needs your review. Your confirmation turns a suggestion into a tracked commitment.</p></div><section className="help-sections" aria-label="How Bindr works">{topics.map(([question,answer])=><details key={question}><summary>{question}</summary><p>{answer}</p></details>)}</section><div className="help-shortcuts"><Link className="workspace-text-link" to="/app/upload">Add a promise <ArrowRight size={17}/></Link><Link className="workspace-text-link" to="/app/agenda">Deadline agenda <ArrowRight size={17}/></Link><Link className="workspace-text-link" to="/app/settings">Activity preferences <ArrowRight size={17}/></Link></div></>;
}
