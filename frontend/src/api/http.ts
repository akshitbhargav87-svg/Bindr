import { ApiError, type BindrApi } from './types';
import type { Evidence } from './types';
import { caseListResponse,caseResponse,complaintResponse,detailResponse,extractResponse,ProtocolError,reviewResponse,uploadResponse } from './protocol';
const origin = (import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(/\/+$/, '');
const base = origin.endsWith('/api/v1') ? origin : `${origin}/api/v1`;
let sessionReady: Promise<void> | null = null;
function csrfToken(): string | undefined {
  const token = document.cookie.split(/;\s*/).find(v => v.startsWith('pk_csrf='))?.slice(8);
  try {return token ? decodeURIComponent(token) : undefined;} catch {throw new ApiError(403,{code:'CSRF_FAILED',message:'Your session token could not be read. Reload this page to restore your workspace session.',details:[],request_id:''});}
}
/** The server chooses an isolated anonymous identity; the browser never supplies one. */
async function ensureSession(): Promise<void> {
  if (!sessionReady) sessionReady = (async () => {
    let response = await fetch(`${base}/auth/session`, {credentials:'include',cache:'no-store'});
    if (response.status === 401) response = await fetch(`${base}/auth/session`, {method:'POST',credentials:'include',cache:'no-store',headers:{'Content-Type':'application/json'},body:'{}'});
    if (!response.ok) throw new ApiError(response.status,{code:'SESSION_UNAVAILABLE',message:'Your workspace session could not be opened. Please try again.',details:[],request_id:''});
    let value;
    try {value = await response.json();} catch {throw new ProtocolError();}
    if (!value || typeof value.session_id !== 'string' || typeof value.user_id !== 'string' || typeof value.csrf_token !== 'string' || !value.csrf_token) throw new ProtocolError();
  })().catch(cause => {sessionReady = null; throw cause;});
  return sessionReady;
}
async function request<T>(path: string, body: object | FormData | undefined,validate:(value:unknown)=>T): Promise<T> {
  // Reject an unreadable token before any write, including session setup.
  if (body) csrfToken();
  await ensureSession();
  const headers: Record<string, string> = {};
  if (body && !(body instanceof FormData)) headers['Content-Type'] = 'application/json';
  const csrf = csrfToken();
  if (body && csrf) headers['X-CSRF-Token'] = csrf;
  const response = await fetch(`${base}${path}`, {method: body ? 'POST' : 'GET', credentials: 'include',cache:'no-store', headers, body: body instanceof FormData ? body : body ? JSON.stringify(body) : undefined});
  let data;
  try{data=await response.json();}catch{if(response.ok)throw new ProtocolError();throw new ApiError(response.status,{code:'HTTP_ERROR',message:response.status===401 ? 'Your workspace session is unavailable.' : response.status===403 ? 'Your workspace session could not be verified.' : 'The server could not complete this request.',details:[],request_id:''});}
  if (!response.ok) {
    if (response.status === 401) sessionReady = null;
    const e=data?.error;const valid=e && typeof e.code==='string' && typeof e.message==='string' && Array.isArray(e.details) && e.details.every((item:unknown)=>item && typeof item==='object' && typeof (item as {field?:unknown}).field==='string' && typeof (item as {message?:unknown}).message==='string') && typeof e.request_id==='string';
    throw new ApiError(response.status,valid ? e : {code:'HTTP_ERROR',message:'The server could not complete this request.',details:[],request_id:''});
  }
  return validate(data);
}
const casePath = (id: string) => `/cases/${encodeURIComponent(id)}`;
export async function downloadHttpEvidence(evidence:Evidence):Promise<Blob> {
  await ensureSession();
  // Construct the contracted route; never follow an evidence-supplied external URL.
  const response=await fetch(`${base}${casePath(evidence.case_id)}/evidence/${encodeURIComponent(evidence.id)}/content`,{credentials:'include',cache:'no-store'});
  if(!response.ok) {
    let message='The original file could not be loaded.';
    if(response.status===404)message='This original file is unavailable. The linked case history is still retained.';
    throw new ApiError(response.status,{code:'EVIDENCE_UNAVAILABLE',message,details:[],request_id:''});
  }
  return response.blob();
}
export const httpApi: BindrApi = {
  listCases: () => request('/cases',undefined,caseListResponse), getCase: id => request(casePath(id),undefined,data=>detailResponse(data,id)), createCase: data => request('/cases',data,caseResponse),
  uploadEvidence: (id, file, version) => {const body = new FormData(); body.append('file', file); body.append('expected_version', String(version)); return request(`${casePath(id)}/evidence`, body,data=>uploadResponse(data,id));},
  extract: (id, evidence_ids, expected_version) => request(`${casePath(id)}/extractions`, {evidence_ids, expected_version},data=>extractResponse(data,id)),
  review: (id, extractionId, data) => request(`${casePath(id)}/extractions/${encodeURIComponent(extractionId)}/review`,data,result=>reviewResponse(result,id)),
  resolve: (id, expected_version, resolution_note) => request(`${casePath(id)}/resolve`, {expected_version, resolution_note},data=>caseResponse(data,id)),
  complaint: (id, expected_version, requested_remedy) => request(`${casePath(id)}/complaint-draft`, {expected_version, requested_remedy},complaintResponse),
};
