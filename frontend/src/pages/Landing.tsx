import { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { ArrowRight, ArrowUpRight, Check, FileCheck2, FileText, History, Link2, Menu, Minus, Plus, ScanLine, ShieldCheck, X } from 'lucide-react';
import { Brand, Button } from '../components/ui';
import ProductPreview from '../components/ProductPreview';
import PromiseConversation from '../components/PromiseConversation';
import { Reveal, useReadingProgress } from '../components/LandingMotion';
import { useAuth } from '../state/Auth';

const faqs = [
  ['What can I keep track of?', 'Refunds, replacements, deliveries, service credits, or another clear company commitment. Start with the message containing the promise, then review its details before tracking it.'],
  ['Who confirms the extracted promise?', 'You do. AI proposes fields and supporting quotations. You review the company, promise, amount and deadline before choosing Confirm & track. Unclear dates need your attention.'],
  ['What happens if the company changes the date?', 'The original promise stays on the timeline. You review the new communication and decide whether it revises the promise. Both versions remain linked to their source evidence.'],
  ['Does Bindr file complaints for me?', 'No. Bindr helps prepare an editable complaint draft using reviewed facts and evidence. You decide what to change, copy or share. Bindr does not send or file complaints.'],
  ['Does a company saying “refunded” close my case?', 'No. A company’s message is a claim. A case is resolved only after you confirm that the promise has been fulfilled.'],
];
type InfoPage = 'Privacy' | 'Terms' | 'Contact';
const info: Record<InfoPage, {title: string; paragraphs: string[]}> = {
  Privacy: {title: 'Your evidence deserves a clear explanation.', paragraphs: ['The refund conversation on this page is a sample scenario, not a report about a real transaction. Brand marks do not imply affiliation.', 'Live extraction is designed to run through the backend, which supplies selected evidence text to its configured AI provider. No AI provider credentials belong in the browser.', 'Retention, deletion and production privacy terms are not finalized. Use synthetic evidence while reviewing this build.']},
  Terms: {title: 'A record to help you take the next step.', paragraphs: ['Bindr is a consumer accountability tool under development. It is not a legal service and does not guarantee a refund, replacement or complaint outcome.', 'AI proposals need your review. A tracked promise is a record of the commitment you confirmed, not independent verification of the company’s conduct.', 'Complaint drafts are editable. Nothing is sent or filed by Bindr. Production terms will be published before a public launch.']},
  Contact: {title: 'Contact the Bindr team.', paragraphs: ['Bindr is being built for the VIHAAN X hackathon. A public support address has not been published yet.', 'For this development build, share questions or feedback directly with the team member who gave you access.']},
};
function InfoDialog({page, close}: {page: InfoPage; close: () => void}) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {const d = ref.current!; d.showModal(); const previous = document.body.style.overflow; document.body.style.overflow = 'hidden'; return () => {d.close(); document.body.style.overflow = previous;};}, []);
  return <dialog ref={ref} className="info-dialog" onCancel={close} onClick={e => {if (e.target === e.currentTarget) close();}} aria-labelledby="info-title"><div className="dialog-top"><span className="eyebrow">{page}</span><Button variant="text" onClick={close} aria-label="Close dialog"><X size={20}/></Button></div><h2 id="info-title">{info[page].title}</h2>{info[page].paragraphs.map(p => <p key={p}>{p}</p>)}<Button variant="secondary" onClick={close}>Close</Button></dialog>;
}
export default function Landing() {
  const account=useAuth();
  const [menu, setMenu] = useState(false);
  const [dialog, setDialog] = useState<InfoPage | null>(null);
  const progress = useReadingProgress();
  useEffect(() => {
    if (!menu) return;
    const closeOnEscape = (event: KeyboardEvent) => {if (event.key === 'Escape') setMenu(false);};
    document.addEventListener('keydown', closeOnEscape);
    return () => document.removeEventListener('keydown', closeOnEscape);
  }, [menu]);
  return <div className="landing">
    <a className="skip-link" href="#main">Skip to content</a>
    <div className="reading-progress" ref={progress} aria-hidden="true"/>
    <header className="site-header">
      <div className="container header-inner">
        <Link to="/" aria-label="Bindr home"><Brand/></Link>
        <nav id="mobile-menu" className={menu ? 'main-nav is-open' : 'main-nav'} aria-label="Main navigation">
          <a href="#how-it-works" onClick={() => setMenu(false)}>How it works</a>
          <a href="#your-record" onClick={() => setMenu(false)}>Why Bindr</a>
          <a href="#questions" onClick={() => setMenu(false)}>FAQs</a>
        </nav>
        <Link className="header-cta" to={account.status==='signed-out' ? '/login' : '/app'}>{account.status==='signed-out' ? 'Sign in' : 'Open workspace'} <ArrowUpRight size={18}/></Link>
        <button className="menu-toggle" aria-expanded={menu} aria-controls="mobile-menu" aria-label={menu ? 'Close menu' : 'Open menu'} onClick={() => setMenu(!menu)}>{menu ? <X/> : <Menu/>}</button>
      </div>
    </header>
    <main id="main">
      <section className="hero container">
        <div className="hero-main">
          <div className="hero-copy">
            <h1 aria-label="Keep companies' promises on record."><span className="headline-line">Keep companies'</span><span className="headline-line">promises</span><span className="headline-line headline-accent">on record.<svg viewBox="0 0 390 15" aria-hidden="true"><path d="M4 10Q180 -1 386 7"/></svg></span></h1>
            <p>The refund. The replacement. The date that moved.<br className="desktop-break"/> Keep what they promised—and the proof.</p>
            <div className="hero-actions"><Link to="/app/upload" className="button button-primary">Track a promise <ArrowRight size={20}/></Link><a href="#product-preview" className="quiet-link">See the record <ArrowRight size={19}/></a></div>
          </div>
          <PromiseConversation/>
        </div>
      </section>
      <section className="product-section" aria-labelledby="record-heading">
        <div className="container">
          <Reveal><div className="section-intro"><div><span className="section-kicker">The whole story, together.</span><h2 id="record-heading">A moving deadline shouldn’t<br/><span>mean starting from scratch.</span></h2></div><p>The original stays. The new date joins it.<br/>Every promise links back to their words.</p></div></Reveal>
          <Reveal><ProductPreview/></Reveal>
        </div>
      </section>
      <section className="how-section container" id="how-it-works">
        <Reveal><div className="section-intro"><div><span className="section-kicker">Three steps. A little less chasing.</span><h2>From “we promise”<br/>to a clear next step.</h2></div><p>Start with the message<br/>you already have.</p></div></Reveal>
        <div className="steps-grid">
          <Reveal className="step" delay={0}><article><div className="step-art capture-art"><span className="step-number">1</span><div className="capture-document"><FileText size={28}/><strong>Your refund confirmation</strong><span>Original communication</span><div className="document-lines"><i/><i/><i/></div><span className="attachment-tag"><Check size={14}/> Evidence attached</span></div><span className="floating-format">PDF</span><span className="floating-format second">Message</span></div><h3>Add the evidence.</h3><p>Bring the company’s message or document. Keep the original with its promise.</p></article></Reveal>
          <Reveal className="step" delay={100}><article><div className="step-art confirm-art"><span className="step-number">2</span><div className="confirmation-form"><span>Promised amount</span><strong>₹4,999 <Check size={19}/></strong><div/><span>Confirmed deadline</span><strong>9 Nov 2026 <Check size={19}/></strong><span className="confirmed-tag"><FileCheck2 size={16}/> Reviewed by you</span></div></div><h3>Give it your okay.</h3><p>Check the details against the exact words. You confirm what gets tracked.</p></article></Reveal>
          <Reveal className="step" delay={200}><article><div className="step-art follow-art"><span className="step-number">3</span><div className="follow-record"><div><span/><p>Original promise<small>Due 9 Nov</small></p><Check size={16}/></div><div><span/><p>Revised promise<small>Due 12 Nov</small></p><History size={16}/></div><div><span/><p>Your next step<small>All the facts, ready.</small></p><ArrowUpRight size={17}/></div></div></div><h3>Know your next step.</h3><p>Track the deadline, record the outcome, or prepare a complaint draft with evidence.</p></article></Reveal>
        </div>
      </section>
      <section className="record-section container" id="your-record">
        <Reveal className="people-visual"><figure><img className="everyday-photo" src="/media/everyday-phone.jpg" alt="A woman outdoors holding her phone" width="1000" height="667" loading="lazy"/></figure><div className="photo-note"><span className="proof-check"><Check size={21}/></span><p>One less thing<br/><strong>to keep in your head.</strong></p></div><span className="photo-spark" aria-hidden="true">✳</span></Reveal>
        <Reveal className="record-statement"><span className="section-kicker">Built around your side of the story.</span><h2>They said it.<br/><span>You kept it.</span></h2><p>A support chat here. An email there. A date that keeps moving. Bring the pieces together, without losing what was said first.</p><div className="record-principles">{[
          {Icon: Link2, title: 'Every promise has a source.', body: 'Exact words. Original files. Connected to the commitment.'},
          {Icon: History, title: 'The original stays original.', body: 'A revised date adds to the history. It never replaces it.'},
          {Icon: FileCheck2, title: 'You decide what’s fulfilled.', body: '“Refund sent” is a claim. You confirm when it arrives.'},
        ].map(({Icon, title, body}) => <div className="principle" key={title}><Icon size={22}/><div><h3>{title}</h3><p>{body}</p></div></div>)}</div><Link to="/app/upload" className="quiet-link">Start your record <ArrowRight size={18}/></Link></Reveal>
      </section>
      <section className="everyday-brands container" aria-label="Illustrative company examples">
        <Reveal><h2>A promise is a promise.<br/><span>Whoever it comes from.</span></h2><div className="brand-examples">{[
          ['flipkart', 'Flipkart', 'Shopping'], ['swiggy', 'Swiggy', 'Food & groceries'], ['uber', 'Uber', 'Travel'], ['zomato', 'Zomato', 'Food delivery'],
        ].map(([id, name, category]) => <div className={`brand-example brand-${id}`} key={id}><div className="company-brand"><img src={`/media/${id}.svg`} alt={`${name} logo`} width="40" height="40" loading="lazy"/>{id !== 'uber' && id !== 'zomato' && <span>{name}</span>}</div><span>{category}</span></div>)}</div><p className="brand-disclosure">Illustrative company examples. Bindr is independent and isn’t affiliated with these brands.</p></Reveal>
      </section>
      <section className="privacy-section"><div className="container"><Reveal className="privacy-inner"><div><span className="section-kicker"><ShieldCheck size={19}/> Evidence is personal.</span><h2>Your evidence.<br/><span>Your call.</span></h2><button className="quiet-link" onClick={() => setDialog('Privacy')}>Read the privacy note <ArrowUpRight size={18}/></button></div><div className="privacy-facts"><span><Check size={21}/> You review every extracted promise.</span><span><Check size={21}/> You decide when a case is fulfilled.</span><span><Check size={21}/> Nothing is sent or filed by Bindr.</span><p>Complaint drafts stay editable.<br/>The next step is always yours.</p></div></Reveal></div></section>
      <section className="faq-section container" id="questions"><Reveal><span className="section-kicker">Before you start.</span><h2>Good<br/><span>questions.</span></h2><p>It’s your evidence.<br/>You should know how this works.</p></Reveal><Reveal className="faq-list">{faqs.map(([q, a]) => <details key={q}><summary>{q}<Plus className="faq-plus" size={22}/><Minus className="faq-minus" size={22}/></summary><p>{a}</p></details>)}</Reveal></section>
      <section className="final-cta container"><Reveal><span className="section-kicker">The next promise, on record.</span><h2>Keep the promise.<br/><span>Keep the proof.</span></h2><div className="final-actions"><Link to="/app/upload" className="button button-primary">Track a promise <ArrowRight size={20}/></Link><p>Start with the message you already have.</p></div></Reveal><div className="cta-graphic" aria-hidden="true"><div className="cta-paper back"/><div className="cta-paper front"><img src="/bindr-mark.svg" alt=""/><span>Promise.<br/>Proof.<br/>Together.</span><Check size={26}/></div><span className="cta-star">✳</span></div></section>
    </main>
    <footer className="site-footer container"><div><Link to="/" aria-label="Bindr home"><Brand/></Link><p>Promises change. The record stays.</p></div><div className="footer-links">{(['Contact', 'Privacy', 'Terms'] as const).map(page => <button key={page} onClick={() => setDialog(page)}>{page}</button>)}</div><span className="footer-meta">Made for everyday follow-through.<br/>© {new Date().getFullYear()} Bindr</span></footer>
    {dialog && <InfoDialog page={dialog} close={() => setDialog(null)}/>}
  </div>;
}
