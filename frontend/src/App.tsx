import { Link, Route, Routes, useLocation } from 'react-router-dom';
import { useEffect } from 'react';
import { ArrowLeft, ArrowRight, Construction } from 'lucide-react';
import Landing from './pages/Landing';
import { Alert, Brand } from './components/ui';
import { isMock } from './api';
function AppFoundation() {
  const upload = useLocation().pathname === '/app/upload';
  return <main className="foundation-page"><Link to="/" aria-label="Bindr home"><Brand/></Link><div className="foundation-body"><span className="eyebrow">PHASE 1 / APP FOUNDATION</span><Construction size={32}/><h1>{upload ? 'Your next promise starts here.' : 'Your workspace is taking shape.'}</h1><p>The landing page and frontend foundation are ready. {upload ? 'Evidence capture and confirmation arrive in Phase 3.' : 'The case dashboard arrives in Phase 2.'}</p><Alert>This route is a build checkpoint. No files have been uploaded and no promises have been saved.</Alert><span className="mode-label mono">ADAPTER: {isMock ? 'SYNTHETIC DEMO' : 'HTTP / FASTAPI'}</span><Link to="/" className="button button-secondary"><ArrowLeft size={16}/> Back to Bindr</Link></div></main>;
}
function NotFound() {return <main className="foundation-page"><Brand/><div className="foundation-body"><span className="mono">404 / PAGE NOT FOUND</span><h1>This page isn’t on the record.</h1><Link to="/" className="button button-primary">Back to Bindr <ArrowRight size={16}/></Link></div></main>;}
export default function App() {const location = useLocation();useEffect(() => {window.scrollTo(0, 0);}, [location.pathname]);return <Routes><Route path="/" element={<Landing/>}/><Route path="/app/*" element={<AppFoundation/>}/><Route path="*" element={<NotFound/>}/></Routes>;}
