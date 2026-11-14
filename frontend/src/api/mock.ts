import type { CaseDetail } from './types';
import { createMockApi } from './mock-mutations';
import { mapCaseRow, type WorkspaceSnapshot } from './mapper';
import { dayInIndia } from './capture-validation';
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
original.extraction_id=uuid(199);
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
const createdCases: CaseDetail[] = [];
export async function loadMockWorkspace(): Promise<WorkspaceSnapshot> {
  const {cases:listed}=await mockApi.listCases();
  const details=await Promise.all(listed.map(c=>mockApi.getCase(c.id)));
  const cases = details.filter(detail => detail.commitments.length > 0 && !mockApi.getCaseExtras(detail.case.id).archived).map(detail => mockCaseRow(detail));
  return structuredClone({cases, asOf: MOCK_TODAY, timezone: 'Asia/Kolkata', demo: true});
}
export function mockCaseRow(detail:CaseDetail) {
    const active = detail.commitments.filter(c => c.status === 'active');
    const day = dayInIndia;
    const dates = active.map(c => c.due_at).filter((v): v is string => v !== null).sort();
    const status = detail.case.status === 'resolved' ? 'Resolved' : !dates.length ? 'Needs a date' : dates.some(d => day(d) < MOCK_TODAY) ? 'Overdue' : dates.some(d => day(d) === MOCK_TODAY) ? 'Due today' : 'Active';
    const row=mapCaseRow(detail,status);const meta=mockApi.getCaseExtras(detail.case.id);
    return {...row,inrAmountMinor:detail.case.status!=='resolved' && row.inrAmountMinor!=null ? Math.max(0,row.inrAmountMinor-meta.receivedMinor) : row.inrAmountMinor,amountMinor:detail.case.status!=='resolved' && row.amountMinor!==null ? Math.max(0,row.amountMinor-meta.receivedMinor) : row.amountMinor,partial:meta.partiallyFulfilled && detail.case.status!=='resolved',demoSeed:fixtures.some(d=>d.case.id===detail.case.id)};
}
export const mockApi = createMockApi(fixtures,createdCases,MOCK_TODAY);
