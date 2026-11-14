import { httpApi } from './http';
import { mockApi } from './mock';
export const isMock = import.meta.env.VITE_USE_MOCK !== 'false';
export const api = isMock ? mockApi : httpApi;
