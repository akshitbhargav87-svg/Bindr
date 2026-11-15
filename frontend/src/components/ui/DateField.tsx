import {useEffect,useId,useLayoutEffect,useRef,useState,type KeyboardEvent} from 'react';
import {createPortal} from 'react-dom';
import {CalendarDays,ChevronDown,ChevronLeft,ChevronRight} from 'lucide-react';
import './date-field.css';

const iso=(date:Date)=>date.toISOString().slice(0,10);
function parsed(value:string){
  if(!/^\d{4}-\d{2}-\d{2}$/.test(value))return null;
  const date=new Date(value+'T12:00:00Z');
  return Number.isFinite(date.getTime()) && iso(date)===value ? date : null;
}
function todayInIndia(){
  const parts=new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Kolkata',year:'numeric',month:'2-digit',day:'2-digit'}).formatToParts(new Date());
  return ['year','month','day'].map(type=>parts.find(p=>p.type===type)!.value).join('-');
}
const monthName=(month:number)=>new Intl.DateTimeFormat('en',{month:'long',timeZone:'UTC'}).format(new Date(Date.UTC(2026,month,1)));
interface Props {value:string;onChange:(value:string)=>void;label:string;disabled?:boolean;readOnly?:boolean;name?:string;min?:string;max?:string}

export default function DateField({value,onChange,label,disabled=false,readOnly=false,name,min,max}:Props){
  const id=useId(),trigger=useRef<HTMLButtonElement>(null),panel=useRef<HTMLDivElement>(null);
  const [open,setOpen]=useState(false),[cursor,setCursor]=useState(()=>value || todayInIndia());
  const [position,setPosition]=useState({top:0,left:0});
  const focusDate=parsed(cursor) ?? parsed(todayInIndia())!;
  const year=focusDate.getUTCFullYear(),month=focusDate.getUTCMonth(),today=todayInIndia();
  const chosen=parsed(value);
  const display=chosen ? new Intl.DateTimeFormat('en-IN',{day:'numeric',month:'short',year:'numeric',timeZone:'UTC'}).format(chosen) : 'Choose a date';
  const start=new Date(Date.UTC(year,month,1,12));start.setUTCDate(1-start.getUTCDay());
  const days=Array.from({length:42},(_,i)=>{const day=new Date(start);day.setUTCDate(day.getUTCDate()+i);return day;});
  const blocked=(day:string)=>Boolean(min && day<min || max && day>max);
  function close(restoreFocus=true){setOpen(false);if(restoreFocus)trigger.current?.focus();}
  function choose(day:string){if(blocked(day) || disabled || readOnly || trigger.current?.matches(':disabled'))return;onChange(day);close();}
  function moveMonth(delta:number){const date=new Date(Date.UTC(year,month+delta,1,12));setCursor(iso(date));}
  useLayoutEffect(()=>{
    if(!open)return;
    function place(){
      const anchor=trigger.current?.getBoundingClientRect(),popup=panel.current?.getBoundingClientRect();
      if(!anchor || !popup)return;
      const below=anchor.bottom+8;
      setPosition({left:Math.max(12,Math.min(anchor.left,window.innerWidth-popup.width-12)),
        top:Math.max(12,below+popup.height<=window.innerHeight-12 ? below : anchor.top-popup.height-8)});
    }
    place();window.addEventListener('resize',place);window.addEventListener('scroll',place,true);
    const frame=requestAnimationFrame(()=>panel.current?.querySelector<HTMLButtonElement>('.date-picker-day[tabindex="0"]')?.focus());
    return()=>{cancelAnimationFrame(frame);window.removeEventListener('resize',place);window.removeEventListener('scroll',place,true);};
  },[open]);
  useEffect(()=>{
    if(!open)return;
    const outside=(event:PointerEvent)=>{if(!panel.current?.contains(event.target as Node) && !trigger.current?.contains(event.target as Node))setOpen(false);};
    const escape=(event:globalThis.KeyboardEvent)=>{if(event.key==='Escape'){event.preventDefault();setOpen(false);trigger.current?.focus();}};
    document.addEventListener('pointerdown',outside);document.addEventListener('keydown',escape);
    return()=>{document.removeEventListener('pointerdown',outside);document.removeEventListener('keydown',escape);};
  },[open]);
  useEffect(()=>{if(disabled || readOnly)setOpen(false);},[disabled,readOnly]);
  function keyboard(event:KeyboardEvent<HTMLButtonElement>,day:Date){
    const offsets:Record<string,number>={ArrowLeft:-1,ArrowRight:1,ArrowUp:-7,ArrowDown:7,Home:-day.getUTCDay(),End:6-day.getUTCDay()};
    const next=new Date(day);
    if(event.key in offsets)next.setUTCDate(next.getUTCDate()+offsets[event.key]);
    else if(event.key==='PageUp' || event.key==='PageDown')next.setUTCMonth(next.getUTCMonth()+(event.key==='PageUp' ? -1 : 1),1);
    else return;
    event.preventDefault();const key=iso(next);setCursor(key);
    requestAnimationFrame(()=>panel.current?.querySelector<HTMLButtonElement>(`[data-day="${key}"]`)?.focus());
  }
  const firstYear=Math.min(year,new Date().getFullYear()-100),lastYear=Math.max(year,new Date().getFullYear()+20);
  return <span className="date-field">
    {name && <input type="hidden" name={name} value={value}/>}
    <button ref={trigger} type="button" className={`date-field-trigger ${!value ? 'date-field-placeholder' : ''}`}
      disabled={disabled || readOnly} aria-label={`${label}: ${display}`} aria-expanded={open} aria-haspopup="dialog" aria-controls={open ? id : undefined}
      onClick={()=>{if(open)close();else{setCursor(parsed(value) ? value : today);setOpen(true);}}}>
      <CalendarDays size={19}/><span>{display}</span><ChevronDown size={16}/>
    </button>
    {open && createPortal(<div ref={panel} id={id} className="date-picker" role="dialog" aria-label={`Choose ${label.toLowerCase()}`} style={position}
      onBlur={event=>{if(event.relatedTarget && !event.currentTarget.contains(event.relatedTarget as Node) && event.relatedTarget!==trigger.current)setOpen(false);}}>
      <div className="date-picker-header"><button type="button" aria-label="Previous month" onClick={()=>moveMonth(-1)}><ChevronLeft size={18}/></button>
        <div><select aria-label="Month" value={month} onChange={e=>setCursor(iso(new Date(Date.UTC(year,Number(e.target.value),1,12))))}>{Array.from({length:12},(_,i)=><option key={i} value={i}>{monthName(i)}</option>)}</select>
        <select aria-label="Year" value={year} onChange={e=>setCursor(iso(new Date(Date.UTC(Number(e.target.value),month,1,12))))}>{Array.from({length:lastYear-firstYear+1},(_,i)=>firstYear+i).map(y=><option key={y} value={y}>{y}</option>)}</select></div>
        <button type="button" aria-label="Next month" onClick={()=>moveMonth(1)}><ChevronRight size={18}/></button></div>
      <p className="sr-only" aria-live="polite">{monthName(month)} {year}</p>
      <div className="date-picker-weekdays" aria-hidden="true">{['Su','Mo','Tu','We','Th','Fr','Sa'].map(day=><span key={day}>{day}</span>)}</div>
      <div className="date-picker-days">{days.map(day=>{const key=iso(day);return <button key={key} type="button" data-day={key}
        className={`date-picker-day ${day.getUTCMonth()!==month ? 'is-adjacent' : ''} ${key===value ? 'is-selected' : ''} ${key===today ? 'is-today' : ''}`}
        aria-label={new Intl.DateTimeFormat('en-IN',{dateStyle:'full',timeZone:'UTC'}).format(day)} aria-pressed={key===value} aria-current={key===today ? 'date' : undefined}
        tabIndex={key===cursor ? 0 : -1} disabled={blocked(key)} onKeyDown={event=>keyboard(event,day)} onClick={()=>choose(key)}>{day.getUTCDate()}</button>;})}</div>
      <div className="date-picker-footer"><button type="button" onClick={()=>{if(disabled || readOnly || trigger.current?.matches(':disabled'))return;onChange('');close();}}>Clear date</button><button type="button" disabled={blocked(today)} onClick={()=>choose(today)}>Today</button><button type="button" onClick={()=>close()}>Done</button></div>
    </div>,document.body)}
  </span>;
}
