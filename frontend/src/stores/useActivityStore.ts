import { create } from 'zustand';
import { AuditEvent } from '../types';
import { useAuthStore } from './useAuthStore';

interface ActivityState {
  events: AuditEvent[];
  fetchActivity: () => Promise<void>;
  addEvent: (event: AuditEvent) => void;
}

export const useActivityStore = create<ActivityState>((set) => ({
  events: [],

  fetchActivity: async () => {
    const token = useAuthStore.getState().token;
    if (!token) return;

    try {
      const res = await fetch('/api/activity?limit=40', {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        set({ events: data.activity || [] });
      }
    } catch (err) {
      console.error('Failed to fetch activity:', err);
    }
  },

  addEvent: (event: AuditEvent) => {
    set((state) => ({ events: [event, ...state.events.slice(0, 49)] }));
  }
}));
