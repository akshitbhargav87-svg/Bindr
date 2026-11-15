/** Official-source catalogue, narrowly scoped; no legal deadlines or eligibility inference. */
export const escalationSources={version:'india-consumer-2026-11-15',verified:'2026-11-15',jurisdiction:'IN',routes:[
  {title:'National Consumer Helpline',url:'https://consumerhelpline.gov.in/public/about',purpose:'Read the official pre-litigation consumer grievance guidance.'},
  {title:'e-Jagriti',url:'https://e-jagriti.gov.in/',purpose:'Review official consumer commission filing information and current requirements.'},
]};
export function escalationDraft(input:{company:string;confirmedFacts:string[];requestedRemedy:string;outcomeKnown:boolean}){
  if(!input.company.trim() || !input.requestedRemedy.trim() || input.confirmedFacts.length>50)throw new Error('Review the company, confirmed facts and requested remedy.');
  return {subject:`Request for an update: ${input.company}`,body:`Hello ${input.company},\n\nPlease provide an update on these recorded terms:\n${input.confirmedFacts.map(f=>'• '+f).join('\n')}\n\nRequested next step: ${input.requestedRemedy}\n\nPlease confirm the current status and expected date in writing.`,requiresReview:true,sent:false};
}
