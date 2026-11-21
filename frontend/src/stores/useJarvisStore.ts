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
  connectionError: string | null;
  actionError: string | null;
  reconnectAttempt: number;
  voiceEnabled: boolean;
  isEmergencyStopped: boolean;
  isListening: boolean;
  voiceConversation: boolean;
  pendingAudioMessageId: string | null;
  setVoiceConversation: (enabled: boolean) => void;

  // Actions
  setOrbState: (state: OrbState) => void;
  setVoiceEnabled: (enabled: boolean) => void;
  setIsListening: (listening: boolean) => void;
  connectWebSocket: () => void;
  retryConnection: () => void;
  disconnectWebSocket: () => void;
  loadSessions: () => Promise<boolean>;
  createSession: (title?: string) => Promise<string>;
  switchSession: (sessionId: string) => Promise<void>;
  deleteSession: (sessionId: string) => Promise<void>;
  sendMessage: (text: string) => boolean;
  decideApproval: (requestId: string, decision: 'approve' | 'reject') => Promise<void>;
  cancelSession: () => Promise<void>;
  triggerEmergencyStop: () => Promise<void>;
  fetchPendingApprovals: () => Promise<void>;
}

export const useJarvisStore = create<JarvisState>((set, get) => {
  let reconnectTimer: any = null;
  let selection = 0;

  return {
    currentSessionId: '',
    sessions: [],
    messages: [],
    orbState: 'disconnected',
    currentTool: null,
    currentThought: null,
    pendingApprovals: [],
    ws: null,
    actionError: null,
    connectionError: null,
    reconnectAttempt: 0,
    voiceEnabled: true,
    isEmergencyStopped: false,
    isListening: false,
    voiceConversation: false,
    pendingAudioMessageId: null,
    setVoiceConversation: (enabled: boolean) => set({ voiceConversation: enabled }),

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

      const existingSocket = get().ws;
      if (
        existingSocket &&
        (existingSocket.readyState === WebSocket.CONNECTING || existingSocket.readyState === WebSocket.OPEN)
      ) {
        return;
      }

      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const wsUrl = `${protocol}//${window.location.host}/ws?token=${encodeURIComponent(token)}`;

      const socket = new WebSocket(wsUrl);
      set({ ws: socket, connectionError: null });

      socket.onopen = async () => {
        if (get().ws !== socket) return;
        set({
          ws: socket,
          orbState: 'disconnected',
          isEmergencyStopped: false,
          connectionError: null,
          reconnectAttempt: 0
        });
        if (reconnectTimer) clearTimeout(reconnectTimer);
        const initialSelection = selection;
        const loaded = await get().loadSessions();
        if (get().ws !== socket || initialSelection !== selection) return;
        if (!loaded) {
          set({ connectionError: 'Could not load your conversations. Tap Retry.' });
          return;
        }
        const sessions = get().sessions;
        const preferred = get().currentSessionId || localStorage.getItem('jarvis_session_id');
        const target = sessions.find(s => s.id === preferred) || sessions[0];
        await get().switchSession(target?.id || 'default');
        get().fetchPendingApprovals();
      };

      socket.onclose = (event) => {
        // Ignore a stale socket closed by cleanup or a newer connection.
        if (get().ws !== socket) return;

        const attempt = get().reconnectAttempt + 1;
        const message = event.code === 1008
          ? 'Connection rejected. Check the owner token.'
          : event.code === 1011
            ? 'The JARVIS core reported an internal error.'
            : 'Realtime link unavailable. The gateway may be missing WebSocket support.';
        set({
          ws: null,
          orbState: 'disconnected',
          connectionError: message,
          reconnectAttempt: attempt
        });
        const delay = Math.min(15000, 1500 * 2 ** Math.min(attempt - 1, 3));
        reconnectTimer = setTimeout(() => {
          if (useAuthStore.getState().isAuthenticated) {
            get().connectWebSocket();
          }
        }, delay);
      };

      socket.onerror = (err) => {
        console.error('WebSocket connection error:', err);
        set({
          orbState: 'error',
          connectionError: 'Unable to establish the realtime link to JARVIS.'
        });
      };

      socket.onmessage = (event) => {
        if (get().ws !== socket) return;
        try {
          const data = JSON.parse(event.data);
          if (data.session_id && data.session_id !== get().currentSessionId &&
              data.type !== 'approval_required') return;

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
              if (get().voiceEnabled && data.voice_pending) useAudioStore.setState({ playbackState: 'generating' });
              set({
                pendingAudioMessageId: data.message_id || null,
                orbState: 'idle',
                currentTool: null,
                currentThought: null
              });
              // Append assistant message
              const newMsg: Message = {
                id: data.message_id || `msg_${Date.now()}`,
                role: 'assistant',
                content: data.text,
                timestamp: Math.floor(Date.now() / 1000),
                audio_id: data.audio_id,
                audio_url: data.audio_url
              };
              set((state) => ({ messages: [...state.messages.filter(m => m.id !== newMsg.id), newMsg] }));
              void get().loadSessions();

              // Play audio if available and voice enabled
              if (get().voiceEnabled && data.audio_url) {
                set({ orbState: 'speaking' });
                useAudioStore.getState().playAudio(data.audio_url, data.audio_id);
              }
              break;

            case 'reply_audio':
              set(state => ({ messages: state.messages.map(m => m.id === data.message_id
                ? { ...m, audio_id: data.audio_id, audio_url: data.audio_url, voiceUnavailable: !data.audio_id }
                : m) }));
              if (data.message_id !== get().pendingAudioMessageId) break;
              set({ pendingAudioMessageId: null });
              if (!data.audio_url) useAudioStore.setState({ playbackState: 'idle' });
              if (data.audio_url && get().voiceEnabled && !get().isEmergencyStopped) {
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

            case 'error':
              useAudioStore.getState().stopAudio();
              set({
                voiceConversation: false,
                pendingAudioMessageId: null,
                orbState: 'error',
                currentTool: null,
                currentThought: null,
                connectionError: data.message || 'JARVIS encountered an unexpected error.'
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
      if (reconnectTimer) {
        clearTimeout(reconnectTimer);
        reconnectTimer = null;
      }
      const socket = get().ws;
      set({ ws: null, orbState: 'disconnected' });
      if (socket) {
        socket.close();
      }
    },

    retryConnection: () => {
      if (reconnectTimer) {
        clearTimeout(reconnectTimer);
        reconnectTimer = null;
      }
      const socket = get().ws;
      set({ ws: null, orbState: 'disconnected', connectionError: null, reconnectAttempt: 0 });
      if (socket) socket.close();
      get().connectWebSocket();
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
          return true;
        }
      } catch (err) {
        console.error('Failed to load sessions:', err);
      }
      return false;
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
      const request = ++selection;
      const socket = get().ws;
      set({ currentSessionId: '', messages: [], orbState: 'disconnected', voiceConversation: false, pendingAudioMessageId: null });
      useAudioStore.getState().stopAudio();
      const token = useAuthStore.getState().token;
      try {
        const res = await fetch(`/api/sessions/${sessionId}`, {
          headers: { Authorization: `Bearer ${token}` }
        });
        const freshDefault = sessionId === 'default' && res.status === 404;
        if (res.ok || freshDefault) {
          const data = freshDefault ? { messages: [] } : await res.json();
          if (request !== selection || get().ws !== socket) return;
          localStorage.setItem('jarvis_session_id', sessionId);
          set({
            currentSessionId: sessionId,
            orbState: socket?.readyState === WebSocket.OPEN ? 'idle' : 'disconnected',
            connectionError: null,
            messages: data.messages || [],
            currentTool: null,
            currentThought: null
          });
          get().fetchPendingApprovals();
        } else {
          throw new Error('Conversation unavailable');
        }
      } catch (err) {
        if (request === selection && get().ws === socket) set({ connectionError: 'Could not load this conversation. Retry to reconnect.' });
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
          if (get().currentSessionId === sessionId) {
            await get().switchSession(get().sessions[0]?.id || 'default');
          }
        }
      } catch (err) {
        console.error(`Failed to delete session ${sessionId}:`, err);
      }
    },

    sendMessage: (text: string) => {
      const socket = get().ws;
      const sessionId = get().currentSessionId;
      if (!sessionId || !socket || socket.readyState !== WebSocket.OPEN || get().pendingApprovals.length ||
          ['acting', 'thinking', 'error', 'disconnected'].includes(get().orbState)) {
        return false;
      }

      useAudioStore.getState().stopAudio();
      set({ pendingAudioMessageId: null, isEmergencyStopped: false });
      // Add user message to UI immediately
      const userMsg: Message = {
        id: `msg_${Date.now()}`,
        role: 'user',
        content: text,
        timestamp: Math.floor(Date.now() / 1000)
      };
      try {
        socket.send(
        JSON.stringify({
          type: 'chat',
          session_id: sessionId,
          text: text,
          text_first: true,
          voice: get().voiceEnabled
        })
      );
      } catch {
        return false;
      }
      set((state) => ({
        messages: [...state.messages, userMsg],
        orbState: 'thinking'
      }));
      return true;
    },

    decideApproval: async (requestId: string, decision: 'approve' | 'reject') => {
      set({actionError: null});
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
        if (!res.ok) {
          await get().fetchPendingApprovals();
          throw new Error('Decision was not accepted');
        }
        if (res.ok) {
          set((state) => ({
            pendingApprovals: state.pendingApprovals.filter((r) => r.id !== requestId),
            orbState: decision === 'approve' ? 'acting' : 'idle'
          }));
        }
      } catch (err) {
        set({actionError:'Your decision was not accepted. Refresh Activity and check whether the request expired.'});
      }
    },

    cancelSession: async () => {
      set({actionError: null, voiceConversation: false, pendingAudioMessageId: null});
      useAudioStore.getState().stopAudio();
      const token = useAuthStore.getState().token;
      const sessionId = get().currentSessionId;
      try {
        const response = await fetch(`/api/sessions/${sessionId}/cancel`, {
          method: 'POST',
          headers: { Authorization: `Bearer ${token}` }
        });
        if (!response.ok) throw new Error('Cancellation was not acknowledged');
        set({
          orbState: 'idle',
          currentTool: null,
          currentThought: null,
          pendingApprovals: []
        });
      } catch (err) {
        set({actionError:'Could not confirm cancellation. The task may still be running.'});
      }
    },

    triggerEmergencyStop: async () => {
      set({actionError: null, isEmergencyStopped: true, voiceConversation: false, pendingAudioMessageId: null});
      useAudioStore.getState().stopAudio();
      const token = useAuthStore.getState().token;
      try {
        const response = await fetch('/api/emergency-stop', {
          method: 'POST',
          headers: { Authorization: `Bearer ${token}` }
        });
        if (!response.ok) throw new Error('Stop was not acknowledged');
        set({
          isEmergencyStopped: true,
          orbState: 'error',
          currentTool: null,
          currentThought: null,
          pendingApprovals: []
        });
      } catch (err) {
        set({actionError:'Could not confirm the stop with Windows. The task may still be running.'});
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
