// API contract v1, feature/integration @ 70f2db0. Server objects stay snake_case.
export interface Case { id: string; title: string; merchant_name: string; status: 'open' | 'overdue' | 'resolved'; version: number; resolution_note: string | null; resolved_at: string | null; created_at: string }
export interface Evidence { id: string; case_id: string; filename: string; media_type: string; size_bytes: number; sha256: string; created_at: string; download_path: string }
export interface Terms { kind: 'refund' | 'replacement' | 'service' | 'other'; description: string; amount_minor: number | null; currency: string | null; due_at: string | null }
export interface Commitment extends Terms { id: string; case_id: string; extraction_id: string; candidate_id: string; status: 'active' | 'superseded' | 'fulfilled'; supersedes_id: string | null; evidence_ids: string[]; reviewed_at: string; created_at: string }
export interface Candidate { candidate_id: string; terms: Terms; sources: {evidence_id: string; quote: string}[]; confidence: number; warnings: string[]; revision: {relation: 'new' | 'revision' | 'uncertain'; supersedes_id: string | null; reason: string} }
export interface Extraction { id: string; case_id: string; evidence_ids: string[]; status: 'pending_review' | 'reviewed' | 'rejected'; candidates: Candidate[]; reviewed_commitment_ids: string[]; created_at: string }
export interface CaseDetail { case: Case; evidence: Evidence[]; commitments: Commitment[]; extractions: Extraction[] }
export interface ReviewRequest { expected_version: number; decision: 'approve' | 'reject'; items: {candidate_id: string; action: 'new' | 'revision'; supersedes_id: string | null; terms: Terms; evidence_ids: string[]}[] }
export interface Draft { subject: string; body: string; evidence_ids: string[] }
export interface ApiErrorBody { code: string; message: string; details: {field: string; message: string}[]; request_id: string }
export class ApiError extends Error { constructor(public status: number, public error: ApiErrorBody) {super(error.message);} }
export interface BindrApi {
  listCases(): Promise<{cases: Case[]}>;
  getCase(id: string): Promise<CaseDetail>;
  createCase(data: {title: string; merchant_name: string}): Promise<{case: Case}>;
  uploadEvidence(id: string, file: File, version: number): Promise<{evidence: Evidence; case_version: number}>;
  extract(id: string, evidence_ids: string[], version: number): Promise<{extraction: Extraction; case_version: number}>;
  review(id: string, extractionId: string, data: ReviewRequest): Promise<{extraction: Extraction; commitments: Commitment[]; case_version: number}>;
  resolve(id: string, version: number, note: string): Promise<{case: Case}>;
  complaint(id: string, version: number, remedy: string): Promise<{draft: Draft; case_version: number}>;
}
