import { create } from 'zustand';
const key = 'jarvis_wake_word';
export const useVoiceStore = create<{
  bargeStatus: 'starting' | 'ready' | 'needs-click' | 'unavailable'; inputLevel: number; unlockInterruption: () => void;
  wakeEnabled: boolean; hint: string; transcript: string; retry: number;
  setWakeEnabled: (enabled: boolean) => void; retryMicrophone: () => void;
}>(set => ({
  bargeStatus: 'starting', inputLevel: 0, unlockInterruption: () => {},
  wakeEnabled: localStorage.getItem(key) !== 'off', hint: '', transcript: '', retry: 0,
  setWakeEnabled: enabled => { localStorage.setItem(key, enabled ? 'on' : 'off'); set({wakeEnabled: enabled, hint: ''}); },
  retryMicrophone: () => set(s => ({hint: '', retry: s.retry + 1})),
}));
