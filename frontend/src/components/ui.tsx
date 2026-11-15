import type { ButtonHTMLAttributes, InputHTMLAttributes, ReactNode } from 'react';
import { CalendarClock, CheckCircle2, Circle, ClockAlert, Info } from 'lucide-react';
function CalendarQuestion({size = 13}: {size?: number}) {return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" aria-hidden="true"><rect x="3" y="5" width="18" height="16" rx="2"/><path d="M16 3v4M8 3v4M3 11h18M10 15a2 2 0 0 1 4 0c0 1-2 1-2 2M12 19h.01"/></svg>;}
export function Button({variant = 'primary', className = '', ...props}: ButtonHTMLAttributes<HTMLButtonElement> & {variant?: 'primary' | 'secondary' | 'text'}) {return <button className={`button button-${variant} ${className}`} {...props}/>;}
export function Input({className = '', ...props}: InputHTMLAttributes<HTMLInputElement>) {return <input className={`input ${className}`} {...props}/>;}
export type Status = 'Overdue' | 'Due today' | 'Active' | 'Resolved' | 'Needs a date' | 'Needs review';
const icons = {'Overdue': ClockAlert, 'Due today': CalendarClock, 'Active': Circle, 'Resolved': CheckCircle2, 'Needs a date': CalendarQuestion, 'Needs review': Info};
export function StatusLabel({status}: {status: Status}) {const Icon = icons[status]; return <span className={`status status-${status.toLowerCase().replaceAll(' ', '-')}`}><Icon size={13}/>{status}</span>;}
export function Alert({children}: {children: ReactNode}) {return <div className="alert" role="status"><Info size={18}/><div>{children}</div></div>;}
export function Brand({compact = false}: {compact?: boolean}) {return <span className="brand" role="img" aria-label="Bindr"><img src="/bindr-mark.svg" alt="" width="23" height="30"/>{!compact && <span aria-hidden="true">indr<span className="brand-period">.</span></span>}</span>;}
