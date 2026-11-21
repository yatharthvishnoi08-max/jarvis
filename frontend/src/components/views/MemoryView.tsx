import React, { useEffect, useState } from 'react';
import { useAuthStore } from '../../stores/useAuthStore';
import { Brain, X, Plus, Search, Pencil, Archive, RotateCcw } from 'lucide-react';

interface MemoryRecord {
  id: number; category: string; rule: string; source: string;
  updated_at: string; expires_at: string | null; archived: number; expired: boolean; version: number; pinned: number;
}
interface MemoryViewProps { isOpen: boolean; onClose: () => void }

export const MemoryView: React.FC<MemoryViewProps> = ({ isOpen, onClose }) => {
  const [records, setRecords] = useState<MemoryRecord[]>([]);
  const [category, setCategory] = useState('USER_PREF');
  const [ruleText, setRuleText] = useState('');
  const [expiry, setExpiry] = useState('');
  const [pinned, setPinned] = useState(false);
  const [recallQuery, setRecallQuery] = useState('');
  const [recallResult, setRecallResult] = useState<{context: string; selected: {id: number}[]; characters: number; limit: number} | null>(null);
  const [showRecall, setShowRecall] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState<MemoryRecord | null>(null);
  const [search, setSearch] = useState('');
  const [showInactive, setShowInactive] = useState(false);
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [msg, setMsg] = useState('');
  const { token } = useAuthStore();
  const headers = { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' };

  const request = async (url: string, init?: RequestInit) => {
    const res = await fetch(url, { ...init, headers });
    if (!res.ok) {
      const detail = await res.json().catch(() => ({}));
      throw new Error(typeof detail.detail === 'string' ? detail.detail : `Request failed (${res.status}). Please try again.`);
    }
    return res.json();
  };
  const fetchMemory = async () => {
    const data = await request('/api/memory');
    if (!Array.isArray(data.records)) throw new Error('The host needs the memory update. Your existing memories are still stored there.');
    setRecords(data.records);
    if (!data.records.length) setShowForm(true);
  };
  const reload = async () => {
    setLoading(true); setError('');
    try { await fetchMemory(); } catch (err) { setError((err as Error).message); }
    finally { setLoading(false); }
  };
  useEffect(() => { if (isOpen) void reload(); }, [isOpen, token]);
  useEffect(() => {
    if (!isOpen) return;
    const close = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', close);
    return () => window.removeEventListener('keydown', close);
  }, [isOpen, onClose]);

  const resetForm = () => { setEditing(null); setRuleText(''); setExpiry(''); setPinned(false); setCategory('USER_PREF'); };
  const previewRecall = async () => {
    setBusy(true); setError(''); setRecallResult(null);
    try { setRecallResult(await request('/api/memory/recall', { method: 'POST', body: JSON.stringify({ query: recallQuery }) })); }
    catch (err) { setError((err as Error).message); }
    finally { setBusy(false); }
  };
  const save = async (e: React.FormEvent) => {
    e.preventDefault(); setBusy(true); setError(''); setMsg('');
    try {
      const values = { category, rule: ruleText.trim(), pinned, expires_at: expiry ? new Date(expiry).toISOString() : null };
      await request(editing ? `/api/memory/${editing.id}` : '/api/memory', {
        method: editing ? 'PUT' : 'POST',
        body: JSON.stringify(editing ? { ...values, version: editing.version, action: 'edit' } : values),
      });
      resetForm(); setRecallResult(null); setShowForm(false);
      setMsg('Saved. Jarvis can recall this memory when it is relevant.');
      await fetchMemory();
    } catch (err) { setError((err as Error).message); }
    finally { setBusy(false); }
  };
  const change = async (record: MemoryRecord, action: string) => {
    setBusy(true); setError(''); setMsg('');
    try {
      await request(`/api/memory/${record.id}`, { method: 'PUT', body: JSON.stringify({ version: record.version, action }) });
      if (editing?.id === record.id) resetForm();
      setRecallResult(null);
      setMsg(action === 'archive' ? 'Archived. Jarvis will stop using it. Restore it from Archived & expired.' : 'Memory updated.');
      await fetchMemory();
    } catch (err) { setError((err as Error).message); }
    finally { setBusy(false); }
  };
  const edit = (record: MemoryRecord) => {
    setEditing(record); setShowForm(true); setCategory(record.category); setRuleText(record.rule); setPinned(!!record.pinned); setError(''); setMsg('');
    const date = record.expires_at ? new Date(record.expires_at) : null;
    setExpiry(date ? new Date(date.getTime() - date.getTimezoneOffset() * 60000).toISOString().slice(0, 16) : '');
  };
  if (!isOpen) return null;
  const visible = records.filter(r => (showInactive ? r.archived || r.expired : !r.archived && !r.expired)
    && `${r.rule} ${r.category}`.toLowerCase().includes(search.toLowerCase()));
  const inputClass = 'w-full min-w-0 rounded-xl border border-white/10 bg-white/5 px-3 py-2.5 text-sm text-slate-100 focus:outline-none focus:border-pink-300';

  return (
    <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-3 sm:p-6">
      <section role="dialog" aria-modal="true" aria-labelledby="memory-title" className="bg-[#19191b] border border-white/10 rounded-3xl w-full max-w-3xl max-h-[90dvh] flex flex-col shadow-2xl overflow-hidden text-slate-200">
        <header className="p-5 border-b border-white/10 flex items-start justify-between shrink-0 gap-3">
          <div><div className="flex items-center gap-2"><Brain className="w-5 h-5 text-pink-300" /><h2 id="memory-title" className="font-semibold text-lg">Your memory</h2></div>
            <p className="text-xs text-slate-400 mt-2">What Jarvis remembers. Correct it, give it an expiry, or set it aside.</p></div>
          <button onClick={onClose} aria-label="Close memory" className="p-2 rounded-full hover:bg-white/10"><X size={18} /></button>
        </header>
        <div className="px-5 py-3 border-b border-white/10 flex flex-wrap items-center gap-3">
          <label className="flex items-center gap-2 flex-1 min-w-0"><Search size={16} className="text-slate-500 shrink-0" /><input aria-label="Search memories" placeholder="Search memories" value={search} onChange={e => setSearch(e.target.value)} className="bg-transparent min-w-0 w-full text-sm outline-none" /></label>
          <button onClick={() => setShowInactive(!showInactive)} className="text-xs text-pink-200 rounded-lg px-2 py-2 hover:bg-white/5">{showInactive ? 'Active memories' : 'Archived & expired'}</button>
          <button disabled={busy} onClick={() => void reload()} className="text-xs text-slate-400">Reload</button>
          <button onClick={() => setShowRecall(!showRecall)} className="text-xs text-pink-200">Test recall</button>
        </div>
        {error && <p role="alert" className="mx-5 mt-3 p-3 rounded-xl bg-red-400/10 text-red-200 text-sm">{error}</p>}
        {msg && <p role="status" className="px-5 pt-3 text-xs text-emerald-300">{msg}</p>}
        <div className="flex-1 min-h-0 overflow-y-auto p-5 space-y-3">
          {showRecall && <div className="p-4 rounded-2xl border border-pink-300/20 space-y-3">
            <p className="text-xs text-slate-400">Try a message to see which saved memories Jarvis would use. Core preferences have priority; other memories are matched to your message.</p>
            <input aria-label="Recall test message" maxLength={2000} placeholder="What should I prepare for the Atlas meeting?" value={recallQuery} onChange={e => {setRecallQuery(e.target.value); setRecallResult(null);}} className={inputClass} />
            <button disabled={busy} onClick={() => void previewRecall()} className="text-sm text-pink-200 disabled:opacity-40">Preview recall</button>
            {recallResult && <div role="status" className="text-xs space-y-2"><p className="text-slate-400">{recallResult.selected.length} memories selected · {recallResult.characters} / {recallResult.limit} characters · Local keyword search</p><pre className="font-sans whitespace-pre-wrap break-words leading-relaxed">{recallResult.context}</pre></div>}
          </div>}
          {loading ? <p className="text-sm text-slate-400">Loading memories…</p> : visible.length === 0 && !error ? <p className="text-sm text-slate-400">{search ? 'No matching memories.' : showInactive ? 'No archived or expired memories.' : 'Add a preference below, or ask Jarvis to remember one in chat.'}</p> : null}
          {visible.map(record => <article key={record.id} className="rounded-2xl bg-white/[0.03] border border-white/10 p-4">
            <div className="flex gap-2 items-center flex-wrap text-[10px] uppercase tracking-widest text-pink-200"><span>{record.category.replace(/_/g, ' ')}</span>{!!record.pinned && <span>Core preference</span>}{!!record.archived && <span className="text-slate-400">Archived</span>}{record.expired && <span className="text-amber-300">Expired</span>}</div>
            <p className="text-sm leading-relaxed my-2 whitespace-pre-wrap break-words">{record.rule}</p>
            <p className="text-[11px] text-slate-500">{record.source} · Updated {new Date(record.updated_at).toLocaleDateString()}{record.expires_at ? ` · Expires ${new Date(record.expires_at).toLocaleString()}` : ''}</p>
            <div className="flex flex-wrap gap-4 mt-3 text-xs text-slate-400">
              <button disabled={busy} onClick={() => edit(record)} className="flex gap-1 items-center hover:text-pink-200"><Pencil size={13} />Edit</button>
              <button disabled={busy} onClick={() => void change(record, record.archived ? 'restore' : 'archive')} className="flex gap-1 items-center hover:text-pink-200"><Archive size={13} />{record.archived ? 'Restore' : 'Archive'}</button>
              {record.version > 1 && <button disabled={busy} onClick={() => void change(record, 'undo')} className="flex gap-1 items-center hover:text-pink-200"><RotateCcw size={13} />Undo last change</button>}
            </div>
          </article>)}
        </div>
        {showForm ? <form onSubmit={save} className="shrink-0 max-h-[48dvh] overflow-y-auto p-4 sm:p-5 border-t border-white/10 space-y-3">
          <div className="flex items-center justify-between text-sm"><span>{editing ? 'Edit memory' : 'Remember something'}</span><button type="button" onClick={() => { resetForm(); setShowForm(false); }} className="text-xs text-slate-400">{editing ? 'Cancel edit' : 'Close form'}</button></div>
          <textarea required aria-label="Memory text" maxLength={4000} rows={2} value={ruleText} onChange={e => setRuleText(e.target.value)} placeholder="I prefer short replies and a morning plan at 9." className={inputClass} />
          <label className="flex items-center gap-2 text-xs text-slate-400"><input type="checkbox" checked={pinned} onChange={e => setPinned(e.target.checked)} />Core preference — prioritize in every conversation</label>
          <div className="flex flex-wrap items-end gap-3">
            <label className="text-[11px] text-slate-400 flex-1 min-w-[100px]">Category<input aria-label="Memory category" maxLength={40} required value={category} onChange={e => setCategory(e.target.value)} className={`${inputClass} mt-1`} /></label>
            <label className="text-[11px] text-slate-400 flex-1 min-w-[180px]">Expiry (optional)<input aria-label="Memory expiry" type="datetime-local" value={expiry} onChange={e => setExpiry(e.target.value)} className={`${inputClass} mt-1 [color-scheme:dark]`} /></label>
            <button disabled={busy || loading || !ruleText.trim()} type="submit" className="flex gap-1 items-center justify-center rounded-xl bg-pink-200 text-[#24171d] px-4 py-3 text-sm font-semibold disabled:opacity-40"><Plus size={16} />{busy ? 'Saving…' : 'Save'}</button>
          </div>
        </form> : <footer className="shrink-0 p-4 border-t border-white/10"><button onClick={() => {resetForm(); setShowForm(true);}} className="flex items-center gap-2 rounded-xl bg-pink-200 text-[#24171d] px-4 py-2 text-sm font-semibold"><Plus size={16} />Add memory</button></footer>}
      </section>
    </div>
  );
};
