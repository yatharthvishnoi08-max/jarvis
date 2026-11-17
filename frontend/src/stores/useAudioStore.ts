import { create } from 'zustand';
import { VoiceMeta } from '../types';
import { useAuthStore } from './useAuthStore';

interface AudioState {
  activeAudioId: string | null;
  playbackState: 'idle' | 'generating' | 'buffering' | 'speaking' | 'stopped' | 'error';
  voices: VoiceMeta[];
  activeVoiceId: string;
  audioElement: HTMLAudioElement | null;
  fetchVoices: () => Promise<void>;
  selectVoice: (voiceId: string) => Promise<void>;
  playAudio: (url: string, audioId?: string) => void;
  stopAudio: () => void;
  replayAudio: (audioId: string) => void;
}

export const useAudioStore = create<AudioState>((set, get) => {
  const audio = typeof Audio !== 'undefined' ? new Audio() : null;

  if (audio) {
    audio.onplay = () => set({ playbackState: 'speaking' });
    audio.onended = () => set({ playbackState: 'idle', activeAudioId: null });
    audio.onerror = () => set({ playbackState: 'error' });
  }

  return {
    activeAudioId: null,
    playbackState: 'idle',
    voices: [],
    activeVoiceId: 'JBFqnCBsd6RMkjVDRZzb',
    audioElement: audio,

    fetchVoices: async () => {
      const token = useAuthStore.getState().token;
      try {
        const res = await fetch('/api/voices', {
          headers: { Authorization: `Bearer ${token}` }
        });
        if (res.ok) {
          const data = await res.json();
          set({ voices: data.voices, activeVoiceId: data.active_voice_id });
        }
      } catch (err) {
        console.error('Failed to fetch voices:', err);
      }
    },

    selectVoice: async (voiceId: string) => {
      const token = useAuthStore.getState().token;
      try {
        const res = await fetch('/api/voices/select', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`
          },
          body: JSON.stringify({ voice_id: voiceId })
        });
        if (res.ok) {
          set({ activeVoiceId: voiceId });
          get().fetchVoices();
        }
      } catch (err) {
        console.error('Failed to select voice:', err);
      }
    },

    playAudio: (url: string, audioId?: string) => {
      const el = get().audioElement;
      if (!el) return;

      el.pause();
      el.src = url;
      set({ playbackState: 'buffering', activeAudioId: audioId || null });
      el.play().catch((err) => {
        console.warn('Playback prevented by browser policy:', err);
        set({ playbackState: 'idle' });
      });
    },

    stopAudio: () => {
      const el = get().audioElement;
      if (el) {
        el.pause();
        el.currentTime = 0;
      }
      set({ playbackState: 'stopped', activeAudioId: null });
      setTimeout(() => {
        if (get().playbackState === 'stopped') {
          set({ playbackState: 'idle' });
        }
      }, 1000);
    },

    replayAudio: (audioId: string) => {
      get().playAudio(`/api/audio/${audioId}?t=${Date.now()}`, audioId);
    }
  };
});
