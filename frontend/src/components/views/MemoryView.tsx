import React, { useEffect, useState } from 'react';
import { useAuthStore } from '../../stores/useAuthStore';
import { Brain, X, Plus, Search, Check } from 'lucide-react';

interface MemoryViewProps {
  isOpen: boolean;
  onClose: () => void;
}

export const MemoryView: React.FC<MemoryViewProps> = ({ isOpen, onClose }) => {
  const [memory, setMemory] = useState('');
  const [category, setCategory] = useState('WORKFLOW');
  const [ruleText, setRuleText] = useState('');
  const [search, setSearch] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [msg, setMsg] = useState('');
  const { token } = useAuthStore();

  const fetchMemory = async () => {
    try {
      const res = await fetch('/api/memory', {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setMemory(data.memory || '');
      }
    } catch (err) {
      console.error('Failed to fetch memory:', err);
    }
  };

  useEffect(() => {
    if (isOpen) {
      fetchMemory();
    }
  }, [isOpen]);

  const handleAddRule = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!ruleText.trim()) return;

    setIsSubmitting(true);
    try {
      const res = await fetch('/api/memory', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({ category, rule: ruleText.trim() })
      });
      if (res.ok) {
        setMsg('Rule logged to persistent memory.');
        setRuleText('');
        fetchMemory();
        setTimeout(() => setMsg(''), 3000);
      }
    } catch (err) {
      console.error('Failed to add memory rule:', err);
    } finally {
      setIsSubmitting(false);
    }
  };

  if (!isOpen) return null;

  const filteredLines = search
    ? memory.split('\n').filter((line) => line.toLowerCase().includes(search.toLowerCase()))
    : memory.split('\n');

  return (
    <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-3 sm:p-6 animate-fade-in">
      <div className="bg-obsidian-900 border border-slate-800 rounded-2xl w-full max-w-3xl h-[80vh] flex flex-col shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="p-4 border-b border-slate-800 flex items-center justify-between shrink-0">
          <div className="flex items-center space-x-2">
            <Brain className="w-5 h-5 text-jarvis-cyan" />
            <h2 className="text-base font-bold text-cyan-300 hud-title tracking-wider uppercase">
              JARVIS Persistent Memory & Heuristics
            </h2>
          </div>
          <button onClick={onClose} className="p-1 text-slate-400 hover:text-white">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Search Bar */}
        <div className="p-3 border-b border-slate-800/80 bg-obsidian-950/60 flex items-center space-x-2">
          <Search className="w-4 h-4 text-slate-500 ml-1" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search learned rules and habits..."
            className="flex-1 bg-transparent text-xs text-slate-200 placeholder-slate-500 focus:outline-none font-mono"
          />
        </div>

        {/* Memory Content */}
        <div className="flex-1 p-4 overflow-y-auto font-mono text-xs text-slate-300 leading-relaxed whitespace-pre-wrap bg-obsidian-950/40">
          {filteredLines.join('\n')}
        </div>

        {/* Add Rule Form */}
        <form onSubmit={handleAddRule} className="p-4 border-t border-slate-800 bg-obsidian-900 space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono font-semibold text-cyan-400">Add Learned Rule / Habit:</span>
            {msg && <span className="text-xs text-emerald-400 font-mono">{msg}</span>}
          </div>

          <div className="flex flex-col sm:flex-row space-y-2 sm:space-y-0 sm:space-x-2">
            <select
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              className="bg-obsidian-850 border border-slate-800 rounded-lg px-2.5 py-2 text-xs text-slate-200 focus:outline-none focus:border-cyan-500 font-mono"
            >
              <option value="WORKFLOW">WORKFLOW</option>
              <option value="POWERSHELL">POWERSHELL</option>
              <option value="USER_PREF">USER_PREF</option>
              <option value="SAFETY">SAFETY</option>
            </select>

            <input
              type="text"
              value={ruleText}
              onChange={(e) => setRuleText(e.target.value)}
              placeholder="e.g. Wrap all paths containing spaces in double quotes..."
              className="flex-1 bg-obsidian-850 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:border-cyan-500 font-mono"
            />

            <button
              type="submit"
              disabled={isSubmitting || !ruleText.trim()}
              className="px-4 py-2 rounded-lg bg-jarvis-cyan text-obsidian-950 text-xs font-bold font-mono hover:bg-cyan-400 disabled:opacity-30 transition flex items-center justify-center space-x-1"
            >
              <Plus className="w-4 h-4" />
              <span>Record</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
