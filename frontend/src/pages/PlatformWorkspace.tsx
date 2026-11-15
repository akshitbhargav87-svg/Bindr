import {useEffect,useState} from 'react';
import {Link} from 'react-router-dom';
import {PlatformClient,platformSnapshot} from '../api/platform';
import {snapshot,type CaseSnapshot} from '../api/v2';
import {formatAuthoritativeMoney} from '../api/workflow';
import '../workflow.css';
const client=new PlatformClient();
export default function PlatformWorkspace(){
  const [cases,setCases]=useState<CaseSnapshot[]|null>(null),[error,setError]=useState('');
  useEffect(()=>{let active=true;void client.request('/workspace',v=>{const envelope=v as {cases:unknown[]};if(!Array.isArray(envelope.cases))throw new Error('Invalid workspace response.');return envelope.cases.map(v=>snapshot(platformSnapshot(v)));}).then(v=>{if(active)setCases(v);}).catch(e=>{if(active)setError(e.message);});return()=>{active=false;};},[]);
  return <section className="workflow"><h1>Your promises and receipts</h1><Link className="button button-primary" to="/app/capture-v2">Capture a new promise</Link><p>Each case shows authoritative server balances by currency. Earlier v1 facts stay available in the original case view and are not silently combined with the v2 receipt ledger.</p>{error && <p role="alert">{error}</p>}{!cases && !error && <p role="status">Loading case records…</p>}{cases?.map(c=><article className="workflow-obligation" key={c.id}><h2><Link to={`/app/cases/${encodeURIComponent(c.id)}/workflow`}>{c.merchant_name} · {c.title}</Link></h2><p>{c.projection.status} · as of {c.projection.as_of}</p>{c.projection.money_by_currency.map(m=><p key={m.currency}>{formatAuthoritativeMoney(m)} outstanding</p>)}<p>{c.obligations.length} obligations · {c.legacy_commitments?.length ?? 0} earlier v1 promises</p><Link to={`/app/cases/${encodeURIComponent(c.id)}`}>Original record and legacy complaint drafts</Link></article>)}{cases?.length===0 && <p>No cases yet. Start with an original company message.</p>}</section>;
}
