import { create } from 'zustand';
const key = 'jarvis_wake_word';
export const useVoiceStore = create<{
  wakeEnabled: boolean; hint: string; transcript: string; retry: number;
  setWakeEnabled: (enabled: boolean) => void; retryMicrophone: () => void;
}>(set => ({
  wakeEnabled: localStorage.getItem(key) !== 'off', hint: '', transcript: '', retry: 0,
  setWakeEnabled: enabled => { localStorage.setItem(key, enabled ? 'on' : 'off'); set({wakeEnabled: enabled, hint: ''}); },
  retryMicrophone: () => set(s => ({hint: '', retry: s.retry + 1})),
}));
