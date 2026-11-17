import { create } from 'zustand';
import { OrbState, Message, SessionMeta, ApprovalRequest } from '../types';
import { useAuthStore } from './useAuthStore';
import { useAudioStore } from './useAudioStore';
import { useActivityStore } from './useActivityStore';

interface JarvisState {
  currentSessionId: string;
  sessions: SessionMeta[];
  messages: Message[];
  orbState: OrbState;
  currentTool: { name: string; args: any } | null;
  currentThought: string | null;
  pendingApprovals: ApprovalRequest[];
  ws: WebSocket | null;
  voiceEnabled: boolean;
  isEmergencyStopped: boolean;
  isListening: boolean;

  // Actions
  setOrbState: (state: OrbState) => void;
  setVoiceEnabled: (enabled: boolean) => void;
  setIsListening: (listening: boolean) => void;
  connectWebSocket: () => void;
  disconnectWebSocket: () => void;
  loadSessions: () => Promise<void>;
  createSession: (title?: string) => Promise<string>;
  switchSession: (sessionId: string) => Promise<void>;
  deleteSession: (sessionId: string) => Promise<void>;
  sendMessage: (text: string) => void;
  decideApproval: (requestId: string, decision: 'approve' | 'reject') => Promise<void>;
  cancelSession: () => Promise<void>;
  triggerEmergencyStop: () => Promise<void>;
  fetchPendingApprovals: () => Promise<void>;
}

export const useJarvisStore = create<JarvisState>((set, get) => {
  let reconnectTimer: any = null;

  return {
    currentSessionId: 'default',
    sessions: [],
    messages: [],
    orbState: 'disconnected',
    currentTool: null,
    currentThought: null,
    pendingApprovals: [],
    ws: null,
    voiceEnabled: true,
    isEmergencyStopped: false,
    isListening: false,

    setOrbState: (state: OrbState) => set({ orbState: state }),
    setVoiceEnabled: (enabled: boolean) => set({ voiceEnabled: enabled }),
    setIsListening: (listening: boolean) => {
      set({ isListening: listening });
      if (listening) {
        set({ orbState: 'listening' });
      } else if (get().orbState === 'listening') {
        set({ orbState: 'idle' });
      }
    },

    connectWebSocket: () => {
      const token = useAuthStore.getState().token;
      if (!token) {
        set({ orbState: 'disconnected' });
        return;
      }

      if (get().ws && get().ws?.readyState === WebSocket.OPEN) {
        return;
      }

      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const wsUrl = `${protocol}//${window.location.host}/ws?token=${encodeURIComponent(token)}`;

      const socket = new WebSocket(wsUrl);

      socket.onopen = () => {
        set({ ws: socket, orbState: 'idle', isEmergencyStopped: false });
        if (reconnectTimer) clearTimeout(reconnectTimer);
        get().loadSessions();
        get().fetchPendingApprovals();
      };

      socket.onclose = () => {
        set({ ws: null, orbState: 'disconnected' });
        reconnectTimer = setTimeout(() => {
          if (useAuthStore.getState().isAuthenticated) {
            get().connectWebSocket();
          }
        }, 3000);
      };

      socket.onerror = (err) => {
        console.error('WebSocket connection error:', err);
        set({ orbState: 'error' });
      };

      socket.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);

          switch (data.type) {
            case 'thought':
              set({ currentThought: data.text, orbState: 'thinking' });
              break;

            case 'tool_start':
              set({
                currentTool: { name: data.tool, args: data.args },
                orbState: 'acting'
              });
              useActivityStore.getState().addEvent({
                timestamp: Math.floor(Date.now() / 1000),
                iso_time: new Date().toISOString(),
                event_type: 'TOOL_EXECUTE',
                session_id: data.session_id,
                action: 'tool_start',
                tool: data.tool,
                args: data.args,
                policy: 'INFO',
                status: 'RUNNING',
                detail: `Executing ${data.tool}`
              });
              break;

            case 'tool_end':
              set({ currentTool: null });
              break;

            case 'approval_required':
              set((state) => ({
                pendingApprovals: [
                  ...state.pendingApprovals.filter((r) => r.id !== data.request.id),
                  data.request
                ],
                orbState: 'error'
              }));
              break;

            case 'response':
              set({
                orbState: 'idle',
                currentTool: null,
                currentThought: null
              });
              // Append assistant message
              const newMsg: Message = {
                id: `msg_${Date.now()}`,
                role: 'assistant',
                content: data.text,
                timestamp: Math.floor(Date.now() / 1000),
                audio_id: data.audio_id,
                audio_url: data.audio_url
              };
              set((state) => ({ messages: [...state.messages, newMsg] }));

              // Play audio if available and voice enabled
              if (get().voiceEnabled && data.audio_url) {
                set({ orbState: 'speaking' });
                useAudioStore.getState().playAudio(data.audio_url, data.audio_id);
              }
              break;

            case 'task_cancelled':
              set({
                orbState: 'idle',
                currentTool: null,
                currentThought: null
              });
              break;

            default:
              break;
          }
        } catch (err) {
          console.error('Error parsing WS message:', err);
        }
      };
    },

    disconnectWebSocket: () => {
      const socket = get().ws;
      if (socket) {
        socket.close();
      }
      set({ ws: null, orbState: 'disconnected' });
    },

    loadSessions: async () => {
      const token = useAuthStore.getState().token;
      try {
        const res = await fetch('/api/sessions', {
          headers: { Authorization: `Bearer ${token}` }
        });
        if (res.ok) {
          const data = await res.json();
          set({ sessions: data.sessions || [] });

          // If no active session or active not in list, pick the first
          const current = get().currentSessionId;
          if (data.sessions.length > 0 && (!current || !data.sessions.some((s: SessionMeta) => s.id === current))) {
            get().switchSession(data.sessions[0].id);
          }
        }
      } catch (err) {
        console.error('Failed to load sessions:', err);
      }
    },

    createSession: async (title?: string) => {
      const token = useAuthStore.getState().token;
      try {
        const res = await fetch('/api/sessions', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`
          },
          body: JSON.stringify({ title: title || 'New Session' })
        });
        if (res.ok) {
          const data = await res.json();
          await get().loadSessions();
          await get().switchSession(data.session.id);
          return data.session.id;
        }
      } catch (err) {
        console.error('Failed to create session:', err);
      }
      return '';
    },

    switchSession: async (sessionId: string) => {
      const token = useAuthStore.getState().token;
      try {
        const res = await fetch(`/api/sessions/${sessionId}`, {
          headers: { Authorization: `Bearer ${token}` }
        });
        if (res.ok) {
          const data = await res.json();
          set({
            currentSessionId: sessionId,
            messages: data.messages || [],
            currentTool: null,
            currentThought: null
          });
          get().fetchPendingApprovals();
        }
      } catch (err) {
        console.error(`Failed to switch to session ${sessionId}:`, err);
      }
    },

    deleteSession: async (sessionId: string) => {
      const token = useAuthStore.getState().token;
      try {
        const res = await fetch(`/api/sessions/${sessionId}`, {
          method: 'DELETE',
          headers: { Authorization: `Bearer ${token}` }
        });
        if (res.ok) {
          await get().loadSessions();
        }
      } catch (err) {
        console.error(`Failed to delete session ${sessionId}:`, err);
      }
    },

    sendMessage: (text: string) => {
      const socket = get().ws;
      const sessionId = get().currentSessionId;
      if (!socket || socket.readyState !== WebSocket.OPEN) {
        console.error('WebSocket is not open.');
        return;
      }

      // Add user message to UI immediately
      const userMsg: Message = {
        id: `msg_${Date.now()}`,
        role: 'user',
        content: text,
        timestamp: Math.floor(Date.now() / 1000)
      };
      set((state) => ({
        messages: [...state.messages, userMsg],
        orbState: 'thinking'
      }));

      socket.send(
        JSON.stringify({
          type: 'chat',
          session_id: sessionId,
          text: text,
          voice: get().voiceEnabled
        })
      );
    },

    decideApproval: async (requestId: string, decision: 'approve' | 'reject') => {
      const token = useAuthStore.getState().token;
      try {
        const res = await fetch(`/api/approvals/${requestId}/decide`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`
          },
          body: JSON.stringify({ decision })
        });
        if (res.ok) {
          set((state) => ({
            pendingApprovals: state.pendingApprovals.filter((r) => r.id !== requestId),
            orbState: decision === 'approve' ? 'acting' : 'idle'
          }));
        }
      } catch (err) {
        console.error(`Failed to decide approval ${requestId}:`, err);
      }
    },

    cancelSession: async () => {
      const token = useAuthStore.getState().token;
      const sessionId = get().currentSessionId;
      try {
        await fetch(`/api/sessions/${sessionId}/cancel`, {
          method: 'POST',
          headers: { Authorization: `Bearer ${token}` }
        });
        useAudioStore.getState().stopAudio();
        set({
          orbState: 'idle',
          currentTool: null,
          currentThought: null,
          pendingApprovals: []
        });
      } catch (err) {
        console.error('Failed to cancel session:', err);
      }
    },

    triggerEmergencyStop: async () => {
      const token = useAuthStore.getState().token;
      try {
        await fetch('/api/emergency-stop', {
          method: 'POST',
          headers: { Authorization: `Bearer ${token}` }
        });
        useAudioStore.getState().stopAudio();
        set({
          isEmergencyStopped: true,
          orbState: 'error',
          currentTool: null,
          currentThought: null,
          pendingApprovals: []
        });
      } catch (err) {
        console.error('Failed to trigger emergency stop:', err);
      }
    },

    fetchPendingApprovals: async () => {
      const token = useAuthStore.getState().token;
      try {
        const res = await fetch('/api/approvals', {
          headers: { Authorization: `Bearer ${token}` }
        });
        if (res.ok) {
          const data = await res.json();
          set({ pendingApprovals: data.pending_approvals || [] });
        }
      } catch (err) {
        console.error('Failed to fetch approvals:', err);
      }
    }
  };
});
