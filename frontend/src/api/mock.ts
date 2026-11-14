import { ApiError, type BindrApi, type CaseDetail } from './types';
import { mapCaseRow, type WorkspaceSnapshot } from './mapper';
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
// A revision appends a commitment and preserves the original terms and evidence.
const nova = fixtures[0];
const original = {...nova.commitments[0], id: uuid(99), due_at: '2026-11-09T18:29:59Z', status: 'superseded' as const, evidence_ids: [uuid(300)]};
nova.commitments[0].supersedes_id = original.id;
nova.commitments[0].evidence_ids = [uuid(300), uuid(301)];
nova.commitments[0].reviewed_at = '2026-11-09T09:00:00Z';
nova.commitments[0].created_at = '2026-11-09T09:00:00Z';
nova.commitments.unshift(original);
for (const [i, detail] of fixtures.entries()) {
  const ids = i === 0 ? [uuid(300), uuid(301)] : [uuid(310 + i)];
  detail.evidence = ids.map((id, index) => ({id, case_id: detail.case.id, filename: i === 0 ? index === 0 ? 'refund-confirmation.txt' : 'refund-follow-up.txt' : ['','replacement-email.pdf','support-chat.txt','delivery-update.pdf','refund-receipt.txt'][i], media_type: i === 1 || i === 3 ? 'application/pdf' : 'text/plain', size_bytes: 1024, sha256: 'a'.repeat(64), created_at: index === 1 ? '2026-11-09T09:00:00Z' : detail.case.created_at, download_path: `/api/v1/cases/${detail.case.id}/evidence/${id}/content`}));
  if (i !== 0) detail.commitments[0].evidence_ids = ids;
}
export async function loadMockWorkspace(): Promise<WorkspaceSnapshot> {
  const cases = fixtures.map(detail => {
    const active = detail.commitments.filter(c => c.status === 'active');
    const day = (stamp: string) => new Intl.DateTimeFormat('en-CA', {timeZone: 'Asia/Kolkata', year: 'numeric', month: '2-digit', day: '2-digit'}).format(new Date(stamp));
    const dates = active.map(c => c.due_at).filter((v): v is string => v !== null).sort();
    const status = detail.case.status === 'resolved' ? 'Resolved' : !dates.length ? 'Needs a date' : dates.some(d => day(d) < MOCK_TODAY) ? 'Overdue' : dates.some(d => day(d) === MOCK_TODAY) ? 'Due today' : 'Active';
    return mapCaseRow(detail, status);
  });
  return structuredClone({cases, asOf: MOCK_TODAY, timezone: 'Asia/Kolkata', demo: true});
}
function notBuilt(): never {throw new ApiError(501, {code: 'PHASE_NOT_IMPLEMENTED', message: 'This workflow will be connected in a later build phase.', details: [], request_id: ''});}
// Foundation supports reads. Mutation simulations arrive with their respective UI phases.
export const mockApi: BindrApi = {
  listCases: async () => ({cases: structuredClone(fixtures.map(d => d.case))}),
  getCase: async id => {const detail = fixtures.find(d => d.case.id === id); if (!detail) throw new ApiError(404, {code: 'NOT_FOUND', message: 'Case not found.', details: [], request_id: ''}); return structuredClone(detail);},
  createCase: async () => notBuilt(), uploadEvidence: async () => notBuilt(), extract: async () => notBuilt(), review: async () => notBuilt(), resolve: async () => notBuilt(), complaint: async () => notBuilt(),
};
