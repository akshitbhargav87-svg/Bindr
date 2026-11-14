import { ApiError, type BindrApi, type CaseDetail } from './types';
// Synthetic examples only. Deterministic clock belongs exclusively to this adapter.
export const MOCK_TODAY = '2026-11-14';
const examples = [
  ['NovaMart', 'Refund for returned headphones', 499900, '2026-11-12', 'overdue', 'refund'],
  ['Aster Electronics', 'Replacement for a faulty keyboard', null, '2026-11-14', 'open', 'replacement'],
  ['Loop Internet', 'Service outage credit', 79900, '2026-11-20', 'open', 'service'],
  ['Parcelwise', 'Delivery of delayed parcel', null, '2026-11-18', 'open', 'other'],
  ['Orbit Store', 'Refund for cancelled order', 219900, '2026-11-10', 'resolved', 'refund'],
] as const;
const uuid = (n: number) => `00000000-0000-4000-8000-${String(n).padStart(12, '0')}`;
const fixtures: CaseDetail[] = examples.map(([merchant_name, title, amount_minor, due, status, kind], i) => ({
  case: {id: uuid(i + 1), title, merchant_name, status, version: 1, resolution_note: status === 'resolved' ? 'Refund received in full' : null, resolved_at: status === 'resolved' ? '2026-11-10T09:00:00Z' : null, created_at: '2026-11-02T09:00:00Z'},
  evidence: [], extractions: [], commitments: [{id: uuid(100 + i), case_id: uuid(i + 1), extraction_id: uuid(200 + i), candidate_id: 'c1', kind, description: title, amount_minor, currency: amount_minor === null ? null : 'INR', due_at: `${due}T18:29:59Z`, status: status === 'resolved' ? 'fulfilled' : 'active', supersedes_id: null, evidence_ids: [], reviewed_at: '2026-11-02T09:00:00Z', created_at: '2026-11-02T09:00:00Z'}],
}));
function notBuilt(): never {throw new ApiError(501, {code: 'PHASE_NOT_IMPLEMENTED', message: 'This workflow will be connected in a later build phase.', details: [], request_id: ''});}
// Foundation supports reads. Mutation simulations arrive with their respective UI phases.
export const mockApi: BindrApi = {
  listCases: async () => ({cases: structuredClone(fixtures.map(d => d.case))}),
  getCase: async id => {const detail = fixtures.find(d => d.case.id === id); if (!detail) throw new ApiError(404, {code: 'NOT_FOUND', message: 'Case not found.', details: [], request_id: ''}); return structuredClone(detail);},
  createCase: async () => notBuilt(), uploadEvidence: async () => notBuilt(), extract: async () => notBuilt(), review: async () => notBuilt(), resolve: async () => notBuilt(), complaint: async () => notBuilt(),
};
