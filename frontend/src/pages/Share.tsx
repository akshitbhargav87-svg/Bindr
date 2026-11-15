import {useEffect,useRef,useState} from 'react';
import {useNavigate} from 'react-router-dom';
import {useCapture} from '../state/Capture';
import {validateFile} from '../api/capture-validation';
import {Button} from '../components/ui';
export default function Share(){
  const capture=useCapture(),navigate=useNavigate(),started=useRef(false);
  const [shared,setShared]=useState<{title:string;text:string;files:File[]}|null>(null);
  useEffect(()=>{if(started.current)return;started.current=true;const worker=navigator.serviceWorker?.controller;if(!worker)return;const channel=new MessageChannel();channel.port1.onmessage=e=>{if(e.data)setShared(e.data);channel.port1.close();};worker.postMessage({type:'bindr:take-share'},[channel.port2]);},[]);
  return <section className="workflow"><h1>Review shared content</h1><p>Choose the company and communication date before extraction. Sharing does not confirm a promise.</p><blockquote>{shared?.text || 'No shared text. Use upload or paste if the share handoff expired or this browser does not support it.'}</blockquote>{shared?.files.map((f,i)=><p key={i}>{f.name} · {f.size} bytes {validateFile(f,false)}</p>)}<Button disabled={!shared} onClick={()=>{if(!shared)return;if((capture.session.text || capture.session.sources.length) && !confirm('Replace the unsaved capture in this tab?'))return;capture.reset();capture.setSession(s=>({...s,tab:shared.files.length ? 'upload' : 'paste',title:shared.title,text:shared.text,sources:shared.files.map(file=>({key:crypto.randomUUID(),file,communicationDate:'',error:validateFile(file,false)}))}));setShared(null);navigate('/app/upload');}}>Continue to capture</Button><p>Unsubmitted content stays in this tab's memory. Reattach files after a full tab or process loss.</p><Button variant="secondary" onClick={()=>navigate('/app/upload')}>Upload or paste instead</Button></section>;
}
