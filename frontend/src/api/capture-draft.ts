import {accountContext} from './account-context';
import {DraftAutosave,operation,type Operation} from './v2';
import type {CaptureSession} from './capture-model';
export interface CaptureDraft {id:string;version:number;text:string;metadata:{company:string;title:string;communicationDate:string};source_references:string[]}
export function captureDraft(v:unknown):CaptureDraft {const d=v as CaptureDraft;if(!d || typeof d.id!=='string' || !Number.isSafeInteger(d.version) || typeof d.text!=='string' || d.text.length>50000 || !d.metadata || typeof d.metadata.company!=='string' || typeof d.metadata.title!=='string' || typeof d.metadata.communicationDate!=='string' || !Array.isArray(d.source_references) || !d.source_references.every(v=>typeof v==='string'))throw new Error('The saved capture draft is invalid.');return d;}
/** Serialize autosaves; uncertain requests retain the exact body/key for replay. */
export class CaptureDraftController {
  private draft:CaptureDraft|null=null;
  private pending:{body:unknown;op:Operation}|null=null;
  private queue:Promise<unknown>=Promise.resolve();
  constructor(private autosave:DraftAutosave,private owner:string){}
  save(session:CaptureSession){
    const run=async()=>{
      if(accountContext().id!==this.owner)throw new Error('Reauthenticate to the same account before cloud autosave.');
      if(this.pending)await this.flush();
      const body={expected_version:this.draft?.version ?? 0,text:session.text,
        metadata:{company:session.company,title:session.title,communicationDate:session.communicationDate},source_references:session.job?.evidenceIds ?? []};
      this.pending={body,op:operation(body)};return this.flush();
    };
    const next=this.queue.then(run,run);this.queue=next.catch(()=>{});return next;
  }
  private async flush(){const pending=this.pending!;const response=await this.autosave.save(this.draft?.id ?? null,pending.body,pending.op);this.draft=captureDraft(response);this.pending=null;return this.draft;}
  current(){return this.draft;}
}
