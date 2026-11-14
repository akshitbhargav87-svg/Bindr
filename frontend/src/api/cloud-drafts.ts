import { newComplaintSession } from './complaint';
import type { CaseView } from './case-model';
import type { SavedComplaint } from './complaint-model';
export interface CloudDraft {case_id:string;version:number;case_version:number;subject:string;body:string}
export function restoreCloudDraft(draft:CloudDraft,view:CaseView):SavedComplaint {
  // The stored version is only a stale flag; don't fabricate an old facts snapshot.
  const session={...newComplaintSession(view),subject:draft.subject,body:draft.body,
    snapshot:structuredClone(view),snapshotSelection:newComplaintSession(view).selection,
    usedEvidenceIds:view.detail.commitments.flatMap(c=>c.evidence_ids).filter((id,index,all)=>all.indexOf(id)===index),
    stage:'draft' as const,dirty:false,needsRefresh:view.detail.case.version!==draft.case_version};
  return {caseId:draft.case_id,company:view.row.company,title:view.row.title,subject:draft.subject,session};
}
