import { useEffect } from 'react';
import { Link, NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom';
import { ArrowUpRight, Bell, CalendarClock, ChevronDown, CircleHelp, FilePenLine, Files, FolderOpen, LayoutGrid, Plus, Settings, WifiOff } from 'lucide-react';
import { Brand, Button } from '../ui';
import { useWorkspace, type DemoView } from '../../state/Workspace';
import { date } from '../../lib/format';
import { useAuth } from '../../state/Auth';
const nav = [
  {to: '/app', label: 'Overview', Icon: LayoutGrid, end: true},
  {to: '/app/cases', label: 'Cases', Icon: FolderOpen},
  {to: '/app/evidence', label: 'Evidence', Icon: Files},
  {to: '/app/settings', label: 'Settings', Icon: Settings},
];
const tools=[{to:'/app/agenda',label:'Deadlines',Icon:CalendarClock},{to:'/app/activity',label:'Activity',Icon:Bell},{to:'/app/drafts',label:'Drafts',Icon:FilePenLine}];
export default function WorkspaceLayout() {
  const account=useAuth(); const workspace = useWorkspace(); const location = useLocation(); const navigate = useNavigate();
  const path = location.pathname;
  const title = path === '/app' || path === '/app/' ? 'Overview' : path==='/app/agenda' ? 'Deadline agenda' : path==='/app/activity' ? 'Activity' : path.endsWith('/complaint') ? 'Complaint draft' : path==='/app/drafts' ? 'Saved drafts' : path.endsWith('/update') ? 'Add communication' : path.startsWith('/app/cases/') ? 'Case detail' : path.startsWith('/app/cases') ? 'All cases' : path.startsWith('/app/archived') ? 'Archived cases' : path.startsWith('/app/review') ? 'Review promise' : path.startsWith('/app/upload') ? 'Add a promise' : path.startsWith('/app/evidence') ? 'Evidence' : path.startsWith('/app/settings') ? 'Settings' : 'Help';
  useEffect(() => {document.title = `${title} · Bindr`;const frame=requestAnimationFrame(()=>document.getElementById('workspace-main')?.focus({preventScroll:true}));return()=>cancelAnimationFrame(frame);}, [title,path]);
  const cases = workspace.data?.cases ?? [];
  return <div className="workspace">
    <a className="skip-link" href="#workspace-main">Skip to content</a>
    <aside className="workspace-sidebar"><Link to="/" aria-label="Bindr home" className="sidebar-brand"><Brand/></Link>
      <div className="workspace-label"><span>Your workspace<small>Personal</small></span></div>
      <Link to="/app/upload" className="button button-primary add-promise"><Plus size={18}/> Add a promise</Link>
      <nav aria-label="Workspace navigation">{nav.map(({to, label, Icon, end}) => <NavLink key={to} to={to} end={end} className={({isActive}) => `sidebar-link ${isActive || label==='Cases' && path==='/app/archived' ? 'is-active' : ''}`}><Icon size={20}/><span>{label === 'Cases' ? 'All cases' : label}</span>{label === 'Cases' && cases.length > 0 && <span className="nav-count">{cases.length}</span>}</NavLink>)}{tools.slice(0,2).map(({to,label,Icon})=><NavLink to={to} key={to} className={({isActive})=>`sidebar-link ${isActive ? 'is-active' : ''}`}><Icon size={20}/>{label}</NavLink>)}</nav>
      <div className="sidebar-bottom"><NavLink to="/app/drafts" className={({isActive})=>`sidebar-link ${isActive ? 'is-active' : ''}`}><FilePenLine size={19}/>Complaint drafts</NavLink><NavLink to="/app/help" className="sidebar-link"><CircleHelp size={19}/> Help & definitions</NavLink><Link to="/" className="sidebar-home">Back to Bindr <ArrowUpRight size={16}/></Link></div>
    </aside>
    <div className="workspace-body"><header className="workspace-topbar"><Link className="mobile-workspace-brand" to="/" aria-label="Bindr home"><Brand/></Link><span className="workspace-location">Your workspace <span>/</span> <strong>{title}</strong></span><div className="topbar-actions">{account.info && <Link to="/app/settings" className="account-avatar" aria-label="Account and security settings"><span>{(account.info.account.display_name || account.info.account.email).slice(0,1).toUpperCase()}</span><strong>{account.info.account.display_name || account.info.account.email}</strong></Link>}
      {workspace.data?.asOf && <span className="workspace-date">{date(workspace.data.asOf)}</span>}
      {workspace.isMock && <details className="demo-menu"><summary>Demo workspace <ChevronDown size={15}/></summary><div className="demo-popover"><p>Fictional cases · fixed demo date. Added records stay in this tab until reload.</p><label htmlFor="demo-view">Workspace view</label><select id="demo-view" value={workspace.view} onChange={e => workspace.chooseView(e.target.value as DemoView)}><option value="sample">Sample cases</option><option value="empty">Empty workspace</option><option value="offline">Connection lost</option><option value="error">Load error</option></select><Button variant="secondary" onClick={e => {workspace.showIntro(); e.currentTarget.closest('details')?.removeAttribute('open'); navigate('/app');}}>Show introduction</Button></div></details>}
    </div></header>
    <nav className="workspace-mobile-tools" aria-label="More workspace views">{tools.map(({to,label,Icon})=><NavLink to={to} key={to} className={({isActive})=>isActive ? 'is-active' : ''}><Icon size={18}/>{label}</NavLink>)}</nav>
    {workspace.offline && <div className="connection-banner" role="status"><WifiOff size={18}/><div><strong>Connection lost.</strong> {workspace.data ? 'Showing your last loaded records. New changes need a connection.' : 'Reconnect to load your workspace.'}</div>{workspace.isMock && workspace.online && workspace.view === 'offline' && <Button variant="text" onClick={() => workspace.chooseView('sample')}>Reconnect</Button>}</div>}
    <main id="workspace-main" className="workspace-main" tabIndex={-1} key={path}><Outlet/></main>
    </div>
    <nav className="workspace-bottom-nav" aria-label="Mobile workspace navigation">{nav.map(({to, label, Icon, end}) => <NavLink key={to} to={to} end={end} className={({isActive}) => isActive ? 'is-active' : ''}><Icon size={21}/><span>{label}</span></NavLink>)}</nav>
  </div>;
}
