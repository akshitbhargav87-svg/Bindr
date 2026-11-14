import { httpApi } from './http';
import { mockApi, loadMockWorkspace } from './mock';
import { loadHttpWorkspace } from './workspace';
export const isMock = import.meta.env.VITE_USE_MOCK !== 'false';
export const api = isMock ? mockApi : httpApi;
export const loadWorkspace = isMock ? loadMockWorkspace : loadHttpWorkspace;
