import type { ReactNode } from 'react';
import { Link } from 'react-router-dom';
import { ArrowRight, FileCheck2, FileText, FolderOpen, RefreshCw, WifiOff } from 'lucide-react';
import { Button } from '../ui';
import { useWorkspace } from '../../state/Workspace';

export function PageHeading({title, description, children}: {title: string; description?: string; children?: ReactNode}) {
  return <div className="workspace-heading"><div><h1>{title}</h1>{description && <p>{description}</p>}</div>{children}</div>;
}
export function AddPromise({label = 'Add a promise', to = '/app/upload'}: {label?: string; to?: string}) {return <Link to={to} className="button button-primary"><span aria-hidden="true">+</span> {label}</Link>;}
export function EmptyWorkspace({addPath = '/app/upload'}: {addPath?: string} = {}) {
  const w = useWorkspace();
  return <section className="workspace-empty"><div className="empty-record-art" aria-hidden="true"><div/><div><img src="/bindr-mark.svg" alt=""/><span/><span/><FileCheck2 size={27}/></div></div><h2>Your first promise starts here.</h2><p>Bring the message. Confirm what was promised.<br/>Keep the deadline and the proof together.</p><AddPromise label="Add your first promise" to={addPath}/>{w.isMock && <Button variant="text" onClick={() => w.chooseView('sample')}>Explore sample cases <ArrowRight size={17}/></Button>}</section>;
}
export function LoadingWorkspace() {return <div className="workspace-loading" role="status" aria-label="Loading workspace"><span className="loading-label"><RefreshCw size={18}/> Loading your records…</span><div className="skeleton-summary" aria-hidden="true"><i/><i/><i/></div><div className="skeleton-rows" aria-hidden="true">{[1,2,3,4].map(n => <div key={n}><i/><i/><i/></div>)}</div></div>;}
export function WorkspaceError() {
  const w = useWorkspace();
  return <section className="workspace-empty error-state" role="alert">{w.offline ? <WifiOff size={36}/> : <FolderOpen size={36}/>}<h2>{w.offline ? 'Let’s get you reconnected.' : 'Your records couldn’t load.'}</h2><p>{w.offline ? 'Check your internet connection, then try again. Your records have not been changed.' : w.error}</p><Button onClick={() => {if (w.isMock && (w.view === 'offline' || w.view === 'error')) w.chooseView('sample'); else void w.refresh();}}><RefreshCw size={17}/> Try again</Button></section>;
}
export function WorkspaceGate({children}: {children: ReactNode}) {
  const w = useWorkspace();
  if (w.loading && !w.data) return <LoadingWorkspace/>;
  if ((w.offline || w.error) && !w.data) return <WorkspaceError/>;
  return <>{w.error && <div className="workspace-inline-error" role="alert"><span>{w.error} Showing previously loaded records.</span><Button variant="secondary" onClick={() => {if(w.isMock && w.view === 'error') w.chooseView('sample'); else void w.refresh();}}>Retry</Button></div>}{children}</>;
}
export function Welcome() {
  const w = useWorkspace();
  return <section className="workspace-welcome"><span className="welcome-tag"><img src="/bindr-mark.svg" alt=""/> Welcome to your record.</span><h1>They made a promise.<br/><span>Let’s keep it together.</span></h1><p>Turn a company’s words into a clear case—with the original message, the deadline, and every revision in one place.</p><div className="welcome-steps">{[
    {Icon: FileText, title: 'Bring the evidence.', body: 'Start with a company message or document.'},
    {Icon: FileCheck2, title: 'Confirm the details.', body: 'Review the promise and its exact supporting words.'},
    {Icon: FolderOpen, title: 'Keep the whole story.', body: 'Track dates and outcomes without losing the original.'},
  ].map(({Icon,title,body}, i) => <div key={title}><span className="welcome-step-number">{i + 1}</span><Icon size={26}/><h2>{title}</h2><p>{body}</p></div>)}</div><div className="welcome-actions"><Button onClick={() => w.finishIntro(false)}>Start your workspace <ArrowRight size={18}/></Button>{w.isMock && <Button variant="secondary" onClick={() => w.finishIntro(true)}>Explore sample cases</Button>}</div><p className="welcome-footnote">You confirm each promise before it is tracked.{!w.isMock && ' Your account keeps your saved records available across devices.'}</p></section>;
}
