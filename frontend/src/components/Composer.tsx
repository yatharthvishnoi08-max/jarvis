import React from 'react';
import { useJarvisStore } from '../stores/useJarvisStore';
import { useAudioStore } from '../stores/useAudioStore';
import { useVoiceStore } from '../stores/useVoiceStore';
import { Send, Mic, MicOff, Square, WifiOff, RotateCw } from 'lucide-react';

export const Composer: React.FC<{text:string;setText:(value:string)=>void}> = ({text,setText}) => {
  const { sendMessage, orbState, cancelSession, isListening, ws, pendingApprovals, voiceConversation, setVoiceConversation } = useJarvisStore();
  const online = ws?.readyState === WebSocket.OPEN;
  const { hint: micHint, transcript: liveTranscript, wakeEnabled, setWakeEnabled, retryMicrophone, bargeStatus, inputLevel, unlockInterruption } = useVoiceStore();
  const { connectionError, retryConnection } = useJarvisStore();
  const playbackState = useAudioStore(s => s.playbackState);
  const toggleMic = () => {
    if (voiceConversation) {
      setVoiceConversation(false); setWakeEnabled(false);
      useJarvisStore.getState().interruptSpeech(); return;
    }
    if (micHint) retryMicrophone(); useJarvisStore.getState().setVoiceEnabled(true); setVoiceConversation(true);
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
              isListening && voiceConversation
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
      <div className="voice-conversation-status" role="status">
        <span className={isListening ? 'voice-dot listening' : 'voice-dot'}/>
        <span>{micHint ? 'Microphone needs attention' : pendingApprovals.length ? 'Waiting for your approval' : isBusy ? 'Jarvis is thinking…' : playbackState === 'speaking' ? 'Speaking — talk to interrupt' : playbackState === 'generating' || playbackState === 'buffering' ? 'Preparing reply — you can interrupt' : isListening ? voiceConversation ? 'Listening — go ahead' : 'Say “Hey Jarvis”' : wakeEnabled ? 'Starting wake-word listener…' : 'Microphone off'}</span>
        {(voiceConversation || wakeEnabled) && <button type="button" onClick={() => {setWakeEnabled(false);setVoiceConversation(false);useJarvisStore.getState().interruptSpeech();}}>Microphone off</button>}
      </div>
      <div className="voice-conversation-status">
        <button type="button" aria-pressed={wakeEnabled} onClick={() => {setWakeEnabled(!wakeEnabled); if (!wakeEnabled) retryMicrophone();}}>Hey Jarvis: {wakeEnabled ? 'on' : 'off'}</button>
        {micHint && <button type="button" onClick={() => {setWakeEnabled(true);retryMicrophone();}}>Enable microphone</button>}
        <small>Keep this tab open. “Stop listening” returns to standby. Browser speech recognition may use an online service.</small>
      </div>
      {(voiceConversation || wakeEnabled) && <div className="voice-conversation-status">
        <span>Interruption: {bargeStatus === 'ready' ? 'ready' : bargeStatus === 'needs-click' ? 'needs one-time audio permission' : bargeStatus === 'starting' ? 'starting' : 'microphone audio unavailable'}</span>
        <meter aria-label="Microphone level" min="0" max="0.12" value={inputLevel}/>
        {bargeStatus === 'needs-click' && <button type="button" onClick={unlockInterruption}>Enable interruption</button>}
      </div>}
      {voiceConversation && liveTranscript && <p className="voice-live-transcript">{liveTranscript}</p>}
      {playbackState === 'error' && <p role="status" className="voice-live-transcript">Browser blocked or failed voice playback. Click Replay Voice once to enable sound.</p>}
      {micHint && <p role="alert" className="voice-live-transcript">{micHint}</p>}

    </div>
  );
};
