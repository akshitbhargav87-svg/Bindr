import { useEffect, useState } from 'react';
import { FileText, ImageIcon, Link2 } from 'lucide-react';
import type { CaptureSource as Source } from '../../api/capture-model';
import { date } from '../../lib/format';
export default function CaptureSource({sources, selected, select}:{sources:Source[];selected:number;select:(index:number)=>void}) {
  const source=sources[selected] ?? sources[0];
  const [url,setUrl]=useState('');const [text,setText]=useState('');
  useEffect(()=>{
    if(!source){setUrl('');setText('');return;}
    const objectUrl=URL.createObjectURL(source.file);setUrl(objectUrl);setText('');let live=true;
    if(source.file.type==='text/plain') void source.file.text().then(value=>{if(live)setText(value);}).catch(()=>{if(live)setText('This file could not be read. Return to capture to replace it or paste its text.');});
    return()=>{live=false;URL.revokeObjectURL(objectUrl);};
  },[source]);
  return <section className="capture-source-panel" aria-label="Original source"><div className="source-panel-heading"><h2>The original words.</h2><Link2 size={20}/></div>
    {sources.length>1 && <label className="capture-label">Source file<select value={Math.min(selected,sources.length-1)} onChange={e=>select(Number(e.target.value))}>{sources.map((item,index)=><option key={item.key} value={index}>{item.file.name}</option>)}</select></label>}
    {source ? <><div className="source-file-meta"><FileText size={18}/><strong>{source.file.name}</strong></div><p className="source-date">{source.communicationDate ? `Communication: ${date(source.communicationDate)}` : 'Communication date not supplied'}</p>
      {source.file.type==='text/plain' ? <pre className="source-message">{text || 'Reading the source…'}</pre> : source.file.type.startsWith('image/') ? <div className="source-image">{url && <img src={url} alt={`Original evidence: ${source.file.name}`}/>}</div> : <div className="source-pdf"><FileText size={34}/><h3>Original PDF</h3><p>Read the source beside your review.</p>{url && <object className="source-pdf-document" data={url} type="application/pdf" aria-label={`Original PDF: ${source.file.name}`}><p>Use Open PDF to view this source in your browser.</p></object>}{url && <a className="button button-secondary" href={url} target="_blank" rel="noreferrer">Open PDF</a>}</div>}
    </> : <div className="source-missing"><ImageIcon size={28}/><p>The original file is no longer available in this tab. Return to capture and attach it again.</p></div>}
  </section>;
}
