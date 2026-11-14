import type { CaseDetail } from './types';
import type { Status } from '../components/ui';
export interface CaseRow {
  partial?:boolean; multipleCurrencies?:boolean; inrAmountMinor?:number|null;
  demoSeed?: boolean; id: string; company: string; title: string; status: Status; version: number;
  amountMinor: number | null; currency: string | null; dueAt: string | null;
  revisionCount: number; evidenceCount: number; resolvedAt: string | null;
}
export interface WorkspaceSnapshot { cases: CaseRow[]; asOf: string | null; timezone: string; demo: boolean }
// Single API -> UI boundary. Do not infer overdue from the browser clock.
export function mapCase(detail: CaseDetail) {
  const active = detail.commitments.filter(c => c.status === 'active');
  const latest = active.at(-1) || detail.commitments.at(-1);
  return {id: detail.case.id, company: detail.case.merchant_name, title: detail.case.title, status: detail.case.status, version: detail.case.version, amountMinor: latest?.amount_minor ?? null, currency: latest?.currency ?? null, dueAt: latest?.due_at ?? null, commitments: detail.commitments, evidence: detail.evidence};
}
export function mapCaseRow(detail: CaseDetail, displayStatus?: Status): CaseRow {
  const mapped = mapCase(detail);
  const active = detail.commitments.filter(c => c.status === 'active');
  const dueAt = active.map(c => c.due_at).filter((d): d is string => d !== null).sort()[0] ?? mapped.dueAt;
  const monetary = (detail.case.status === 'resolved' ? detail.commitments.filter(c => c.status === 'fulfilled') : active).filter(c => c.currency !== null && c.amount_minor !== null);
  const currencies = [...new Set(monetary.map(c=>c.currency!))];
  const multipleCurrencies = currencies.length > 1;
  // Only sum current reviewed commitments. Superseded promises never inflate totals.
  const amountMinor = monetary.length && !multipleCurrencies ? monetary.reduce((sum, c) => sum + c.amount_minor!, 0) : null;
  return {id: mapped.id, company: mapped.company, title: mapped.title, version: mapped.version,
    status: displayStatus ?? (mapped.status === 'resolved' ? 'Resolved' : mapped.status === 'overdue' ? 'Overdue' : !detail.commitments.length ? 'Needs review' : active.length && active.every(c => c.due_at === null) ? 'Needs a date' : 'Active'),
    amountMinor, currency: amountMinor === null ? null : currencies[0], multipleCurrencies, inrAmountMinor:monetary.some(c=>c.currency==='INR') ? monetary.filter(c=>c.currency==='INR').reduce((sum,c)=>sum+c.amount_minor!,0) : null, dueAt,
    revisionCount: detail.commitments.filter(c => c.supersedes_id !== null).length,
    evidenceCount: detail.evidence.length, resolvedAt: detail.case.resolved_at};
}
