import { useEffect } from 'react';
import { MicrophoneInput } from './MicrophoneInput';
import { VoiceConversation } from './VoiceConversation';
import { useJarvisStore } from '../stores/useJarvisStore';
import { useAudioStore } from '../stores/useAudioStore';
import { useVoiceStore } from '../stores/useVoiceStore';

/** Mounted once for the whole authenticated app, including Planner and Settings. */
export function VoiceAssistant({onUnsent, onWake}: {onUnsent: (text: string) => void; onWake: () => void}) {
  const retry = useVoiceStore(s => s.retry);
  const wakeEnabled = useVoiceStore(s => s.wakeEnabled);
  const conversation = useJarvisStore(s => s.voiceConversation);
  const wanted = wakeEnabled || conversation;
  useEffect(() => {
    if (!wanted) return;
    const Recognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!Recognition || !window.isSecureContext) {
      useVoiceStore.setState({hint: 'Voice needs Chrome or Edge at http://localhost:8000 or HTTPS. This page cannot start speech recognition.'});
      return;
    }
    let disposed = false, syncing = false, release: (() => void) | undefined;
    let ownsMic = false;
    const lockAbort = new AbortController();
    let session = useJarvisStore.getState().currentSessionId;
    const capture = new MicrophoneInput({
      speaking: () => useAudioStore.getState().playbackState === 'speaking' && controller.awake,
      interrupt: () => controller.interruptFromMicrophone(),
      status: bargeStatus => { if (!disposed) useVoiceStore.setState({bargeStatus}); },
      level: inputLevel => { if (!disposed) useVoiceStore.setState({inputLevel}); },
    });
    useVoiceStore.setState({bargeStatus: 'starting', unlockInterruption: () => {void capture.unlock();}});
    const controller = new VoiceConversation(() => new Recognition(), {
      startRecognition: recognition => capture.startRecognition(recognition),
      send: text => {
        const accepted = useJarvisStore.getState().sendMessage(text);
        if (!accepted) onUnsent(text);
        return accepted;
      },
      listening: value => useJarvisStore.getState().setIsListening(value),
      awake: value => { if (disposed) return; useJarvisStore.getState().setVoiceConversation(value); if (value) { useJarvisStore.getState().setVoiceEnabled(true); onWake(); } },
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
    const openMicrophone = async () => {
      try {
        await capture.open();
        if (disposed) return;
        ownsMic = true; useVoiceStore.setState({hint: ''}); sync();
      } catch (error) {
        if (!disposed) useVoiceStore.setState({hint: error instanceof DOMException && error.name === 'NotAllowedError'
          ? 'Allow microphone access for this page, then click Enable microphone once.'
          : 'Could not open your microphone. Check the selected input device and click Enable microphone.'});
      }
    };
    if (navigator.locks) {
      useVoiceStore.setState({hint: 'Waiting for microphone access. Close other Jarvis tabs if this message stays here.'});
      void navigator.locks.request('jarvis-voice-microphone', {signal: lockAbort.signal}, async () => {
        if (disposed) return;
        // Create release before awaiting permission so unmount cannot strand the lock.
        const held = new Promise<void>(resolve => { release = resolve; });
        await Promise.race([openMicrophone(), held]);
        await held;
      }).catch(() => { if (!disposed) useVoiceStore.setState({hint: 'Could not reserve the microphone. Reload this page to retry.'}); });
    } else { void openMicrophone(); }

    sync();
    return () => { disposed = true; unsub.forEach(fn => fn()); controller.stop(); capture.close(); lockAbort.abort(); release?.(); };
  }, [onUnsent, onWake, retry, wanted]);
  return null;
}
