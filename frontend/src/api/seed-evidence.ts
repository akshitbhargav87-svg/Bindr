import type { CaseDetail } from './types';
/** Synthetic seed originals, distinct from user files. No reconstructed live evidence. */
export async function prepareSeedEvidence(seed:CaseDetail[], register:(id:string,file:File,text:string,date:string)=>void) {
  for(const [index,detail] of seed.entries()) {
    for(const [sourceIndex,evidence] of detail.evidence.entries()) {
      const quote=index===0 ? sourceIndex===0 ? 'We will refund INR 4999 for the returned headphones within 5 business days.' : 'Your refund will now be completed within another 3 business days.'
        : index===1 ? 'Your replacement keyboard will be delivered by 14 November 2026.'
        : index===2 ? 'We will credit INR 799 by 20 November 2026 for the service outage.'
        : index===3 ? 'Your delayed parcel will arrive by 18 November 2026.'
        : 'Your refund of INR 2199 has been sent.';
      const text=`${detail.case.merchant_name} Support\n\n${quote}\n\nThank you,\n${detail.case.merchant_name} Customer Support`;
      evidence.filename=evidence.filename.replace(/\.pdf$/i,'.txt');evidence.media_type='text/plain';
      const file=new File([text],evidence.filename,{type:'text/plain'});evidence.size_bytes=file.size;
      evidence.sha256=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',await file.arrayBuffer()))).map(n=>n.toString(16).padStart(2,'0')).join('');
      register(evidence.id,file,text,evidence.created_at.slice(0,10));
      const commitment=detail.commitments[index===0 ? sourceIndex : 0];
      if(!commitment)continue;
      const {kind,description,amount_minor,currency,due_at}=commitment;
      detail.extractions.push({id:commitment.extraction_id,case_id:detail.case.id,evidence_ids:[evidence.id],status:'reviewed',candidates:[{candidate_id:commitment.candidate_id,terms:{kind,description,amount_minor,currency,due_at},sources:[{evidence_id:evidence.id,quote}],confidence:0,warnings:[],revision:{relation:commitment.supersedes_id ? 'revision' : 'new',supersedes_id:commitment.supersedes_id,reason:'User-confirmed sample commitment.'}}],reviewed_commitment_ids:[commitment.id],created_at:commitment.created_at});
    }
  }
}
