import type { Candidate, CommitmentKind } from './capture-types';
import type {Operation,Proposal,Job} from './v2';
export interface V2CaptureState {caseId:string|null;version:number;evidenceIds:string[];uploadedKeys:string[];proposal:Proposal|null;job:Job|null;operations:Record<string,Operation>}
export type Scenario = 'standard' | 'multiple' | 'vague' | 'date-review' | 'no-promise' | 'duplicate' | 'ai-error' | 'save-error';
export interface CaptureSource { key: string; file: File; communicationDate: string; error: string | null }
export interface CaptureInput { company: string; title: string; sources: CaptureSource[] }
export interface CaptureJob {
  caseId: string; version: number; evidenceIds: string[]; uploadedKeys: string[];
  extractionId: string | null; candidates: Candidate[]; duplicateId: string | null;
  state: 'ready' | 'needs-reconciliation';
  pendingUpload?: {key:string;filename:string;sha256:string};
  reviewEvidenceIds?:string[];
  ignoredExtractionIds?:string[];
}
export interface ReviewFields {
  id: string; selected: boolean; kind: CommitmentKind; description: string;
  amount: string; currency: string; deadline: string; originalDueAt: string | null;
  quote: string | null; warnings: string[]; explanation: string;
}
export interface CaptureSession {
  v2?:V2CaptureState;
  tab: 'upload' | 'paste'; company: string; title: string; text: string; communicationDate: string;
  sources: CaptureSource[]; scenario: Scenario; step: 'capture' | 'processing' | 'review' | 'saved';
  job: CaptureJob | null; fields: ReviewFields[]; manual: boolean; confirmed: boolean;
  allowDuplicate: boolean; error: string | null; progress: string; savedId: string | null;
  evidenceOnly: boolean; savedDescription: string; formErrors: Record<string,string>;
  pending: boolean;
}
