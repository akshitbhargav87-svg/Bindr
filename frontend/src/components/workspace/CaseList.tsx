import { Link } from 'react-router-dom';
import { ChevronRight, History, SearchX } from 'lucide-react';
import { StatusLabel, Button } from '../ui';
import type { CaseRow } from '../../api/mapper';
import { date, money } from '../../lib/format';
export function CompanyMark({name}: {name: string}) {return <span className="case-company-mark" aria-hidden="true">{name.split(/\s+/).slice(0,2).map(n => n[0]).join('')}</span>;}
export function CaseList({cases, timezone = 'Asia/Kolkata', compact = false, caseLink}: {cases: CaseRow[]; timezone?: string; compact?: boolean; caseLink?:(item:CaseRow)=>string}) {
  return <div className={`case-list ${compact ? 'case-list-compact' : ''}`}><div className="case-list-header" aria-hidden="true"><span>Company & promise</span><span>Amount</span><span>Deadline</span><span>Status</span><span/></div><ul>{cases.map(item => <li key={item.id}><Link className="case-row" to={caseLink ? caseLink(item) : `/app/cases/${item.id}`} aria-label={`${item.company}, ${item.title}, ${item.status}${item.partial ? ', partially fulfilled' : ''}`}><div className="case-company"><CompanyMark name={item.company}/><div><strong>{item.company}</strong><span>{item.title}</span>{item.partial && <small>Partially fulfilled · balance shown</small>}{item.revisionCount > 0 && <small><History size={13}/>{item.revisionCount} revised {item.revisionCount===1 ? 'promise' : 'promises'}</small>}</div></div><span className="case-money">{item.multipleCurrencies ? 'Multiple currencies' : money(item.amountMinor, item.currency ?? 'INR')}</span><span className="case-deadline">{date(item.dueAt, timezone)}</span><span className="case-status"><StatusLabel status={item.status}/></span><ChevronRight className="case-chevron" size={18}/></Link></li>)}</ul></div>;
}
export function NoCases({search, filtered, clear}: {search: string; filtered: boolean; clear: () => void}) {
  return <div className="no-cases" role="status"><SearchX size={30}/><h2>{search ? `No cases match “${search}”.` : 'No cases with this status.'}</h2><p>{search ? 'Try a company name or a word from the promise.' : 'Choose another status to see more of your records.'}</p><Button variant="secondary" onClick={clear}>{filtered ? 'Clear search & filters' : 'Clear search'}</Button></div>;
}
