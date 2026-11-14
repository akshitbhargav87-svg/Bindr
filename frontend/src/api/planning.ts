import type { WorkspaceSnapshot,CaseRow } from './mapper';
import type { CaseView } from './case-model';
import type { Preferences } from './preferences';
import { caseTimeline,listEvidence } from './case-service';
export interface AgendaGroup {key:string;label:string;cases:CaseRow[]}
export function buildAgenda(snapshot:WorkspaceSnapshot):AgendaGroup[] {
  const open=snapshot.cases.filter(c=>c.status!=='Resolved' && c.status!=='Needs review');
  const sort=(rows:CaseRow[])=>[...rows].sort((a,b)=>(a.dueAt ? Date.parse(a.dueAt) : Infinity)-(b.dueAt ? Date.parse(b.dueAt) : Infinity) || a.company.localeCompare(b.company));
  // Group by authoritative display status. Never compare a deadline with browser time.
  return [
    {key:'overdue',label:'Overdue',cases:sort(open.filter(c=>c.status==='Overdue'))},
    {key:'today',label:'Due today',cases:sort(open.filter(c=>c.status==='Due today'))},
    {key:'scheduled',label:'Confirmed dates',cases:sort(open.filter(c=>c.status!=='Overdue' && c.status!=='Due today' && c.dueAt!==null))},
    {key:'undated',label:'Needs a date',cases:sort(open.filter(c=>c.dueAt===null && c.status!=='Overdue' && c.status!=='Due today'))},
  ];
}
export interface ActivityItem {id:string;caseId:string;company:string;title:string;description:string;at:string|null;category:'deadline'|'case';demoSeed:boolean}
export function buildActivity(views:CaseView[],preferences:Preferences):ActivityItem[] {
  const items:ActivityItem[]=[];
  for(const view of views.filter(v=>!v.meta.archived)) {
    const row=view.row;const shared={caseId:row.id,company:row.company,demoSeed:Boolean(row.demoSeed)};
    if(preferences.deadlinePrompts && (row.status==='Overdue' || row.status==='Due today'))items.push({...shared,id:`deadline:${row.id}:${row.dueAt}:${row.status}`,title:row.status==='Overdue' ? 'The confirmed deadline has passed.' : 'A promise is due today.',description:row.title,at:row.dueAt,category:'deadline'});
    if(preferences.caseUpdates)for(const event of caseTimeline(view))items.push({...shared,id:`event:${row.id}:${event.id}`,title:event.title,description:event.note,at:event.at,category:'case'});
  }
  return items.sort((a,b)=>a.category!==b.category ? a.category==='deadline' ? -1 : 1 : (b.at ? Date.parse(b.at) : 0)-(a.at ? Date.parse(a.at) : 0) || a.id.localeCompare(b.id));
}
// GAP: local read projection of contracted case data, not an inbox/notification API.
export const loadActivityCases=listEvidence;
