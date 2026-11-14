import type { CaseRow } from '../api/mapper';
export const filters = ['All', 'Open', 'Overdue', 'Due today', 'Active', 'Resolved', 'Needs a date'] as const;
export type CaseFilter = typeof filters[number];
export function filterCases(cases: CaseRow[], query: string, status: CaseFilter): CaseRow[] {
  const needle = query.trim().toLocaleLowerCase();
  return cases.filter(c => (status === 'All' || (status === 'Open' ? c.status !== 'Resolved' : c.status === status)) && (!needle || `${c.company} ${c.title}`.toLocaleLowerCase().includes(needle)));
}
export function summarizeCases(cases: CaseRow[]) {
  const open = cases.filter(c => c.status !== 'Resolved');
  return {open: open.length, outstandingMinor: open.reduce((sum,c) => sum + (c.currency === 'INR' ? c.amountMinor ?? 0 : 0),0), overdue: open.filter(c => c.status === 'Overdue').length};
}
