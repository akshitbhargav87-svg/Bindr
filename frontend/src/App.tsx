import { Link, Route, Routes, useLocation } from 'react-router-dom';
import { useEffect,lazy,Suspense } from 'react';
import { ArrowRight } from 'lucide-react';
import Landing from './pages/Landing';
import { Brand } from './components/ui';
import { WorkspaceProvider } from './state/Workspace';
import WorkspaceLayout from './components/workspace/WorkspaceLayout';
import Overview from './pages/Overview';
import Cases from './pages/Cases';
import { WorkspaceHelp } from './pages/WorkspaceSupporting';
import CaseDetail from './pages/CaseDetail';
import CaseCommunication from './pages/CaseCommunication';
import EvidenceLibrary,{ArchivedCases} from './pages/EvidenceLibrary';
import Capture from './pages/Capture';
import { AccountCaptureProvider } from './state/CaptureRecovery';
import { ComplaintsProvider } from './state/Complaints';
import Complaint,{ComplaintDrafts} from './pages/Complaint';
import { PreferencesProvider } from './state/Preferences';
const Verifier=lazy(()=>import('./pages/Verifier'));
const IntelligenceCapture=lazy(()=>import('./pages/IntelligenceCapture'));
const SharePage=lazy(()=>import('./pages/Share'));
const WorkflowPage=lazy(()=>import('./pages/Workflow'));
const Settings=lazy(()=>import('./pages/Settings'));
import { Activity,Agenda } from './pages/Planning';
import './auth.css';
import { AuthProvider,AccountGate,useAuth } from './state/Auth';
const AuthPage=lazy(()=>import('./pages/Auth'));
function NotFound() {return <main className="foundation-page"><Brand/><div className="foundation-body"><span className="mono">404 / PAGE NOT FOUND</span><h1>This page isn’t on the record.</h1><Link to="/" className="button button-primary">Back to Bindr <ArrowRight size={16}/></Link></div></main>;}
function AccountRoutes(){const auth=useAuth();return <PreferencesProvider key={auth.info?.account.id ?? auth.status}><ComplaintsProvider><Routes><Route path="/" element={<Landing/>}/><Route path="/verify" element={<Verifier/>}/><Route path="/login" element={<AuthPage/>}/><Route path="/register" element={<AuthPage/>}/><Route path="/forgot-password" element={<AuthPage/>}/><Route path="/auth/action" element={<AuthPage/>}/><Route element={<AccountGate/>}><Route path="/app" element={<WorkspaceProvider><WorkspaceLayout/></WorkspaceProvider>}>
    <Route path="cases/:caseId/workflow" element={<WorkflowPage/>}/><Route path="cases/:caseId/complaint" element={<Complaint/>}/><Route path="drafts" element={<ComplaintDrafts/>}/>
    <Route index element={<Overview/>}/><Route path="cases" element={<Cases/>}/><Route path="cases/:caseId" element={<CaseDetail/>}/><Route path="cases/:caseId/update" element={<CaseCommunication/>}/><Route path="archived" element={<ArchivedCases/>}/>
    <Route path="capture-v2" element={<IntelligenceCapture/>}/><Route path="share" element={<SharePage/>}/><Route path="upload" element={<Capture/>}/><Route path="review" element={<Capture/>}/><Route path="evidence" element={<EvidenceLibrary/>}/>
    <Route path="agenda" element={<Agenda/>}/><Route path="activity" element={<Activity/>}/><Route path="settings" element={<Settings/>}/><Route path="help" element={<WorkspaceHelp/>}/>
    <Route path="*" element={<NotFound/>}/>
  </Route></Route><Route path="*" element={<NotFound/>}/></Routes></ComplaintsProvider></PreferencesProvider>;}
export default function App() {
  const location = useLocation();
  useEffect(() => {window.scrollTo(0, 0); if (!location.pathname.startsWith('/app')) document.title = "Bindr — Keep companies' promises on record.";}, [location.pathname]);
  return <AuthProvider><Suspense fallback={<main className="auth-loading" role="status">Opening Bindr…</main>}><AccountCaptureProvider><AccountRoutes/></AccountCaptureProvider></Suspense></AuthProvider>;
}
