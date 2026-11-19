import React, { useState, useEffect, useRef } from 'react';
import { useJarvisStore } from '../stores/useJarvisStore';
import { Send, Mic, MicOff, Square } from 'lucide-react';

export const Composer: React.FC = () => {
  const [text, setText] = useState('');
  const { sendMessage, orbState, cancelSession, isListening, setIsListening, ws, pendingApprovals } = useJarvisStore();
  const online = ws?.readyState === WebSocket.OPEN;
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
        setIsListening(false);
      };

      recognition.onend = () => {
        setIsListening(false);
      };

      recognitionRef.current = recognition;
      return () => {
        recognition.onresult = recognition.onerror = recognition.onend = recognition.onstart = null;
        recognition.abort();
      };
    }
  }, [setIsListening, sendMessage]);

  const toggleMic = () => {
    if (!recognitionRef.current) {
      alert('Speech recognition is not supported in this browser. Use Chrome, Edge, or Safari.');
      return;
    }

    if (isListening) {
      recognitionRef.current.stop();
    } else {
      recognitionRef.current.start();
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!text.trim()) return;
    if (sendMessage(text.trim())) setText('');
  };

  const isBusy = orbState === 'thinking' || orbState === 'acting';

  return (
    <div className="jarvis-composer">
      {!online && <p role="status">Gateway offline. You can keep typing while Jarvis reconnects.</p>}
      <form onSubmit={handleSubmit} className="max-w-3xl mx-auto flex items-center space-x-2">
        {/* Microphone Button */}
        <button
          type="button"
          onClick={toggleMic}
          disabled={!online || isBusy || pendingApprovals.length > 0}
          className={`p-3 rounded-full border transition flex items-center justify-center shrink-0 shadow-lg ${
            isListening
              ? 'bg-red-950 border-red-500 text-red-400 animate-pulse'
              : 'bg-obsidian-850 border-cyan-500/40 text-cyan-400 hover:bg-cyan-950/60 active:scale-95'
          }`}
          title={isListening ? 'Stop Listening' : 'Tap to Speak'}
        >
          {isListening ? <MicOff className="w-5 h-5" /> : <Mic className="w-5 h-5" />}
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
                : 'Message Jarvis…'
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
            disabled={!online || !text.trim() || pendingApprovals.length > 0}
            className="p-2.5 rounded-full bg-jarvis-cyan text-obsidian-950 hover:bg-cyan-400 disabled:opacity-30 disabled:pointer-events-none active:scale-95 transition flex items-center justify-center shrink-0 font-bold"
            title="Send"
          >
            <Send className="w-4 h-4" />
          </button>
        )}
      </form>
    </div>
  );
};
