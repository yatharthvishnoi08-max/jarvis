import { useEffect, useRef, useState } from 'react';
import { ArrowUp, AudioLines, History, Mic, Plus, Volume2, X } from 'lucide-react';
import { useAuthStore } from '../stores/useAuthStore';
import type { Message, SessionMeta } from '../types';
import './basic-chat.css';

const activeKey = 'jarvis_basic_conversation';
const newId = () => 'chat_' + Array.from(crypto.getRandomValues(new Uint32Array(3)), n => n.toString(16)).join('');

export function BasicChat() {
  const token = useAuthStore(s => s.token);
  const [id, setId] = useState(() => localStorage.getItem(activeKey) || newId());
  const [sessions, setSessions] = useState<SessionMeta[]>([]);
  const [messages, setMessages] = useState<Message[]>([]);
  const [draft, setDraft] = useState('');
  const [pending, setPending] = useState('');
  const [ready, setReady] = useState(false);
  const [refresh, setRefresh] = useState(0);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [history, setHistory] = useState(false);
  const [listening, setListening] = useState(false);
  const [readAloud, setReadAloud] = useState(() => localStorage.getItem('jarvis_basic_voice') === 'on');
  const [audio, setAudio] = useState<{id: string; url: string} | null>(null);
  const [loadingAudio, setLoadingAudio] = useState('');
  const mic = useRef<any>(null);
  const audioRequest = useRef<AbortController | null>(null);
  const sending = useRef(false);
  const end = useRef<HTMLDivElement>(null);
  const input = useRef<HTMLTextAreaElement>(null);
  const headers = { Authorization: 'Bearer ' + token };

  useEffect(() => {
    const controller = new AbortController();
    localStorage.setItem(activeKey, id);
    setReady(false); setMessages([]); setError(''); setNotice(''); setAudio(null); setLoadingAudio('');
    const options = { headers: {Authorization: 'Bearer ' + token}, signal: controller.signal };
    (async () => {
      const res = await fetch('/api/sessions/' + id, options);
      if (!res.ok && res.status !== 404) throw new Error();
      const rows = res.ok ? (await res.json()).messages : [];
      if (!controller.signal.aborted) { setMessages(rows); setReady(true); }
    })().catch(() => { if (!controller.signal.aborted) setError('Could not open this chat. Check the gateway and retry.'); });
    fetch('/api/sessions', options).then(r => r.json()).then(data => {
      if (!controller.signal.aborted) setSessions((data.sessions || []).filter((s: SessionMeta) => s.id.startsWith('chat_')));
    }).catch(() => {});
    return () => { controller.abort(); audioRequest.current?.abort(); mic.current?.abort(); };
  }, [id, token, refresh]);

  useEffect(() => () => { if (audio) URL.revokeObjectURL(audio.url); }, [audio]);
  useEffect(() => { end.current?.scrollIntoView({block: 'end'}); }, [messages, pending, error]);

  async function send() {
    const text = draft.trim();
    if (!ready || !text || sending.current) return;
    sending.current = true;
    mic.current?.abort(); setPending(text); setDraft(''); setError(''); setNotice('');
    const controller = new AbortController();
    const timeout = window.setTimeout(() => controller.abort(), 105000);
    try {
      const res = await fetch('/api/chat', { method: 'POST', signal: controller.signal,
        headers: {...headers, 'Content-Type': 'application/json'}, body: JSON.stringify({session_id: id, text}) });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(typeof body.detail === 'string' ? body.detail : 'Could not send this message.');
      }
      const data = await res.json();
      if (!data.reply?.content || !data.user?.id) throw new Error('Unexpected gateway response. Check the installed version.');
      setMessages(prev => [...prev, data.user, data.reply]);
      if (readAloud) void speak(data.reply);
      setSessions(prev => [prev.find(s => s.id === id) || {id, title: text.slice(0, 36), created_at: Date.now()/1000, updated_at: Date.now()/1000},
        ...prev.filter(s => s.id !== id)]);
    } catch (err) {
      setError(controller.signal.aborted ? 'Reply timed out. Reopen the chat to check its history before resending.'
        : err instanceof Error ? err.message : 'Could not reach the gateway.');
      setDraft(text);
    } finally { clearTimeout(timeout); sending.current = false; setPending(''); }
  }

  function dictate() {
    if (mic.current) { mic.current.stop(); return; }
    const Recognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!window.isSecureContext || !Recognition) { setNotice('Use your keyboard microphone to dictate, then press Send.'); input.current?.focus(); return; }
    const recognition = new Recognition();
    mic.current = recognition;
    recognition.onresult = (e: any) => setDraft(old => [old, e.results[0][0].transcript].filter(Boolean).join(' '));
    recognition.onerror = () => setNotice('Microphone unavailable. Check browser permissions or use keyboard dictation.');
    recognition.onend = () => { mic.current = null; setListening(false); };
    try { recognition.start(); setListening(true); setNotice(''); }
    catch { mic.current = null; setNotice('Could not start the microphone. Try keyboard dictation.'); }
  }

  async function speak(message: Message) {
    audioRequest.current?.abort();
    const controller = new AbortController();
    audioRequest.current = controller;
    setLoadingAudio(message.id); setAudio(null); setNotice('');
    try {
      const res = await fetch('/api/sessions/' + id + '/replies/' + message.id + '/speech',
        {method: 'POST', headers, signal: controller.signal});
      if (!res.ok) throw new Error((await res.json()).detail || 'Voice unavailable.');
      const blob = await res.blob();
      if (!controller.signal.aborted) setAudio({id: message.id, url: URL.createObjectURL(blob)});
    } catch (err) { if (!controller.signal.aborted) setNotice(err instanceof Error ? err.message : 'Voice unavailable.'); }
    finally { if (!controller.signal.aborted) setLoadingAudio(''); }
  }

  function select(next: string) {
    setDraft(''); setHistory(false);
    if (next === id) setRefresh(v => v + 1);
    else setId(next);
  }
  return <main className="basic-chat">
    <header className="chat-bar"><div className="chat-wordmark"><AudioLines size={22}/> Jarvis</div>
      <nav aria-label="Chat controls">
        <button disabled={!!pending} onClick={() => setHistory(!history)} aria-expanded={history}><History size={17}/> History</button>
        <button disabled={!!pending} onClick={() => select(newId())}><Plus size={17}/> New chat</button>
        <a href="/workspace">Agent workspace ↗</a>
      </nav>
    </header>
    {history && <aside className="chat-history"><button aria-label="Close history" onClick={() => setHistory(false)}><X size={16}/></button>
      <h2>Conversations</h2>{sessions.length ? sessions.map(s => <button key={s.id} onClick={() => select(s.id)}>{s.title}</button>) : <p>No saved chats yet.</p>}</aside>}
    <section className="chat-feed" aria-label="Conversation"><div className="chat-column">
      {!messages.length && !pending && <div className="chat-welcome"><span className="chat-signal" aria-hidden="true"><AudioLines size={38}/></span>
        <h1>What’s on your mind?</h1><p>Type a message or use the microphone.</p></div>}
      {messages.filter(m => m.role === 'user' || m.role === 'assistant').map(m => <article key={m.id} className={'chat-turn ' + m.role}>
        <small>{m.role === 'user' ? 'You' : 'Jarvis'}</small><p>{m.content}</p>
        {m.role === 'assistant' && <button className="voice-action" onClick={() => speak(m)} disabled={loadingAudio === m.id}><Volume2 size={14}/>
          {loadingAudio === m.id ? 'Preparing audio…' : 'Listen'}</button>}
        {audio?.id === m.id && <audio controls autoPlay src={audio.url}/>}</article>)}
      {pending && <><article className="chat-turn user"><small>You</small><p>{pending}</p></article><p className="chat-status" role="status">Jarvis is thinking…</p></>}
      <div ref={end}/></div></section>
    <footer><div className="chat-column">
      {error && <p role="alert" className="chat-alert">{error} {!ready && <button onClick={() => setRefresh(v => v+1)}>Retry</button>}</p>}
      {notice && <p role="status" className="chat-alert">{notice}</p>}
      <form onSubmit={e => { e.preventDefault(); void send(); }}>
        <textarea ref={input} aria-label="Message Jarvis" maxLength={16000} rows={2} placeholder="Message Jarvis…" value={draft}
          disabled={!!pending} onChange={e => setDraft(e.target.value)} onKeyDown={e => {
            if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) { e.preventDefault(); void send(); }
          }}/>
        <div className="composer-actions"><button type="button" onClick={dictate} disabled={!!pending} aria-pressed={listening}><Mic size={17}/>{listening ? 'Finish dictation' : 'Dictate'}</button>
          <button type="button" aria-pressed={readAloud} onClick={() => {
            if (readAloud) { audioRequest.current?.abort(); setAudio(null); setLoadingAudio(''); }
            localStorage.setItem('jarvis_basic_voice', readAloud ? 'off' : 'on'); setReadAloud(!readAloud);
          }}><Volume2 size={16}/>{readAloud ? 'Read aloud on' : 'Read aloud off'}</button>
          <button className="send-turn" disabled={!draft.trim() || !ready || !!pending} type="submit" aria-label="Send message"><ArrowUp size={20}/></button></div>
      </form></div></footer>
  </main>;
}
