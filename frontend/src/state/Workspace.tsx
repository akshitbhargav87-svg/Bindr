import { createContext, useCallback, useContext, useEffect, useRef, useState, type ReactNode } from 'react';
import { isMock, loadWorkspace } from '../api';
import { ApiError } from '../api/types';
import type { WorkspaceSnapshot } from '../api/mapper';
export type DemoView = 'sample' | 'empty' | 'offline' | 'error';
const getPreference = (key: string) => {try {return localStorage.getItem(key);} catch {return null;}};
const setPreference = (key: string, value: string) => {try {localStorage.setItem(key, value);} catch { /* Preferences remain in memory if storage is unavailable. */ }};
function useWorkspaceState() {
  const [data, setData] = useState<WorkspaceSnapshot | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [online, setOnline] = useState(navigator.onLine);
  const [view, setView] = useState<DemoView>(() => getPreference('bindr.demo-view') === 'empty' ? 'empty' : 'sample');
  const [introduced, setIntroduced] = useState(() => getPreference('bindr.introduced') === 'yes');
  const sequence = useRef(0);
  const offline = !online || (isMock && view === 'offline');
  const refresh = useCallback(async () => {
    const current = ++sequence.current;
    if (offline) {setLoading(false); return;}
    setLoading(true); setError(null);
    try {
      if (isMock && view === 'error') throw new Error('The workspace could not be loaded. Your records have not been changed.');
      const result = await loadWorkspace();
      if (current === sequence.current) setData(isMock && view === 'empty' ? {...result, cases: result.cases.filter(c => !c.demoSeed)} : result);
    } catch (cause) {
      if (current === sequence.current) setError(cause instanceof ApiError && cause.status === 401 ? 'Your workspace session could not be opened. Reload this page, then try again.' : cause instanceof ApiError && cause.status === 403 ? 'Your workspace session could not be verified. Reload this page, then try again.' : 'The workspace could not be loaded. Your records have not been changed.');
    } finally {if (current === sequence.current) setLoading(false);}
  }, [offline, view]);
  useEffect(() => {void refresh(); return () => {sequence.current++;};}, [refresh]);
  useEffect(() => {
    const on = () => setOnline(true); const off = () => setOnline(false);
    window.addEventListener('online', on); window.addEventListener('offline', off);
    return () => {window.removeEventListener('online', on); window.removeEventListener('offline', off);};
  }, []);
  function chooseView(next: DemoView) {
    if (!isMock) return;
    if (next === view) return;
    setView(next);
    if (next === 'sample' || next === 'empty') setPreference('bindr.demo-view', next);
    if (next !== 'offline') setData(null);
  }
  function finishIntro(sample = false) {
    setPreference('bindr.introduced', 'yes'); setIntroduced(true);
    if (isMock) chooseView(sample ? 'sample' : 'empty');
  }
  function markIntroduced() {setPreference('bindr.introduced', 'yes'); setIntroduced(true);}
  function showIntro() {setIntroduced(false); setPreference('bindr.introduced', 'no');}
  return {data, loading, error, offline, online, refresh, view, chooseView, introduced, finishIntro, markIntroduced, showIntro, isMock};
}
type WorkspaceValue = ReturnType<typeof useWorkspaceState>;
const Context = createContext<WorkspaceValue | null>(null);
export function WorkspaceProvider({children}: {children: ReactNode}) {return <Context.Provider value={useWorkspaceState()}>{children}</Context.Provider>;}
export function useWorkspace() {const context = useContext(Context); if (!context) throw new Error('WorkspaceProvider is required'); return context;}
