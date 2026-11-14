import type { Candidate, Terms } from './types';
import { minorUnits, relativeMockDate, validDay } from './capture-validation';
export interface ReadableSource {id: string; text: string; communicationDate: string}
/** Local deterministic demo parser; never presented as live AI/OCR. */
export function extractMockCandidates(sources: ReadableSource[]): Candidate[] {
  const result: Candidate[] = [];
  for (const source of sources) {
    const paragraphs = source.text.split(/\n\s*\n/).map(s => s.trim()).filter(Boolean);
    for (const quote of paragraphs) {
      if (!/\b(will|promise|confirm|within|by)\b/i.test(quote) || !/\b(refund|replac\w*|deliver\w*|credit)\b/i.test(quote)) continue;
      const kind: Terms['kind'] = /refund/i.test(quote) ? 'refund' : /replac/i.test(quote) ? 'replacement' : /credit/i.test(quote) ? 'service' : 'other';
      const match = quote.match(/(?:₹|INR\s*)([\d,]+(?:\.\d{1,2})?)/i);
      const amount_minor = match ? minorUnits(match[1].replaceAll(',','')) : null;
      let due_at: string | null = null; const warnings: string[] = [];
      const absolute = quote.match(/\b(\d{4}-\d{2}-\d{2})\b/);
      const relative = quote.match(/within\s+(\d+)(?:\s*[-–]\s*(\d+))?\s*(business\s+)?days?/i);
      if (absolute && validDay(absolute[1])) {due_at = new Date(`${absolute[1]}T23:59:59+05:30`).toISOString().replace('.000Z','Z'); warnings.push('Confirm this date-only deadline ends at 23:59 in Asia/Kolkata.');}
      else if (relative && source.communicationDate) {
        const day = relativeMockDate(source.communicationDate,Number(relative[2] ?? relative[1]),Boolean(relative[3]));
        due_at = new Date(`${day}T23:59:59+05:30`).toISOString().replace('.000Z','Z');
        const range=relative[2] ? `; window ${relativeMockDate(source.communicationDate,Number(relative[1]),Boolean(relative[3]))} to ${day}; the final day determines overdue` : '';
        warnings.push(`Count starts after ${source.communicationDate}; ${relative[3] ? 'Saturday and Sunday are skipped; holidays are not excluded' : 'calendar days are counted'}${range}. Confirm the result.`);
      } else warnings.push(/soon|shortly/i.test(quote) ? '“Soon” is not a date. Choose an explicit date or keep the deadline unset.' : 'No unambiguous deadline was found. Confirm a date or keep it unset.');
      if (kind === 'refund' && amount_minor === null) warnings.push('The refund amount needs your review.');
      const description = /returned headphones/i.test(quote) ? 'Refund for returned headphones' : kind === 'refund' ? 'Refund for returned order' : kind === 'replacement' ? 'Replacement for a faulty product' : kind === 'service' ? 'Service credit' : 'Delivery of delayed order';
      result.push({candidate_id:`c${result.length+1}`,terms:{kind,description,amount_minor,currency:amount_minor === null ? null : 'INR',due_at},sources:[{evidence_id:source.id,quote:quote.slice(0,2000)}],confidence:0,warnings,revision:{relation:'new',supersedes_id:null,reason:'Review as a new promise.'}});
      if (result.length === 10) return result;
    }
  }
  return result;
}
