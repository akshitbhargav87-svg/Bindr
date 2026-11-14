import type { CaseDetail } from './types';
// Single API -> UI boundary. Do not infer overdue from the browser clock.
export function mapCase(detail: CaseDetail) {
  const active = detail.commitments.filter(c => c.status === 'active');
  const latest = active.at(-1) || detail.commitments.at(-1);
  return {id: detail.case.id, company: detail.case.merchant_name, title: detail.case.title, status: detail.case.status, version: detail.case.version, amountMinor: latest?.amount_minor ?? null, currency: latest?.currency ?? null, dueAt: latest?.due_at ?? null, commitments: detail.commitments, evidence: detail.evidence};
}
