import { useEffect, useRef, useState, type FormEvent } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { ArrowLeft, ArrowRight, Check, CircleAlert, FileText, GitCompareArrows, Link2, LoaderCircle, RefreshCw, Upload, X } from 'lucide-react';
import { Button } from '../components/ui';
import { PageHeading } from '../components/workspace/WorkspaceStates';
import CaptureSource from '../components/workspace/CaptureSource';
import { useWorkspace } from '../state/Workspace';
import { captureError, deadlineSummary, prepareCapture, reconcileCapture, reviewFields, supportingFragment, validateFile } from '../api/capture';
import { dayInIndia, termsFromFields, validDay } from '../api/capture-validation';
import { communicationSample, keepCommunication, loadCase, reviewCommunication, type CaseView } from '../api/case-service';
import type { CaptureJob, CaptureSource as Source, ReviewFields } from '../api/capture-model';
import { ApiError } from '../api/types';
import { date, money } from '../lib/format';
import '../communication.css';

type Action = { action: '' | 'new' | 'revision'; predecessor: string };
type Sample = 'revision' | 'conflict' | 'update' | 'claim';

/** Case-local capture: original uploads stay attached even when no new promise is accepted. */
export default function CaseCommunication() {
  const {caseId = ''} = useParams();
  const navigate = useNavigate();
  const workspace = useWorkspace();
  const [view, setView] = useState<CaseView | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [tab, setTab] = useState<'paste' | 'upload'>('paste');
  const [step, setStep] = useState<'input' | 'review'>('input');
  const [text, setText] = useState('');
  const [file, setFile] = useState<File | null>(null);
  const [communicationDate, setCommunicationDate] = useState('');
  const [matched, setMatched] = useState(false);
  const [source, setSource] = useState<Source | null>(null);
  const [job, setJob] = useState<CaptureJob | null>(null);
  const [fields, setFields] = useState<ReviewFields[]>([]);
  const [actions, setActions] = useState<Record<string, Action>>({});
  const [reason, setReason] = useState('');
  const [note, setNote] = useState('');
  const [claim, setClaim] = useState(false);
  const [confirmed, setConfirmed] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [progress, setProgress] = useState('');
  const [mobileTab, setMobileTab] = useState<'fields' | 'source'>('fields');
  const [sample, setSample] = useState<Sample>('revision');
  const picker = useRef<HTMLInputElement>(null);
  const inFlight = useRef(false);
  const saved = useRef(false);
  const busyRef = useRef(false);
  const active = view?.detail.commitments.filter(item => item.status === 'active') ?? [];
  const selected = fields.filter(field => field.selected);
  const hasRevision = selected.some(field => actions[field.id]?.action === 'revision');
  const blocked = busy || workspace.offline || job?.state === 'needs-reconciliation';

  useEffect(() => {
    let current = true;
    setLoading(true); setLoadError(null);
    if (workspace.offline) {setLoading(false); setLoadError('Reconnect before adding a communication. Your input stays in this tab.'); return;}
    void loadCase(caseId).then(result => {if (current) setView(result);}).catch(cause => {if (current) setLoadError(captureError(cause));}).finally(() => {if (current) setLoading(false);});
    return () => {current = false;};
  }, [caseId, workspace.offline]);

  useEffect(() => {
    if ((!text && !file && !job) || saved.current) return;
    const warn = (event: BeforeUnloadEvent) => {if (!saved.current) {event.preventDefault(); event.returnValue = '';}};
    window.addEventListener('beforeunload', warn);
    return () => window.removeEventListener('beforeunload', warn);
  }, [text, file, job]);

  function begin() {if (inFlight.current || workspace.offline) return false; inFlight.current = true; busyRef.current = true; setBusy(true); setError(null); return true;}
  function finish() {inFlight.current = false; busyRef.current = false; setBusy(false);}
  function updateJob(value: CaptureJob, label: string) {setJob(structuredClone(value)); setProgress(label);}
  function updateField(id: string, values: Partial<ReviewFields>) {setFields(items => items.map(item => item.id === id ? {...item, ...values} : item)); setConfirmed(false);}
  function updateAction(id: string, values: Partial<Action>) {setActions(previous => ({...previous, [id]: {...(previous[id] ?? {action: '', predecessor: ''}), ...values}})); setConfirmed(false);}
  function rememberFailure(cause: unknown) {
    setError(captureError(cause)); setConfirmed(false);
    if (!(cause instanceof ApiError) || cause.status === 409) setJob(previous => previous ? {...previous, state: 'needs-reconciliation'} : previous);
  }
  async function inputSource(): Promise<Source> {
    if (!view) throw new Error('Load the case before continuing.');
    if (!matched) throw new Error('Confirm that this message belongs to the selected case.');
    if (communicationDate && !validDay(communicationDate)) throw new Error('Choose a valid communication date or leave it unset.');
    if (tab === 'paste') {
      if (!text.trim()) throw new Error('Paste the original company message.');
      if (text.length > 50000) throw new Error('Use at most 50,000 characters.');
      if (source?.file.type === 'text/plain' && await source.file.text() === text) return {...source, communicationDate};
      return {key: `paste:${crypto.randomUUID()}`, file: new File([text], 'company-update.txt', {type: 'text/plain'}), communicationDate, error: null};
    }
    if (!file) throw new Error('Choose the original file, or paste its text.');
    const problem = validateFile(file, workspace.isMock);
    if (problem) throw new Error(problem);
    return source?.file === file ? {...source, communicationDate} : {key: crypto.randomUUID(), file, communicationDate, error: null};
  }
  function initialJob(): CaptureJob {
    return {caseId, version: view!.detail.case.version, evidenceIds: [], uploadedKeys: [], extractionId: null, candidates: [], duplicateId: null, state: 'ready'};
  }
  async function analyze(onlyEvidence = false) {
    if (!begin()) return;
    setProgress('Preparing the original communication');
    try {
      // Validate before entering the request pipeline; a local field error is not an uncertain POST.
      const original = await inputSource(); setSource(original);
      const next = await prepareCapture({company: view!.detail.case.merchant_name, title: view!.detail.case.title, sources: [original]}, job ?? initialJob(), updateJob, false, onlyEvidence);
      setJob(next);
      if (onlyEvidence) {setFields([]); setStep('review');}
      else {
        setFields(reviewFields(next.candidates));
        setActions(Object.fromEntries(next.candidates.map(candidate => [candidate.candidate_id, {action: '', predecessor: ''}])));
        setStep('review');
      }
      setConfirmed(false); setMobileTab('fields');
    } catch (cause) {setError(captureError(cause));}
    finally {finish();}
  }
  async function checkLatest() {
    if (!job || !begin()) return;
    try {
      const next = await reconcileCapture(job); const fresh = await loadCase(caseId);
      setJob(next); setView(fresh);
      if (!fields.length && next.candidates.length) {setFields(reviewFields(next.candidates)); setActions(Object.fromEntries(next.candidates.map(candidate => [candidate.candidate_id, {action: '', predecessor: ''}]))); setStep('review');}
      setConfirmed(false); setError('Latest case loaded. Your entered values are preserved; review them before saving.');
    } catch (cause) {setError(captureError(cause)); await workspace.refresh();}
    finally {finish();}
  }
  async function savePromises(event: FormEvent) {
    event.preventDefault();
    if (blocked || !job || !view) return;
    try {
      if (!selected.length) throw new Error('Choose at least one promise, or keep this communication as evidence only.');
      if (!confirmed) throw new Error('Confirm that you reviewed the selected promises against the original.');
      const predecessors = new Set<string>();
      for (const field of selected) {
        termsFromFields(field);
        const choice = actions[field.id];
        if (!choice?.action) throw new Error('Choose whether each selected promise is new or revises an existing promise.');
        if (choice.action === 'revision') {
          if (!active.some(item => item.id === choice.predecessor)) throw new Error('Choose an active promise to revise.');
          if (predecessors.has(choice.predecessor)) throw new Error('Two revisions cannot replace the same promise in one confirmation.');
          predecessors.add(choice.predecessor);
        }
      }
      if (hasRevision && !reason.trim()) throw new Error('Explain why the new wording replaces the earlier promise.');
    } catch (cause) {setError(captureError(cause)); return;}
    if (!begin()) return;
    setProgress('Saving your confirmed promises');
    try {
      await reviewCommunication(job, selected.map(field => ({field, action: actions[field.id].action as 'new' | 'revision', predecessor: actions[field.id].action === 'revision' ? actions[field.id].predecessor : null})), reason);
      saved.current = true; await workspace.refresh(); navigate(`/app/cases/${caseId}`);
    } catch (cause) {rememberFailure(cause);}
    finally {finish();}
  }
  async function saveEvidence() {
    if (blocked || !job || !begin()) return;
    setProgress('Keeping the communication with this case');
    try {
      await keepCommunication(job, claim ? 'claim' : 'update', note);
      saved.current = true; await workspace.refresh(); navigate(`/app/cases/${caseId}`);
    } catch (cause) {rememberFailure(cause);}
    finally {finish();}
  }
  function useSample() {
    if (!view || busyRef.current || job?.evidenceIds.length) return;
    const example = communicationSample(view, sample);
    setTab('paste'); setText(example.text); setCommunicationDate(example.communicationDate); setClaim(sample === 'claim'); setError(null); setMatched(false);
  }
  async function retryLoad() {
    if (!begin()) return;
    setProgress('Loading the current case');
    try {setView(await loadCase(caseId)); setLoadError(null);} catch (cause) {setLoadError(captureError(cause));} finally {finish();}
  }

  const back = <Link className="workspace-back" to={`/app/cases/${caseId}`}><ArrowLeft size={17}/> Back to case</Link>;
  if (loading && !view) return <section className="communication-loading" role="status"><LoaderCircle className="spin" size={26}/><h1>Loading the case…</h1></section>;
  if (!view) return <>{back}<section className="communication-empty" role="alert"><FileText size={32}/><h1>This case couldn’t load.</h1><p>{loadError}</p><Button onClick={() => void retryLoad()} disabled={busy || workspace.offline}><RefreshCw size={17}/>Try again</Button></section></>;
  if (view.meta.archived || view.detail.case.status === 'resolved') return <>{back}<section className="communication-empty"><FileText size={32}/><h1>{view.meta.archived ? 'Restore this case first.' : 'This case has been resolved.'}</h1><p>{view.meta.archived ? 'Its original evidence is still with the case. Restore it before adding a communication.' : 'Reopen it with a reason before adding another promise.'}</p><Link className="button button-primary" to={`/app/cases/${caseId}`}>Return to case <ArrowRight size={17}/></Link></section></>;

  return <section className="case-communication">
    {step === 'input' ? back : <button className="workspace-back" disabled={busy} onClick={() => {setStep('input'); setConfirmed(false); setError(null);}}><ArrowLeft size={17}/> Back to communication</button>}
    <PageHeading title={step === 'input' ? 'Keep the next chapter, too.' : 'What changed in their promise?'} description={step === 'input' ? 'Add the company’s latest words to the same case.' : 'Confirm the relationship. Both versions stay on record.'}/>
    <div className="communication-case"><div><strong>{view.detail.case.merchant_name}</strong><span>{view.detail.case.title}</span></div><Link to={`/app/cases/${caseId}`} className="workspace-text-link">View case <ArrowRight size={17}/></Link></div>
    {(error || loadError) && <div className="capture-error" role="alert"><CircleAlert size={21}/><div><strong>Your communication and edits are still here.</strong><p>{error ?? loadError}</p>{job?.state === 'needs-reconciliation' && <Button variant="secondary" disabled={busy || workspace.offline} onClick={() => void checkLatest()}>Check latest case state</Button>}<Link className="workspace-text-link" to={`/app/cases/${caseId}`}>Open current case <ArrowRight size={17}/></Link></div></div>}
    {busy && <p className="communication-progress" role="status"><LoaderCircle className="spin" size={18}/>{progress || 'Saving your communication…'}</p>}
    {step === 'input' ? <div className="communication-input-layout"><form className="capture-entry" onSubmit={event => {event.preventDefault(); void analyze();}}><fieldset disabled={busy}>
      <div className="capture-tabs" role="group" aria-label="Communication input method"><button type="button" aria-pressed={tab === 'paste'} onClick={() => setTab('paste')}><FileText size={18}/>Paste a message</button><button type="button" aria-pressed={tab === 'upload'} onClick={() => setTab('upload')}><Upload size={18}/>Upload a file</button></div>
      {tab === 'paste' ? <label className="capture-label">Original company message<textarea rows={8} maxLength={50000} value={text} onChange={event => {setText(event.target.value); setMatched(false);}} placeholder="Paste the exact words they sent…"/></label> : <div className="communication-file"><input ref={picker} className="sr-only" type="file" accept='image/png,image/jpeg,application/pdf,text/plain' onChange={event => {setFile(event.target.files?.[0] ?? null); setMatched(false); setError(null);}} aria-label="Choose original communication"/>{file ? <><div className="communication-selected-file"><FileText size={23}/><strong>{file.name}</strong><button type="button" aria-label="Remove selected file" onClick={() => {setFile(null); if (picker.current) picker.current.value = '';}}><X size={18}/></button></div>{validateFile(file, workspace.isMock) && <p className="field-error">{validateFile(file, workspace.isMock)}</p>}<Button type="button" variant="secondary" onClick={() => picker.current?.click()}>Replace file</Button></> : <><Upload size={32}/><h2>Bring the original.</h2><p>{workspace.isMock ? 'A screenshot, PDF or UTF-8 text file.' : 'A screenshot, PDF or UTF-8 text file.'} Up to 10 MB.</p><Button type="button" onClick={() => picker.current?.click()}>Choose file</Button></>}</div>}
      <label className="capture-label communication-date">Communication date<span className="label-optional">Use the message date, not the upload date</span><input type="date" value={communicationDate} onChange={event => setCommunicationDate(event.target.value)}/></label>
      <label className="capture-check communication-match"><input type="checkbox" checked={matched} onChange={event => setMatched(event.target.checked)}/><span>This communication belongs to <strong>{view.detail.case.merchant_name}</strong> and this case.</span></label>
      <Link className="workspace-text-link" to="/app/upload">Different issue? Start a separate case <ArrowRight size={17}/></Link>
      {!workspace.isMock && <p className="capture-meta">Communication dates are available for this review; the connected backend does not store that field.</p>}
      <div className="capture-actions"><Button type="submit" disabled={blocked}>{job?.evidenceIds.length ? 'Retry extraction' : 'Review communication'} <ArrowRight size={18}/></Button><Button type="button" variant="text" onClick={() => void analyze(true)} disabled={blocked}>Keep original without extraction</Button></div>
    </fieldset></form><aside className="communication-guide"><GitCompareArrows size={32}/><h2>A new date doesn’t erase the old one.</h2><p>Choose whether the message adds a new promise, revises an existing one, or simply belongs in the evidence.</p><div><Check size={18}/><p>The earlier terms and their sources stay visible.</p></div><div><CircleAlert size={18}/><p>A company saying “processed” does not confirm receipt.</p></div>{workspace.isMock && <details className="capture-samples"><summary>Try a sample communication</summary><label className="capture-label">Example<select value={sample} onChange={event => setSample(event.target.value as Sample)} disabled={busy || Boolean(job?.evidenceIds.length)}><option value="revision">Revised promise</option><option value="conflict">Conflicting deadline</option><option value="update">Update without a promise</option><option value="claim">Company claims fulfilment</option></select></label><Button type="button" variant="secondary" disabled={busy || Boolean(job?.evidenceIds.length)} onClick={useSample}>Use this sample</Button><p>Local demo extraction reads text. Images and PDFs can be kept as evidence.</p></details>}</aside></div> : <>
      <div className="review-mobile-tabs" role="group" aria-label="Communication review view"><button aria-pressed={mobileTab === 'fields'} onClick={() => setMobileTab('fields')}>Fields</button><button aria-pressed={mobileTab === 'source'} onClick={() => setMobileTab('source')}>Source</button></div>
      <div className={`capture-review review-show-${mobileTab}`}><div className="review-source-column"><CaptureSource sources={source ? [source] : []} selected={0} select={() => {}}/></div><div className="communication-fields-column">
      {fields.length ? <form className="capture-review-form" onSubmit={event => void savePromises(event)} noValidate><fieldset disabled={busy}>
        {fields.map((field, index) => {
          const choice = actions[field.id] ?? {action: '', predecessor: ''};
          const predecessor = active.find(item => item.id === choice.predecessor);
          const differentDate = choice.action === 'revision' && predecessor && (predecessor.due_at ? dayInIndia(predecessor.due_at) : '') !== field.deadline;
          return <section className={`promise-review-card ${!field.selected ? 'promise-unselected' : ''}`} key={field.id}>
            <div className="promise-review-heading"><h2>Promise {index + 1}</h2>{fields.length > 1 && <label className="capture-check"><input type="checkbox" checked={field.selected} onChange={event => updateField(field.id, {selected: event.target.checked})}/>Track this</label>}</div>
            <fieldset disabled={!field.selected} className="promise-fields">
              <label className="capture-label">How does this belong?<select value={choice.action} onChange={event => updateAction(field.id, {action: event.target.value as Action['action']})}><option value="">Choose new or revised promise</option><option value="revision" disabled={!active.length}>Revises an existing promise</option><option value="new">Adds a separate promise to this case</option></select></label>
              {choice.action === 'revision' && <label className="capture-label">Which promise does it replace?<select value={choice.predecessor} onChange={event => updateAction(field.id, {predecessor: event.target.value})}><option value="">Choose the earlier promise</option>{active.map(item => <option value={item.id} key={item.id}>{item.description} · {date(item.due_at)}</option>)}</select></label>}
              {predecessor && choice.action === 'revision' && <div className="communication-comparison"><div><span>Earlier confirmed promise</span><strong>{money(predecessor.amount_minor, predecessor.currency ?? 'INR')}</strong><p>{date(predecessor.due_at)}</p></div><ArrowRight size={19}/><div><span>Proposed revision</span><strong>{field.amount ? `INR ${field.amount}` : 'No amount set'}</strong><p>{field.deadline ? date(field.deadline) : 'No date set'}</p></div></div>}
              {differentDate && <p className="needs-review-note">These dates differ. Confirm that the new message replaces the selected promise. Keeping it as evidence leaves the earlier deadline unchanged.</p>}
              <label className="capture-label">Promise type<select value={field.kind} onChange={event => updateField(field.id, {kind: event.target.value as ReviewFields['kind']})}><option value="refund">Refund</option><option value="replacement">Replacement</option><option value="service">Service credit</option><option value="other">Delivery / other</option></select></label>
              <label className="capture-label">What was promised?<textarea rows={3} maxLength={2000} value={field.description} onChange={event => updateField(field.id, {description: event.target.value})}/></label>
              {field.quote && <div className="field-quote"><Link2 size={16}/><div><q>{field.quote}</q><button type="button" onClick={() => setMobileTab('source')}>View supporting source <ArrowRight size={14}/></button></div></div>}
              <div className="review-field-pair"><label className="capture-label">Amount ({field.currency})<span className="label-optional">{field.kind === 'refund' ? 'Required for refunds' : 'Optional'}</span><input inputMode="decimal" value={field.amount} onChange={event => updateField(field.id, {amount: event.target.value})}/>{supportingFragment(field, 'amount') && <span className="field-source-fragment">“{supportingFragment(field, 'amount')}”</span>}</label><label className="capture-label">Confirmed deadline<span className="label-optional">Leave unset if unclear</span><input type="date" value={field.deadline} onChange={event => updateField(field.id, {deadline: event.target.value})}/>{supportingFragment(field, 'deadline') && <span className="field-source-fragment">“{supportingFragment(field, 'deadline')}”</span>}</label></div>
              <p className="deadline-explanation"><CircleAlert size={17}/><span>{field.warnings.join(' ')} {deadlineSummary(field)}</span></p>
            </fieldset>
          </section>;
        })}
        {hasRevision && <label className="capture-label communication-reason">Why does this replace the earlier promise?<textarea rows={3} maxLength={2000} value={reason} onChange={event => {setReason(event.target.value); setConfirmed(false);}} placeholder="Explain the link between the two messages."/>{!workspace.isMock && <span className="capture-meta">This explanation stays in your current review; the backend review contract stores the confirmed terms and source links.</span>}</label>}
        <label className="capture-check confirm-facts"><input type="checkbox" checked={confirmed} onChange={event => setConfirmed(event.target.checked)}/><span>I reviewed the selected promises, their source and how they relate to the earlier record.</span></label>
        <Button type="submit" disabled={blocked || !confirmed || !selected.length}><Check size={18}/> Confirm selected promises</Button>
      </fieldset></form> : <section className="communication-no-promise"><FileText size={30}/><h2>No new promise to confirm.</h2><p>Keep the message with the case. Its existing deadline and outcome stay unchanged.</p></section>}
      <section className="communication-evidence-only"><h2>Keep the words, without changing the promise.</h2><p>{fields.length ? 'Use this when the wording doesn’t clearly replace or add a promise.' : 'A progress update can still belong in the story.'}</p><fieldset disabled={busy}><label className="capture-check"><input type="checkbox" checked={claim} onChange={event => setClaim(event.target.checked)}/><span>Company claims fulfilment. I have not confirmed receipt.</span></label><label className="capture-label">Your note<span className="label-optional">Optional</span><textarea rows={3} maxLength={2000} value={note} onChange={event => setNote(event.target.value)} placeholder="What should you remember about this update?"/></label>{!workspace.isMock && <p className="capture-meta">The original file is stored. Notes and claim labels are local demo features until the backend supports them.</p>}<Button type="button" variant="secondary" disabled={blocked} onClick={() => void saveEvidence()}>Keep as evidence only <ArrowRight size={17}/></Button></fieldset><p className="capture-meta">A company claim never closes this case. Confirm receipt through Record outcome.</p></section>
      </div></div>
    </>}
  </section>;
}
