import { useCallback, useEffect, useState } from 'react';
import { CalendarDays, Check, ListChecks, Plus } from 'lucide-react';
import { useAuthStore } from '../stores/useAuthStore';

type Task = { id: number; title: string; due: string | null };

export function Planner() {
  const token = useAuthStore(s => s.token);
  const [tasks, setTasks] = useState<Task[] | null>(null);
  const [title, setTitle] = useState('');
  const [due, setDue] = useState('');
  const [busy, setBusy] = useState(false);
  const [feedback, setFeedback] = useState('');
  const [failed, setFailed] = useState(false);
  const request = useCallback(async (url: string, options?: RequestInit) => {
    const res = await fetch(url, {...options, headers: {
      Authorization: 'Bearer ' + token, 'Content-Type': 'application/json'
    }});
    if (!res.ok) throw new Error('Planner request failed');
    return res.json();
  }, [token]);
  const refresh = useCallback(async (signal?: AbortSignal) => {
    const data = await request('/api/planner', {signal});
    if (!Array.isArray(data.tasks)) throw new Error('Planner unavailable');
    if (!signal?.aborted) { setTasks(data.tasks); setFailed(false); }
  }, [request]);
  useEffect(() => {
    const controller = new AbortController();
    refresh(controller.signal).catch(() => { if (!controller.signal.aborted) setFailed(true); });
    return () => controller.abort();
  }, [refresh]);

  async function save(id?: number) {
    if (busy) return;
    setBusy(true); setFeedback('');
    try {
      const result = await request(id ? '/api/planner/' + id + '/complete' : '/api/planner', {
        method: 'POST', body: id ? undefined : JSON.stringify({title: title.trim(), due: due || null})
      });
      if (!id) { setTitle(''); setDue(''); }
      setFeedback(result.message);
      await refresh();
    } catch { setFailed(true); }
    finally { setBusy(false); }
  }

  return <section className="planner-page">
    <header><ListChecks/><h2>My commitments</h2></header>
    <form onSubmit={e => {e.preventDefault(); if (title.trim()) void save();}}>
      <label>Task<input value={title} maxLength={300} onChange={e=>setTitle(e.target.value)} placeholder="What do you need to follow up on?" required/></label>
      <label>Due date<input type="date" value={due} onChange={e=>setDue(e.target.value)}/></label>
      <button disabled={busy || !title.trim()}><Plus size={16}/>Add task</button>
    </form>
    {failed && <p role="alert">Couldn’t sync with the planner. <button onClick={()=>void refresh().catch(()=>setFailed(true))}>Retry</button></p>}
    <p role="status">{feedback}</p>
    <h3>Open tasks{tasks && <small>{tasks.length}</small>}</h3>
    {tasks === null ? !failed && <p>Loading tasks…</p> : tasks.length === 0 ? <p>No open tasks.</p> :
      <ul>{tasks.map(task=><li key={task.id}>
        <button disabled={busy} aria-label={'Complete ' + task.title} onClick={()=>void save(task.id)}><Check size={16}/></button>
        <span>{task.title}</span>{task.due && <small><CalendarDays size={13}/>{task.due}</small>}
      </li>)}</ul>}
  </section>;
}
