import type { ReviewFields } from './capture-model';
import type { Terms } from './types';
export const MAX_FILE_BYTES = 10 * 1024 * 1024;
export function validateFile(file: Pick<File,'size'|'type'|'name'>, mock: boolean): string | null {
  if (!file.size) return 'This file is empty. Replace it or paste the message.';
  if (file.size > MAX_FILE_BYTES) return 'This file exceeds 10 MB. Replace it with a smaller file or paste the text.';
  const allowed = ['image/png','image/jpeg','application/pdf','text/plain'];
  void mock;
  if (!allowed.includes(file.type)) return 'Use PNG, JPG, PDF or plain text. Replace this file or paste the message.';
  return null;
}
export function validDay(day: string): boolean {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(day)) return false;
  const parsed = new Date(`${day}T12:00:00Z`);
  return Number.isFinite(parsed.getTime()) && parsed.toISOString().slice(0,10) === day;
}
export function minorUnits(input: string): number | null {
  if (!input.trim()) return null;
  if (!/^\d+(\.\d{1,2})?$/.test(input.trim())) throw new Error('Enter a nonnegative amount with up to two decimals.');
  const [whole,fraction=''] = input.trim().split('.');
  const result = Number(whole) * 100 + Number(fraction.padEnd(2,'0'));
  if (!Number.isSafeInteger(result)) throw new Error('This amount is too large.');
  return result;
}
export function dayInIndia(stamp: string): string {
  const parts = new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Kolkata',year:'numeric',month:'2-digit',day:'2-digit'}).formatToParts(new Date(stamp));
  return ['year','month','day'].map(type => parts.find(p => p.type === type)!.value).join('-');
}
export function termsFromFields(field: ReviewFields): Terms {
  const amount_minor = minorUnits(field.amount);
  if (!field.description.trim() || field.description.trim().length > 2000) throw new Error('Describe the promise in 1–2000 characters.');
  if (field.kind === 'refund' && amount_minor === null) throw new Error('A refund needs an amount before it can be tracked.');
  if (field.deadline && !validDay(field.deadline)) throw new Error('Choose a valid date or leave the deadline unset.');
  if(amount_minor!==null && !/^[A-Z]{3}$/.test(field.currency)) throw new Error('Review the currency code before confirming the amount.');
  const due_at = !field.deadline ? null : field.originalDueAt && dayInIndia(field.originalDueAt) === field.deadline ? field.originalDueAt : new Date(`${field.deadline}T23:59:59+05:30`).toISOString().replace('.000Z','Z');
  return {kind:field.kind,description:field.description.trim(),amount_minor,currency:amount_minor === null ? null : field.currency,due_at};
}
/** Deterministic calendar used by the mock adapter only: day zero is communication day. */
export function relativeMockDate(start: string, count: number, business: boolean): string {
  if (!validDay(start) || count < 0 || count > 366 || !Number.isInteger(count)) throw new Error('Clarify the communication date and time window.');
  const day = new Date(`${start}T12:00:00Z`);
  for (let elapsed = 0; elapsed < count;) {day.setUTCDate(day.getUTCDate()+1); if (!business || (day.getUTCDay() !== 0 && day.getUTCDay() !== 6)) elapsed++;}
  return day.toISOString().slice(0,10);
}
