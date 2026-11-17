import { create } from 'zustand';
import { Telemetry } from '../types';
import { useAuthStore } from './useAuthStore';

interface TelemetryState {
  telemetry: Telemetry | null;
  isLoading: boolean;
  fetchTelemetry: () => Promise<void>;
}

export const useTelemetryStore = create<TelemetryState>((set) => ({
  telemetry: null,
  isLoading: false,

  fetchTelemetry: async () => {
    const token = useAuthStore.getState().token;
    if (!token) return;

    try {
      const res = await fetch('/api/system/telemetry', {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        set({ telemetry: data, isLoading: false });
      }
    } catch (err) {
      console.error('Failed to fetch telemetry:', err);
    }
  }
}));
