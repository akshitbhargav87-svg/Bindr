import { ApiError, type BindrApi } from './types';
import type { Evidence } from './types';
const origin = (import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(/\/$/, '');
const base = origin.endsWith('/api/v1') ? origin : `${origin}/api/v1`;
async function request<T>(path: string, body?: object | FormData): Promise<T> {
  const headers: Record<string, string> = {};
  if (body && !(body instanceof FormData)) headers['Content-Type'] = 'application/json';
  const csrf = document.cookie.split('; ').find(v => v.startsWith('pk_csrf='))?.slice(8);
  if (body && csrf) headers['X-CSRF-Token'] = decodeURIComponent(csrf);
  // GAP: session bootstrap/login is outside the domain contract; backend must supply it.
  const response = await fetch(`${base}${path}`, {method: body ? 'POST' : 'GET', credentials: 'include', headers, body: body instanceof FormData ? body : body ? JSON.stringify(body) : undefined});
  const data = await response.json();
  if (!response.ok) throw new ApiError(response.status, data.error || {code: 'INVALID_RESPONSE', message: 'The server could not complete this request.', details: [], request_id: ''});
  return data as T;
}
const casePath = (id: string) => `/cases/${encodeURIComponent(id)}`;
export async function downloadHttpEvidence(evidence:Evidence):Promise<Blob> {
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
  listCases: () => request('/cases'), getCase: id => request(casePath(id)), createCase: data => request('/cases', data),
  uploadEvidence: (id, file, version) => {const body = new FormData(); body.append('file', file); body.append('expected_version', String(version)); return request(`${casePath(id)}/evidence`, body);},
  extract: (id, evidence_ids, expected_version) => request(`${casePath(id)}/extractions`, {evidence_ids, expected_version}),
  review: (id, extractionId, data) => request(`${casePath(id)}/extractions/${encodeURIComponent(extractionId)}/review`, data),
  resolve: (id, expected_version, resolution_note) => request(`${casePath(id)}/resolve`, {expected_version, resolution_note}),
  complaint: (id, expected_version, requested_remedy) => request(`${casePath(id)}/complaint-draft`, {expected_version, requested_remedy}),
};
