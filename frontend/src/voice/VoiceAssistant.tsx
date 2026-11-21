import { useEffect } from 'react';
import { VoiceConversation } from './VoiceConversation';
import { useJarvisStore } from '../stores/useJarvisStore';
import { useAudioStore } from '../stores/useAudioStore';
import { useVoiceStore } from '../stores/useVoiceStore';

/** Mounted once for the whole authenticated app, including Planner and Settings. */
export function VoiceAssistant({onUnsent}: {onUnsent: (text: string) => void}) {
  const retry = useVoiceStore(s => s.retry);
  useEffect(() => {
    const Recognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!Recognition || !window.isSecureContext) {
      useVoiceStore.setState({hint: 'Voice needs Chrome or Edge at http://localhost:8000 or HTTPS. This page cannot start speech recognition.'});
      return;
    }
    let disposed = false, syncing = false, release: (() => void) | undefined;
    let ownsMic = !navigator.locks;
    let session = useJarvisStore.getState().currentSessionId;
    const controller = new VoiceConversation(() => new Recognition(), {
      send: text => {
        const accepted = useJarvisStore.getState().sendMessage(text);
        if (!accepted) onUnsent(text);
        return accepted;
      },
      listening: value => useJarvisStore.getState().setIsListening(value),
      awake: value => { useJarvisStore.getState().setVoiceConversation(value); if (value) useJarvisStore.getState().setVoiceEnabled(true); },
      transcript: text => useVoiceStore.setState({transcript: text}),
      interrupt: () => useJarvisStore.getState().interruptSpeech(),
      error: hint => useVoiceStore.setState({hint}),
    });
    const sync = () => {
      if (disposed || syncing) return;
      syncing = true;
      try {
        const state = useJarvisStore.getState(), voice = useVoiceStore.getState();
        const changedSession = session !== state.currentSessionId;
        session = state.currentSessionId;
        if (changedSession) controller.stop();
        const blocked = !ownsMic || !state.currentSessionId || !state.ws || state.ws.readyState !== WebSocket.OPEN ||
          state.isEmergencyStopped || !!voice.hint || state.pendingApprovals.length > 0 ||
          ['thinking', 'acting', 'error', 'disconnected'].includes(state.orbState);
        const audio = useAudioStore.getState();
        const activeReply = state.messages.find(m => m.audio_id === audio.activeAudioId) ||
          [...state.messages].reverse().find(m => m.role === 'assistant');
        controller.setPlayback(['speaking', 'buffering', 'generating'].includes(audio.playbackState), activeReply?.content || '');
        controller.setBlocked(blocked);
        if (state.isEmergencyStopped || voice.hint || (!voice.wakeEnabled && !state.voiceConversation)) controller.stop();
        else controller.start(!useJarvisStore.getState().voiceConversation);
      } finally { syncing = false; }
    };
    const unsub = [useJarvisStore.subscribe(sync), useAudioStore.subscribe(sync), useVoiceStore.subscribe(sync)];
    if (navigator.locks) {
      void navigator.locks.request('jarvis-voice-microphone', {ifAvailable: true}, async lock => {
        if (disposed) return;
        if (!lock) { useVoiceStore.setState({hint: 'Another Jarvis tab owns the microphone. Close that tab, then click Enable microphone here.'}); return; }
        ownsMic = true; sync();
        await new Promise<void>(resolve => { release = resolve; });
      }).catch(() => useVoiceStore.setState({hint: 'Could not reserve the microphone. Reload this page to retry.'}));
    }
    sync();
    return () => { disposed = true; unsub.forEach(fn => fn()); controller.stop(); release?.(); };
  }, [onUnsent, retry]);
  return null;
}
