import { useEffect, useState } from 'react';
import { CalendarDays, Inbox, Mail, RefreshCw } from 'lucide-react';
import { useAuthStore } from '../stores/useAuthStore';

type Snapshot = {
  state: 'disconnected' | 'connected' | 'sync_error';
  checked_at: string | null;
  inbox: {id: string; title: string; sender: string; unread: boolean}[];
  events: {id: string; title: string; start: string}[];
};

export function WorkspaceInbox({initial}: {initial: 'Inbox' | 'Calendar'}) {
  const token = useAuthStore(s => s.token);
  const [snapshot, setSnapshot] = useState<Snapshot>();
  const [error, setError] = useState(false);
  const [attempt, setAttempt] = useState(0);
  const [tab, setTab] = useState(initial);
  useEffect(() => {
    const controller = new AbortController();
    async function load() {
      try {
        const r = await fetch('/api/workspace', {headers: {Authorization: 'Bearer ' + token}, signal: controller.signal});
        if (!r.ok) throw new Error();
        const data = await r.json();
        if (!Array.isArray(data.inbox) || !Array.isArray(data.events)) throw new Error();
        if (!controller.signal.aborted) {setSnapshot(data); setError(false);}
      } catch {if (!controller.signal.aborted) setError(true);}
    }
    void load(); const t = setInterval(load, 30000);
    return () => {controller.abort(); clearInterval(t);};
  }, [token, attempt]);
  const connected = snapshot?.state === 'connected';
  return <section className="planner-page workspace-inbox">
    <header><Inbox/><h2>Google Workspace</h2></header>
    <div className="workspace-tabs" aria-label="Workspace view">{(['Inbox','Calendar'] as const).map(label=>
      <button key={label} aria-pressed={tab===label} onClick={()=>setTab(label)}>{label==='Inbox'?<Mail size={16}/>:<CalendarDays size={16}/>} {label}</button>)}</div>
    {error ? <p role="alert">Gateway unavailable. <button onClick={()=>setAttempt(v=>v+1)}><RefreshCw size={14}/>Retry</button></p>
    : !snapshot ? <p>Loading connection…</p>
    : snapshot.state==='disconnected' ? <><h3>Connect your Google account on the Jarvis host</h3>
      <p>Save your Google desktop client as <code>~/.config/jarvis/google-desktop.json</code>, then run <code>python -m tools.google_workspace</code> in the Jarvis environment. Inbox and calendar sync every five minutes after sign-in.</p></>
    : <>{!connected && <p role="alert">Sync failed. Check the Google connection on the host.</p>}
      {snapshot.checked_at && <p>Last synced {new Date(snapshot.checked_at).toLocaleString()}</p>}
      {tab === 'Inbox' ? <><h3>Recent incoming threads</h3><ul>{snapshot.inbox.map(t=>
        <li key={t.id}><Mail size={16}/><div><a href={'https://mail.google.com/mail/#all/'+encodeURIComponent(t.id)} target="_blank" rel="noreferrer">{t.title}</a><p>{t.sender}</p></div></li>)}</ul>
        {connected && !snapshot.inbox.length && <p>No recent incoming threads.</p>}</> :
      <><h3>Next seven days</h3><ul>{snapshot.events.map(e=>
        <li key={e.id}><CalendarDays size={16}/><span>{e.title}</span><small>{e.start?.length===10 ? e.start : new Date(e.start).toLocaleString()}</small></li>)}</ul>
        {connected && !snapshot.events.length && <p>No upcoming events.</p>}</>}</>}
  </section>;
}
