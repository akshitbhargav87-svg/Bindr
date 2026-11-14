// Presentation only. Status/deadline decisions belong to adapters/backend.
export function money(minor: number | null, currency = 'INR') {
  if (minor === null) return '—';
  return new Intl.NumberFormat('en-IN', {style: 'currency', currency, maximumFractionDigits: minor % 100 === 0 ? 0 : 2}).format(minor / 100);
}
export function date(value: string | null, timezone = 'Asia/Kolkata') {
  if (!value) return 'No date set';
  return new Intl.DateTimeFormat('en-GB', {day: 'numeric', month: 'short', year: 'numeric', timeZone: timezone}).format(new Date(value.length === 10 ? `${value}T12:00:00Z` : value));
}
