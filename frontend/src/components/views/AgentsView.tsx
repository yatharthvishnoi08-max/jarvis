import React, { useEffect, useState } from 'react';
import { Employee } from '../../types';
import { useAuthStore } from '../../stores/useAuthStore';
import { Users, X, Edit3, Check } from 'lucide-react';

interface AgentsViewProps {
  isOpen: boolean;
  onClose: () => void;
}

export const AgentsView: React.FC<AgentsViewProps> = ({ isOpen, onClose }) => {
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [selected, setSelected] = useState<Employee | null>(null);
  const [newRule, setNewRule] = useState('');
  const [isUpdating, setIsUpdating] = useState(false);
  const [msg, setMsg] = useState('');
  const { token } = useAuthStore();

  const fetchTeam = async () => {
    try {
      const res = await fetch('/api/team', {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setEmployees(data.employees || []);
        if (data.employees.length > 0 && !selected) {
          setSelected(data.employees[0]);
        }
      }
    } catch (err) {
      console.error('Failed to fetch team:', err);
    }
  };

  useEffect(() => {
    if (isOpen) {
      fetchTeam();
    }
  }, [isOpen]);

  const handleUpdateSOP = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selected || !newRule.trim()) return;

    setIsUpdating(true);
    try {
      const res = await fetch(`/api/team/${selected.name}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({ rule: newRule.trim() })
      });
      if (res.ok) {
        setMsg('SOP updated successfully.');
        setNewRule('');
        fetchTeam();
        setTimeout(() => setMsg(''), 3000);
      }
    } catch (err) {
      console.error('Failed to update SOP:', err);
    } finally {
      setIsUpdating(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-3 sm:p-6 animate-fade-in">
      <div className="bg-obsidian-900 border border-slate-800 rounded-2xl w-full max-w-4xl h-[85vh] flex flex-col shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="p-4 border-b border-slate-800 flex items-center justify-between shrink-0">
          <div className="flex items-center space-x-2">
            <Users className="w-5 h-5 text-jarvis-cyan" />
            <h2 className="text-base font-bold text-cyan-300 hud-title tracking-wider uppercase">
              Employee Agent Roster & Guidelines
            </h2>
          </div>
          <button onClick={onClose} className="p-1 text-slate-400 hover:text-white">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content Body */}
        <div className="flex-1 flex flex-col md:flex-row overflow-hidden">
          {/* Agent Selector Sidebar */}
          <div className="w-full md:w-56 border-b md:border-b-0 md:border-r border-slate-800 p-3 space-y-1 overflow-y-auto">
            {employees.map((emp) => (
              <button
                key={emp.name}
                onClick={() => setSelected(emp)}
                className={`w-full text-left px-3 py-2.5 rounded-lg text-xs font-mono transition ${
                  selected?.name === emp.name
                    ? 'bg-cyan-950/60 border border-cyan-500/50 text-cyan-300'
                    : 'text-slate-400 hover:bg-obsidian-850 hover:text-slate-200'
                }`}
              >
                <div className="font-bold uppercase tracking-wider">{emp.name}</div>
                <div className="text-[10px] text-slate-500 truncate">{emp.summary}</div>
              </button>
            ))}
          </div>

          {/* Details & SOP View */}
          <div className="flex-1 p-4 overflow-y-auto flex flex-col space-y-4">
            {selected ? (
              <>
                <div className="space-y-1">
                  <h3 className="text-sm font-bold text-white font-mono uppercase">
                    Role: {selected.name}
                  </h3>
                  <p className="text-xs text-slate-400 font-mono">{selected.summary}</p>
                </div>

                {/* SOP Editor/Preview */}
                <div className="flex-1 min-h-[160px] p-3 rounded-xl bg-obsidian-950 border border-slate-800 text-xs font-mono text-slate-300 whitespace-pre-wrap overflow-y-auto">
                  {selected.sop}
                </div>

                {/* Quick Rule Append */}
                <form onSubmit={handleUpdateSOP} className="space-y-2 pt-2 border-t border-slate-800">
                  <label className="text-xs font-mono text-cyan-400 font-semibold block">
                    Coach Employee (Append New SOP Rule):
                  </label>
                  <div className="flex space-x-2">
                    <input
                      type="text"
                      value={newRule}
                      onChange={(e) => setNewRule(e.target.value)}
                      placeholder="e.g. Always include type annotations and error checks..."
                      className="flex-1 bg-obsidian-850 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:border-cyan-500/60 font-mono"
                    />
                    <button
                      type="submit"
                      disabled={isUpdating || !newRule.trim()}
                      className="px-4 py-2 rounded-lg bg-jarvis-cyan text-obsidian-950 text-xs font-bold font-mono hover:bg-cyan-400 disabled:opacity-30 transition flex items-center space-x-1"
                    >
                      <Check className="w-3.5 h-3.5" />
                      <span>Update</span>
                    </button>
                  </div>
                  {msg && <div className="text-xs text-emerald-400 font-mono">{msg}</div>}
                </form>
              </>
            ) : (
              <div className="text-xs text-slate-500 font-mono text-center my-auto">
                Select an employee to view SOP.
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
