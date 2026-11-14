import { Link, Route, Routes, useLocation } from 'react-router-dom';
import { useEffect } from 'react';
import { ArrowRight } from 'lucide-react';
import Landing from './pages/Landing';
import { Brand } from './components/ui';
import { WorkspaceProvider } from './state/Workspace';
import WorkspaceLayout from './components/workspace/WorkspaceLayout';
import Overview from './pages/Overview';
import Cases from './pages/Cases';
import { CaseSummary, CaptureCheckpoint, ReservedWorkspacePage, WorkspaceHelp } from './pages/WorkspaceSupporting';
function NotFound() {return <main className="foundation-page"><Brand/><div className="foundation-body"><span className="mono">404 / PAGE NOT FOUND</span><h1>This page isn’t on the record.</h1><Link to="/" className="button button-primary">Back to Bindr <ArrowRight size={16}/></Link></div></main>;}
export default function App() {
  const location = useLocation();
  useEffect(() => {window.scrollTo(0, 0); if (!location.pathname.startsWith('/app')) document.title = "Bindr — Keep companies' promises on record.";}, [location.pathname]);
  return <Routes><Route path="/" element={<Landing/>}/><Route path="/app" element={<WorkspaceProvider><WorkspaceLayout/></WorkspaceProvider>}>
    <Route index element={<Overview/>}/><Route path="cases" element={<Cases/>}/><Route path="cases/:caseId" element={<CaseSummary/>}/>
    <Route path="upload" element={<CaptureCheckpoint/>}/><Route path="evidence" element={<ReservedWorkspacePage kind="evidence"/>}/>
    <Route path="settings" element={<ReservedWorkspacePage kind="settings"/>}/><Route path="help" element={<WorkspaceHelp/>}/>
    <Route path="*" element={<NotFound/>}/>
  </Route><Route path="*" element={<NotFound/>}/></Routes>;
}
