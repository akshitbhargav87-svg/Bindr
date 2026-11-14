import { useEffect, useRef, useState } from 'react';
import { ArrowDown, ArrowUpRight, Check, ChevronRight, FileText, History, Link2, Mail, Paperclip } from 'lucide-react';
import { StatusLabel } from './ui';
export default function ProductPreview() {
  const [source, setSource] = useState<'original' | 'revision'>('revision');
  const timeline = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
    let frame = 0;
    const update = () => {
      if (frame) return;
      frame = requestAnimationFrame(() => {
        const element = timeline.current;
        if (element) {
          const rect = element.getBoundingClientRect();
          const progress = Math.min(1, Math.max(0, (window.innerHeight * 0.78 - rect.top) / rect.height));
          element.style.setProperty('--timeline-progress', String(progress));
        }
        frame = 0;
      });
    };
    update(); window.addEventListener('scroll', update, {passive: true}); window.addEventListener('resize', update);
    return () => {cancelAnimationFrame(frame); window.removeEventListener('scroll', update); window.removeEventListener('resize', update);};
  }, []);
  return <div className="product-preview" id="product-preview">
    <div className="preview-toolbar"><span><span className="live-dot"/> Your promise record</span></div>
    <div className="preview-layout">
      <section className="preview-case" aria-label="Example case history">
        <div className="preview-breadcrumb">All cases <ChevronRight size={12}/> <span>Refund example</span></div>
        <div className="preview-company"><span className="company-avatar"><img src="/media/flipkart.svg" alt="Flipkart" width="30" height="30"/></span><div><h3>Flipkart</h3><span>Refund for returned headphones</span></div><StatusLabel status="Overdue"/></div>
        <div className="preview-amount"><strong>₹4,999</strong><span>Awaiting your confirmation of receipt</span></div>
        <div className="preview-divider"/>
        <div className="preview-section-label"><History size={15}/> Commitment history <span>2 promises · 2 sources</span></div>
        <div className="commitment-timeline" ref={timeline}>
          <button className={`commitment-event ${source === 'original' ? 'selected' : ''}`} onClick={() => setSource('original')} aria-pressed={source === 'original'}><span className="timeline-node"/><span className="event-heading">Original promise <span>02 NOV</span></span><span className="event-description">Refund within 5 business days</span><span className="deadline-line">Due 9 Nov 2026 <span className="source-link"><Link2 size={12}/> Source 01 <ArrowUpRight size={12}/></span></span></button>
          <button className={`commitment-event ${source === 'revision' ? 'selected' : ''}`} onClick={() => setSource('revision')} aria-pressed={source === 'revision'}><span className="timeline-node"/><span className="event-heading">Revised promise <span>09 NOV</span></span><span className="event-description">“Please allow 3 more business days.”</span><span className="deadline-line">Due 12 Nov 2026 <span className="source-link"><Link2 size={12}/> Source 02 <ArrowUpRight size={12}/></span></span></button>
        </div>
        <div className="record-footnote"><Check size={13}/> Original promise preserved. Every change on record.</div>
      </section>
      <section className="preview-source" aria-label="Source evidence for selected promise">
        <div className="source-heading"><Paperclip size={16}/> Their exact words </div>
        <div className="source-tabs"><button onClick={() => setSource('original')} className={source === 'original' ? 'active' : ''} aria-pressed={source === 'original'}>Original message</button><button onClick={() => setSource('revision')} className={source === 'revision' ? 'active' : ''} aria-pressed={source === 'revision'}>Follow-up</button></div>
        <div className="email-evidence" key={source}><div className="email-icon"><Mail size={20}/></div><strong>{source === 'original' ? 'Your refund is confirmed' : 'An update on your refund'}</strong><div className="email-metadata">Flipkart Support <span>{source === 'original' ? '2' : '9'} Nov 2026</span></div><hr/><p>Hi Tushar,</p>{source === 'original' ? <p>Your return has been received. <mark>We will refund ₹4,999 within 5 business days.</mark></p> : <p>We’re sorry for the delay with your refund. <mark>Please allow 3 more business days for ₹4,999 to reach your account.</mark></p>}<p>Thank you,<br/>Flipkart Support</p><div className="email-file"><FileText size={14}/>{source === 'original' ? 'refund-confirmation.txt' : 'refund-follow-up.txt'}</div></div>
        <div className="source-verification"><Link2 size={14}/><span>Deadline timezone: Asia/Kolkata</span></div>
      </section>
    </div><div className="preview-bottom"><span><Check size={13}/> Reviewed by you</span><span><ArrowDown size={13}/> Nothing overwritten</span><span><FileText size={13}/> Ready for your next step</span></div>
  </div>;
}
