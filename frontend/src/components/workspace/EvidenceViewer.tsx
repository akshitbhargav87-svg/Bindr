import { useEffect, useId, useRef, useState } from 'react';
import { Download, ExternalLink, FileText, FolderX, LoaderCircle, RefreshCw, X } from 'lucide-react';
import { ApiError, type Evidence } from '../../api/types';
import { Button } from '../ui';
import '../../evidence-viewer.css';

interface Props {
  evidence: Evidence | null;
  quote?: string | null;
  loadFile: (evidence: Evidence) => Promise<Blob>;
  onClose: () => void;
}
interface Preview {url:string; text:string | null; mime:string}
const safeTypes = new Set(['text/plain','application/pdf','image/png','image/jpeg']);
function uploadedAt(value:string) {
  const stamp=new Date(value);
  return Number.isNaN(stamp.getTime()) ? 'Date unavailable' : `${new Intl.DateTimeFormat('en-GB',{day:'numeric',month:'short',year:'numeric',hour:'2-digit',minute:'2-digit',hourCycle:'h23',timeZone:'Asia/Kolkata'}).format(stamp)} · Asia/Kolkata`;
}
function sourceText(text:string,quote?:string|null) {
  const start=quote ? text.indexOf(quote) : -1;
  return start<0 ? text : <>{text.slice(0,start)}<mark>{text.slice(start,start+quote!.length)}</mark>{text.slice(start+quote!.length)}</>;
}

export default function EvidenceViewer({evidence,quote,loadFile,onClose}:Props) {
  const dialog=useRef<HTMLDialogElement>(null);
  const titleId=useId();
  const [preview,setPreview]=useState<Preview|null>(null);
  const [loading,setLoading]=useState(false);
  const [error,setError]=useState<string|null>(null);
  const [missing,setMissing]=useState(false);
  const [attempt,setAttempt]=useState(0);
  const isOpen=Boolean(evidence);
  useEffect(()=>{
    const element=dialog.current;
    if(!isOpen || !element)return;
    const prior=document.activeElement instanceof HTMLElement ? document.activeElement : null;
    const overflow=document.body.style.overflow;
    document.body.style.overflow='hidden';
    if(!element.open)element.showModal();
    return()=>{
      if(element.open)element.close();
      document.body.style.overflow=overflow;
      if(prior?.isConnected)prior.focus({preventScroll:true});
    };
  },[isOpen]);
  useEffect(()=>{
    if(!evidence){setPreview(null);setError(null);setLoading(false);return;}
    let live=true;let objectUrl='';
    setPreview(null);setError(null);setMissing(false);setLoading(true);
    void (async()=>{
      try {
        const blob=await loadFile(evidence);
        if(!(blob instanceof Blob) || !blob.size)throw new Error('The original file is unavailable.');
        const mime=(blob.type || evidence.media_type).split(';')[0].trim().toLowerCase();
        let text:string|null=null;
        if(mime==='text/plain')text=new TextDecoder('utf-8',{fatal:true}).decode(await blob.arrayBuffer());
        if(!live)return;
        // Preview only the allowlist. In particular, never embed HTML or SVG evidence.
        if(safeTypes.has(mime))objectUrl=URL.createObjectURL(new Blob([blob],{type:mime}));
        setPreview({url:objectUrl,text,mime});
      } catch(cause) {
        if(!live)return;
        const notFound=cause instanceof ApiError && cause.status===404 || cause instanceof Error && /unavailable|not found|missing/i.test(cause.message);
        setMissing(notFound);
        setError(notFound ? 'The original file could not be found. Its case reference is still on record.' : cause instanceof ApiError && cause.status===401 ? 'Your session is unavailable. Restore the backend session, then retry.' : cause instanceof ApiError && cause.status===403 ? 'This file could not be accessed with the current session.' : 'The original file could not be loaded. Reconnect or retry; your case has not changed.');
      } finally {if(live)setLoading(false);}
    })();
    return()=>{live=false;if(objectUrl)URL.revokeObjectURL(objectUrl);};
  },[evidence,loadFile,attempt]);
  if(!evidence)return null;
  return <dialog ref={dialog} className="evidence-viewer" aria-labelledby={titleId} onCancel={event=>{event.preventDefault();onClose();}}>
    <div className="evidence-viewer-shell">
      <header className="evidence-viewer-heading"><div><span className="evidence-viewer-label">Original evidence</span><h2 id={titleId}>{evidence.filename}</h2></div><button type="button" className="evidence-viewer-close" onClick={onClose} aria-label="Close original evidence" autoFocus><X size={22}/></button></header>
      <div className="evidence-viewer-scroll">
        {quote && <section className="evidence-linked-quote"><h3>Linked quotation</h3><q>{quote}</q>{preview?.text!==null && preview && !preview.text?.includes(quote) && <p>The linked quotation is not present in this file’s text. Check the original before relying on it.</p>}</section>}
        <section className="evidence-preview" aria-label="Original file preview" aria-busy={loading}>
          {loading ? <div className="evidence-preview-state" role="status"><LoaderCircle size={28} className="spin"/><h3>Opening the original…</h3><p>Your case stays exactly as it is.</p></div> : error ? <div className="evidence-preview-state" role="alert">{missing ? <FolderX size={32}/> : <FileText size={32}/>}<h3>{missing ? 'The original is missing.' : 'The file couldn’t load.'}</h3><p>{error}</p><Button variant="secondary" onClick={()=>setAttempt(value=>value+1)}><RefreshCw size={17}/>Retry</Button></div> : preview ? <>
            {preview.mime==='text/plain' ? <pre className="evidence-original-text">{sourceText(preview.text ?? '',quote)}</pre> : preview.mime==='image/png' || preview.mime==='image/jpeg' ? <img className="evidence-original-image" src={preview.url} alt={`Original evidence: ${evidence.filename}`}/> : preview.mime==='application/pdf' ? <object className="evidence-original-pdf" data={preview.url} type="application/pdf" aria-label={`Original PDF: ${evidence.filename}`}><p>Your browser cannot display this PDF here. Use Open original below.</p></object> : <div className="evidence-preview-state"><FileText size={32}/><h3>This file type cannot be previewed.</h3><p>Bindr previews plain text, PDF, PNG and JPEG files.</p></div>}
          </> : null}
        </section>
        {preview?.url && <div className="evidence-viewer-actions"><a className="button button-secondary" href={preview.url} target="_blank" rel="noreferrer"><ExternalLink size={17}/>Open original</a><a className="button button-secondary" href={preview.url} download={evidence.filename}><Download size={17}/>Download</a></div>}
        <details className="evidence-file-details"><summary>File details</summary><dl><div><dt>Source ID</dt><dd className="evidence-mono">{evidence.id}</dd></div><div><dt>File type</dt><dd>{evidence.media_type}</dd></div><div><dt>Size</dt><dd>{new Intl.NumberFormat('en-IN').format(evidence.size_bytes)} bytes</dd></div><div><dt>Added to case</dt><dd>{uploadedAt(evidence.created_at)}</dd></div><div><dt>SHA-256</dt><dd className="evidence-mono">{evidence.sha256}</dd></div></dl></details>
      </div>
      <footer className="evidence-viewer-footer"><Button variant="secondary" onClick={onClose}>Back to case</Button><span>Original file · read only</span></footer>
    </div>
  </dialog>;
}
