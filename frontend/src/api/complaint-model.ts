import type { CaseView } from './case-model';
export interface ComplaintSelection {factIds:string[];evidenceIds:string[];remedy:string}
export type ComplaintStage='setup'|'generating'|'draft'|'review'|'export'|'prepared';
export interface ComplaintSession {
  selection:ComplaintSelection;stage:ComplaintStage;snapshot:CaseView|null;
  snapshotSelection:ComplaintSelection|null;
  subject:string;body:string;usedEvidenceIds:string[];mode:'generated'|'manual';
  includeEvidence:boolean;includeHistory:boolean;exportConfirmed:boolean;
  preparedText:string|null;delivered:'copied'|'downloaded'|null;
  error:string|null;busy:boolean;needsRefresh:boolean;dirty:boolean;
}
export interface SavedComplaint {caseId:string;company:string;title:string;subject:string;session:ComplaintSession}
