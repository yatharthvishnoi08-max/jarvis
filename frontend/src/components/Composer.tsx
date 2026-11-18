import React, { useState, useEffect, useRef } from 'react';
import { useJarvisStore } from '../stores/useJarvisStore';
import { Send, Mic, MicOff, Square, WifiOff, RotateCw } from 'lucide-react';

export const Composer: React.FC = () => {
  const [text, setText] = useState('');
  const [micHint, setMicHint] = useState('');
  const {
    sendMessage,
    orbState,
    cancelSession,
    isListening,
    setIsListening,
    connectionError,
    retryConnection
  } = useJarvisStore();
  const recognitionRef = useRef<any>(null);

  useEffect(() => {
    // Setup Browser Web Speech API if supported
    const SpeechRecognition =
      (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;

    if (SpeechRecognition) {
      const recognition = new SpeechRecognition();
      recognition.continuous = false;
      recognition.interimResults = false;
      recognition.lang = 'en-US';

      recognition.onstart = () => {
        setIsListening(true);
      };

      recognition.onresult = (event: any) => {
        const transcript = event.results[0][0].transcript;
        if (transcript) {
          if (!sendMessage(transcript)) setText(transcript);
        }
      };

      recognition.onerror = (event: any) => {
        console.warn('Speech recognition error:', event.error);
        setMicHint('Could not hear you. Check microphone permission or use your keyboard’s dictation.');
        setIsListening(false);
      };

      recognition.onend = () => {
        setIsListening(false);
      };

      recognitionRef.current = recognition;
      return () => {
        recognition.onresult = recognition.onstart = recognition.onerror = recognition.onend = null;
        recognition.abort();
        recognitionRef.current = null;
      };
    }
  }, [setIsListening, sendMessage]);

  const toggleMic = () => {
    setMicHint('');
    if (!window.isSecureContext || !recognitionRef.current) {
      setMicHint('Use your phone keyboard’s dictation, then tap Send. The in-app mic needs HTTPS and a supported browser.');
      return;
    }

    if (isListening) {
      recognitionRef.current.stop();
    } else {
      try {
        recognitionRef.current.start();
      } catch {
        setMicHint('Microphone unavailable. Use keyboard dictation or try again.');
      }
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!text.trim()) return;
    if (sendMessage(text.trim())) setText('');
  };

  const isBusy = orbState === 'thinking' || orbState === 'acting';
  const isConnected = orbState !== 'disconnected' && orbState !== 'error';

  return (
    <div className="p-3 sm:p-4 bg-obsidian-900/90 border-t border-slate-800/80 backdrop-blur-md">
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
        </div>
      )}
      <form onSubmit={handleSubmit} className="max-w-3xl mx-auto flex items-center space-x-2">
        {/* Microphone Button */}
        <button
          type="button"
          onClick={toggleMic}
          disabled={!isConnected || isBusy}
          className={`p-3 rounded-full border transition flex items-center justify-center shrink-0 shadow-lg ${
            isListening
              ? 'bg-red-950 border-red-500 text-red-400 animate-pulse'
              : 'bg-obsidian-850 border-cyan-500/40 text-cyan-400 hover:bg-cyan-950/60 active:scale-95 disabled:opacity-35 disabled:pointer-events-none'
          }`}
          title={isListening ? 'Stop Listening' : 'Tap to Speak'}
        >
          {isListening ? <MicOff className="w-5 h-5" /> : <Mic className="w-5 h-5" />}
        </button>

        {/* Text Input */}
        <div className="flex-1 relative">
          <input
            type="text"
            value={text}
            onChange={(e) => setText(e.target.value)}
            disabled={!isConnected}
            placeholder={
              isListening
                ? 'Listening to your voice... Speak now.'
                : !isConnected
                  ? 'Waiting for the realtime connection…'
                  : 'Message JARVIS, run a system tool, or coach an employee...'
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
            disabled={!text.trim() || !isConnected}
            className="p-2.5 rounded-full bg-jarvis-cyan text-obsidian-950 hover:bg-cyan-400 disabled:opacity-30 disabled:pointer-events-none active:scale-95 transition flex items-center justify-center shrink-0 font-bold"
            title="Send"
          >
            <Send className="w-4 h-4" />
          </button>
        )}
      </form>
      {micHint && <p role="status" className="max-w-3xl mx-auto mt-2 text-xs text-amber-200">{micHint}</p>}
    </div>
  );
};
