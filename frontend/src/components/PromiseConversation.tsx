import { ArrowDown, Check, CheckCheck, Paperclip } from 'lucide-react';

export default function PromiseConversation() {
  return <div className="conversation-art" aria-label="Example refund conversation showing an original and revised promise">
    <div className="conversation-orbit" aria-hidden="true"/>
    <div className="art-doodle doodle-one" aria-hidden="true">✳</div>
    <div className="art-doodle doodle-two" aria-hidden="true">+</div>
    <div className="conversation-sequence">
      <div className="message message-original"><div className="message-sender"><span className="company-avatar"><img src="/media/flipkart.svg" alt="Flipkart" width="30" height="30"/></span><div><strong>Flipkart Support</strong><span>2 November · original promise</span></div><CheckCheck size={18}/></div><p>“We’ll refund <strong>₹4,999</strong> within<br className="bubble-break"/> 5 business days.”</p><div className="message-date"><span>Refund confirmed</span><span>Due 9 Nov</span></div></div>
      <div className="message-connector" aria-hidden="true"><span/><ArrowDown size={20}/><span/></div>
      <div className="message message-revised"><div className="message-sender"><span className="company-avatar"><img src="/media/flipkart.svg" alt="Flipkart" width="30" height="30"/></span><div><strong>Flipkart Support</strong><span>9 November · a new date</span></div><CheckCheck size={18}/></div><p>“Please allow <strong>3 more<br className="bubble-break"/> business days.</strong>”</p><div className="message-date"><span>1 revision</span><span>Now due 12 Nov</span></div></div>
      <div className="message-bindr"><div className="bindr-message-icon"><img src="/bindr-mark.svg" alt=""/></div><div><strong>The date moved.<br/>Your proof didn’t.</strong><span><Paperclip size={14}/> Both promises. One record.</span></div><span className="proof-check"><Check size={21}/></span></div>
    </div>
  </div>;
}
