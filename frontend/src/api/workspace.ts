import { httpApi } from './http';
import { mapCaseRow, type CaseRow, type WorkspaceSnapshot } from './mapper';

/** Existing contract reads only. No inferred browser-clock status or new endpoint. */
export async function loadHttpWorkspace(): Promise<WorkspaceSnapshot> {
  const {cases} = await httpApi.listCases();
  // GAP: list omits amounts/deadlines; bounded detail reads supply the small MVP list.
  const rows: CaseRow[] = [];
  let next = 0;
  await Promise.all(Array.from({length: Math.min(4, cases.length)}, async () => {
    while (next < cases.length) {
      const item = cases[next++];
      const detail = await httpApi.getCase(item.id);
      // Unconfirmed records stay reachable after reload; they never enter promise totals.
      rows.push(mapCaseRow(detail));
    }
  }));
  const order = new Map(cases.map((c, i) => [c.id, i]));
  rows.sort((a, b) => order.get(a.id)! - order.get(b.id)!);
  // GAP: API lacks reference date, timezone and Due today status. Keep server status;
  // timezone follows the integration proposal. Do not guess "today" in UI components.
  return {cases: rows, asOf: null, timezone: 'Asia/Kolkata', demo: false};
}
