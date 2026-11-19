import React, { useEffect, useRef } from 'react';
import { useJarvisStore } from '../stores/useJarvisStore';
import { useAudioStore } from '../stores/useAudioStore';
import { Play, Square, Bot, User, Wrench, Folder, Activity, Users, ArrowUpRight } from 'lucide-react';
import DOMPurify from 'dompurify';
import { marked } from 'marked';

export const ChatArea: React.FC = () => {
  const { messages, orbState, currentTool, currentThought, sendMessage, ws, pendingApprovals } = useJarvisStore();
  const { activeAudioId, playbackState, replayAudio, stopAudio } = useAudioStore();
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, currentTool, currentThought]);

  const renderMarkdown = (content: string) => {
    try {
      return { __html: DOMPurify.sanitize(marked.parse(content) as string) };
    } catch {
      return { __html: DOMPurify.sanitize(content) };
    }
  };

  return (
    <div className="jarvis-feed flex-1 overflow-y-auto px-3 sm:px-6 py-6 space-y-5">
      {/* Empty State / Welcome HUD */}
      {messages.length === 0 && <section className="jarvis-start">
        <div className="signal-field" aria-hidden="true"><div className="signal-core">{Array.from({length:22}, (_, i) =>
          <i key={i} style={{transform: `rotate(${i * 8.2}deg) scaleX(.38)`}} />)}</div></div>
        <h1>What’s on your mind?</h1>
        <p>Talk to Jarvis or start with a message.</p>
        <div className="jarvis-shortcuts">{[
          {label:'Check my system', icon:Activity, prompt:'Check my laptop system telemetry and available memory.'},
          {label:'Find recent files', icon:Folder, prompt:'List the 5 most recent files in my Downloads folder.'},
          {label:'Meet my agents', icon:Users, prompt:'What is the current team roster and operational rules?'}
        ].map(({label, icon: Icon, prompt}) => <button key={label} disabled={ws?.readyState !== WebSocket.OPEN} onClick={() => sendMessage(prompt)}>
          <Icon size={16}/>{label}<ArrowUpRight size={14}/></button>)}</div>
      </section>}

      {/* Messages Feed */}
      {messages.map((msg) => {
        const isUser = msg.role === 'user';
        const isAssistant = msg.role === 'assistant';
        const isTool = msg.role === 'tool';

        if (isTool) {
          return (
            <div key={msg.id} className="max-w-3xl mx-auto pl-10 text-xs font-mono text-slate-400">
              <div className="p-2.5 rounded-lg bg-obsidian-850 border border-slate-800/80 space-y-1">
                <div className="text-[10px] uppercase font-bold text-slate-500 flex items-center space-x-1.5">
                  <Wrench className="w-3 h-3 text-cyan-400" />
                  <span>Tool Output</span>
                </div>
                <div className="text-slate-300 whitespace-pre-wrap max-h-36 overflow-y-auto">
                  {msg.content}
                </div>
              </div>
            </div>
          );
        }

        return (
          <div
            key={msg.id}
            className={`max-w-3xl mx-auto flex items-start space-x-3 ${
              isUser ? 'flex-row-reverse space-x-reverse' : ''
            }`}
          >
            {/* Avatar */}
            <div
              className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 border ${
                isUser
                  ? 'bg-cyan-950/80 border-cyan-500/50 text-cyan-300'
                  : 'bg-obsidian-850 border-cyan-900/60 text-jarvis-cyan'
              }`}
            >
              {isUser ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
            </div>

            {/* Bubble */}
            <div
              className={`flex-1 rounded-2xl p-4 text-sm leading-relaxed ${
                isUser
                  ? 'bg-cyan-950/40 border border-cyan-500/40 text-cyan-100 rounded-tr-sm ml-12'
                  : 'bg-obsidian-900/90 border border-slate-800/80 text-slate-200 rounded-tl-sm mr-12 shadow-lg'
              }`}
            >
              {/* Tool Calls Chips inside Assistant message */}
              {msg.tool_calls && msg.tool_calls.length > 0 && (
                <div className="mb-2 space-y-1">
                  {msg.tool_calls.map((tc) => (
                    <div
                      key={tc.id}
                      className="inline-flex items-center space-x-1.5 px-2.5 py-1 rounded-md bg-cyan-950/80 border border-cyan-800/60 text-cyan-300 text-xs font-mono"
                    >
                      <Wrench className="w-3 h-3" />
                      <span>{tc.function.name}</span>
                    </div>
                  ))}
                </div>
              )}

              {/* Message Content */}
              {isUser ? (
                <div className="whitespace-pre-wrap">{msg.content}</div>
              ) : (
                <div
                  className="prose prose-invert prose-sm max-w-none prose-pre:bg-obsidian-950 prose-pre:border prose-pre:border-slate-800"
                  dangerouslySetInnerHTML={renderMarkdown(msg.content)}
                />
              )}

              {/* Unique Audio Playback Control */}
              {msg.audio_id && (
                <div className="mt-3 pt-2.5 border-t border-slate-800/60 flex items-center justify-between text-xs font-mono">
                  <div className="flex items-center space-x-2">
                    {activeAudioId === msg.audio_id && playbackState === 'speaking' ? (
                      <button
                        onClick={stopAudio}
                        className="px-2 py-1 rounded bg-amber-950/60 border border-amber-600/60 text-amber-300 flex items-center space-x-1 hover:bg-amber-900/60 transition"
                      >
                        <Square className="w-3 h-3 fill-amber-300" />
                        <span>Stop</span>
                      </button>
                    ) : (
                      <button
                        onClick={() => replayAudio(msg.audio_id!)}
                        className="px-2.5 py-1 rounded bg-cyan-950/80 border border-cyan-600/60 text-cyan-300 flex items-center space-x-1 hover:bg-cyan-900/60 transition"
                      >
                        <Play className="w-3 h-3 fill-cyan-300" />
                        <span>Replay Voice</span>
                      </button>
                    )}
                    <span className="text-[10px] text-slate-500">{msg.audio_id}</span>
                  </div>
                </div>
              )}
            </div>
          </div>
        );
      })}

      {/* Live Tool Execution Spinner */}
      {currentTool && (
        <div className="max-w-3xl mx-auto flex items-center space-x-3 pl-11">
          <div className="px-3.5 py-2 rounded-xl bg-cyan-950/50 border border-cyan-500/40 text-cyan-300 text-xs font-mono flex items-center space-x-2.5 shadow-md">
            <span className="relative flex h-2.5 w-2.5">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-cyan-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-cyan-500"></span>
            </span>
            <span>Running:</span>
            <span className="font-bold text-white">{currentTool.name}</span>
          </div>
        </div>
      )}

      {/* Live Thought Bubble */}
      {currentThought && (
        <div className="max-w-3xl mx-auto flex items-center space-x-3 pl-11">
          <div className="p-3 rounded-xl bg-obsidian-850/80 border border-slate-800 text-slate-400 text-xs italic font-mono max-w-lg">
            Thinking: {currentThought}
          </div>
        </div>
      )}

      {orbState === 'thinking' && !currentThought && <p className="turn-status" role="status">Jarvis is thinking…</p>}
      {pendingApprovals.length > 0 && <p className="turn-status" role="status">Waiting for your decision in Activity.</p>}
      <div ref={bottomRef} />
    </div>
  );
};
