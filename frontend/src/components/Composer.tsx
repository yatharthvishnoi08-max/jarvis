import React, { useState, useEffect, useRef } from 'react';
import { useJarvisStore } from '../stores/useJarvisStore';
import { useAudioStore } from '../stores/useAudioStore';
import { VoiceConversation } from '../voice/VoiceConversation';
import { Send, Mic, MicOff, Square, WifiOff, RotateCw } from 'lucide-react';

export const Composer: React.FC<{text:string;setText:(value:string)=>void}> = ({text,setText}) => {
  const { sendMessage, orbState, cancelSession, isListening, setIsListening, ws, pendingApprovals, voiceConversation, setVoiceConversation } = useJarvisStore();
  const online = ws?.readyState === WebSocket.OPEN;
  const [micHint, setMicHint] = useState('');
  const { connectionError, retryConnection } = useJarvisStore();
  const [liveTranscript, setLiveTranscript] = useState('');
  const playbackState = useAudioStore(s => s.playbackState);
  const controllerRef = useRef<VoiceConversation | null>(null);

  useEffect(() => {
    const Recognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!Recognition || !window.isSecureContext) return;
    const controller = new VoiceConversation(() => new Recognition(), {
      send: transcript => { const accepted = sendMessage(transcript); if (!accepted) setText(transcript); return accepted; },
      listening: setIsListening,
      transcript: setLiveTranscript,
      error: message => { setMicHint(message); setVoiceConversation(false); },
    });
    controllerRef.current = controller;
    let session = useJarvisStore.getState().currentSessionId;
    const sync = () => {
      const state = useJarvisStore.getState();
      if (session !== state.currentSessionId || state.isEmergencyStopped || document.hidden || !state.ws || state.ws.readyState !== WebSocket.OPEN) {
        session = state.currentSessionId;
        if (state.voiceConversation) { setVoiceConversation(false); return; }
      }
      controller.setBlocked(!state.ws || state.ws.readyState !== WebSocket.OPEN ||
        state.pendingApprovals.length > 0 || ['thinking', 'acting', 'error', 'disconnected'].includes(state.orbState) ||
        ['generating', 'buffering', 'speaking'].includes(useAudioStore.getState().playbackState));
      if (state.voiceConversation) controller.start(); else controller.stop();
    };
    const stopJarvis = useJarvisStore.subscribe(sync);
    const stopAudio = useAudioStore.subscribe(sync);
    document.addEventListener('visibilitychange', sync);
    sync();
    return () => {
      stopJarvis(); stopAudio(); document.removeEventListener('visibilitychange', sync);
      controller.stop(); controllerRef.current = null; setVoiceConversation(false);
    };
  }, [sendMessage, setIsListening, setVoiceConversation, setText]);

  useEffect(() => {
    if (voiceConversation && (!(window as any).SpeechRecognition && !(window as any).webkitSpeechRecognition || !window.isSecureContext)) {
      setVoiceConversation(false);
      setMicHint('Voice needs Chrome or Edge with microphone access on localhost or HTTPS. You can still type here.');
    }
  }, [voiceConversation, setVoiceConversation]);

  const toggleMic = () => {
    setMicHint(''); setLiveTranscript('');
    if (voiceConversation) {
      setVoiceConversation(false); useJarvisStore.getState().setVoiceEnabled(false); useAudioStore.getState().stopAudio(); return;
    }
    if (!controllerRef.current) {
      setMicHint('Voice needs Chrome or Edge with microphone access on localhost or HTTPS. You can still type here.');
      return;
    }
    useJarvisStore.getState().setVoiceEnabled(true);
    setVoiceConversation(true);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!text.trim()) return;
    if (sendMessage(text.trim())) setText('');
  };

  const isBusy = orbState === 'thinking' || orbState === 'acting';
  const isConnected = online && orbState !== 'disconnected' && (orbState !== 'error' || pendingApprovals.length > 0);

  return (
    <div className="jarvis-composer">
      {!isConnected && (
        <div className="max-w-3xl mx-auto mb-3 flex items-center justify-between gap-3 rounded-xl border border-amber-500/30 bg-amber-950/30 px-3 py-2.5 text-xs text-amber-100">
          <div className="flex items-center gap-2 min-w-0">
            <WifiOff className="w-4 h-4 shrink-0 text-amber-400" />
            <span className="truncate">{connectionError || 'Connecting to the JARVIS realtime gateway…'}</span>
          </div>
          <button
            type="button"
            onClick={retryConnection}
            className="shrink-0 inline-flex items-center gap-1.5 rounded-lg border border-amber-400/40 bg-amber-400/10 px-2.5 py-1.5 font-mono font-semibold text-amber-200 hover:bg-amber-400/20"
          >
            <RotateCw className="w-3.5 h-3.5" />
            Retry
          </button>
          <a href="?view=basic">Open basic chat</a>
        </div>
      )}
      <form onSubmit={handleSubmit} className="max-w-3xl mx-auto flex items-center space-x-2">
        {/* Microphone Button */}
        <button
          type="button"
          onClick={toggleMic}
          disabled={!voiceConversation && (!isConnected || isBusy || pendingApprovals.length > 0)}
          className={`p-3 rounded-full border transition flex items-center justify-center shrink-0 shadow-lg ${
            isListening
              ? 'bg-red-950 border-red-500 text-red-400 animate-pulse'
              : 'bg-obsidian-850 border-cyan-500/40 text-cyan-400 hover:bg-cyan-950/60 active:scale-95 disabled:opacity-35 disabled:pointer-events-none'
          }`}
          aria-label={voiceConversation ? 'Stop voice conversation' : 'Start voice conversation'}
          aria-pressed={voiceConversation}
          title={voiceConversation ? 'Stop voice conversation' : 'Start voice conversation'}
        >
          {voiceConversation ? <MicOff className="w-5 h-5" /> : <Mic className="w-5 h-5" />}
        </button>

        {/* Text Input */}
        <div className="flex-1 relative">
          <input
            type="text"
            aria-label="Message Jarvis"
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder={
              isListening
                ? 'Listening to your voice... Speak now.'
                : 'Type to Jarvis while you talk…'
            }
            className="w-full bg-obsidian-850/90 border border-slate-800 rounded-full px-4 py-2.5 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-cyan-500/70 transition"
          />
        </div>

        {/* Action Button: Send or Stop */}
        {isBusy ? (
          <button
            type="button"
            onClick={cancelSession}
            className="p-2.5 rounded-full bg-red-950/60 border border-red-500/60 text-red-400 hover:bg-red-900/60 active:scale-95 transition flex items-center justify-center shrink-0"
            title="Cancel current task"
          >
            <Square className="w-4 h-4 fill-red-400" />
          </button>
        ) : (
          <button
            type="submit"
            disabled={!isConnected || !text.trim() || pendingApprovals.length > 0}
            className="p-2.5 rounded-full bg-jarvis-cyan text-obsidian-950 hover:bg-cyan-400 disabled:opacity-30 disabled:pointer-events-none active:scale-95 transition flex items-center justify-center shrink-0 font-bold"
            title="Send"
          >
            <Send className="w-4 h-4" />
          </button>
        )}
      </form>
      {voiceConversation && <div className="voice-conversation-status" role="status">
        <span className={isListening ? 'voice-dot listening' : 'voice-dot'}/>
        <span>{isListening ? 'Listening — go ahead' : pendingApprovals.length ? 'Waiting for your approval' : playbackState === 'speaking' ? 'Jarvis is speaking' : playbackState === 'generating' || playbackState === 'buffering' ? 'Preparing voice reply…' : isBusy ? 'Jarvis is thinking…' : 'Starting microphone…'}</span>
        <button type="button" onClick={toggleMic}>End conversation</button>
      </div>}
      {voiceConversation && liveTranscript && <p className="voice-live-transcript">{liveTranscript}</p>}
      {voiceConversation && playbackState === 'error' && <p role="status" className="voice-live-transcript">Voice playback failed. Your reply is in chat; use Replay Voice to try again.</p>}
      {micHint && <p role="status" className="max-w-3xl mx-auto mt-2 text-xs text-amber-200">{micHint}</p>}
    </div>
  );
};
