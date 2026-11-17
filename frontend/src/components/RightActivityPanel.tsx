import React, { useEffect } from 'react';
import { useJarvisStore } from '../stores/useJarvisStore';
import { useActivityStore } from '../stores/useActivityStore';
import { ApprovalRequest } from '../types';
import { ShieldCheck, ShieldAlert, Check, X, Clock, Terminal, Activity, AlertTriangle } from 'lucide-react';

interface RightActivityPanelProps {
  isOpen: boolean;
  onClose: () => void;
}

export const RightActivityPanel: React.FC<RightActivityPanelProps> = ({
  isOpen,
  onClose
}) => {
  const { pendingApprovals, decideApproval } = useJarvisStore();
  const { events, fetchActivity } = useActivityStore();

  useEffect(() => {
    fetchActivity();
    const interval = setInterval(fetchActivity, 5000);
    return () => clearInterval(interval);
  }, [fetchActivity]);

  return (
    <>
      {/* Mobile Backdrop */}
      {isOpen && (
        <div
          onClick={onClose}
          className="fixed inset-0 bg-black/60 backdrop-blur-sm z-40 xl:hidden"
        />
      )}

      <aside
        className={`fixed xl:static top-0 right-0 h-full w-80 bg-obsidian-900 border-l border-slate-800/80 flex flex-col z-50 transition-transform duration-300 ease-in-out ${
          isOpen ? 'translate-x-0' : 'translate-x-full xl:translate-x-0'
        }`}
      >
        {/* Panel Header */}
        <div className="p-3.5 border-b border-slate-800 flex items-center justify-between shrink-0">
          <div className="flex items-center space-x-2">
            <Activity className="w-4 h-4 text-jarvis-cyan" />
            <span className="font-bold text-xs font-hud tracking-wider uppercase text-cyan-300">
              Activity & Approvals
            </span>
          </div>
          <button onClick={onClose} className="p-1 text-slate-400 hover:text-white xl:hidden">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content Container */}
        <div className="flex-1 overflow-y-auto p-3 space-y-4">
          {/* Pending Approvals Section */}
          <div>
            <div className="flex items-center justify-between pb-2">
              <span className="text-[10px] font-mono uppercase tracking-wider text-slate-400 font-bold flex items-center space-x-1.5">
                <ShieldCheck className="w-3.5 h-3.5 text-amber-400" />
                <span>Pending Approvals ({pendingApprovals.length})</span>
              </span>
            </div>

            {pendingApprovals.length === 0 ? (
              <div className="p-3 rounded-lg bg-obsidian-850/60 border border-slate-800 text-center text-xs text-slate-500 font-mono">
                No pending tool approvals.
              </div>
            ) : (
              <div className="space-y-2.5">
                {pendingApprovals.map((req) => (
                  <ApprovalCard key={req.id} req={req} onDecide={decideApproval} />
                ))}
              </div>
            )}
          </div>

          {/* Audit History Log */}
          <div className="pt-2 border-t border-slate-800/80">
            <div className="pb-2">
              <span className="text-[10px] font-mono uppercase tracking-wider text-slate-400 font-bold">
                Audit Trail (Live)
              </span>
            </div>

            <div className="space-y-2">
              {events.length === 0 ? (
                <div className="text-xs text-slate-500 font-mono p-3 text-center">
                  No activity recorded yet.
                </div>
              ) : (
                events.map((ev, idx) => (
                  <div
                    key={idx}
                    className="p-2 rounded-lg bg-obsidian-850/80 border border-slate-800/70 text-[11px] font-mono space-y-1"
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-cyan-400 font-semibold">{ev.event_type}</span>
                      <span className="text-[10px] text-slate-500">
                        {new Date(ev.timestamp * 1000).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </span>
                    </div>

                    {ev.tool && (
                      <div className="text-slate-300 flex items-center space-x-1 truncate">
                        <Terminal className="w-3 h-3 text-slate-500 shrink-0" />
                        <span className="truncate">{ev.tool}</span>
                      </div>
                    )}

                    <div className="flex items-center justify-between text-[10px] pt-0.5">
                      <span
                        className={`px-1.5 py-0.2 rounded font-bold ${
                          ev.status === 'BLOCKED'
                            ? 'bg-red-950 text-red-400 border border-red-800'
                            : ev.status === 'APPROVED'
                            ? 'bg-emerald-950 text-emerald-400'
                            : 'bg-slate-800 text-slate-300'
                        }`}
                      >
                        {ev.status}
                      </span>
                      <span className="text-slate-500 truncate max-w-[150px]">{ev.detail}</span>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      </aside>
    </>
  );
};

const ApprovalCard: React.FC<{
  req: ApprovalRequest;
  onDecide: (id: string, decision: 'approve' | 'reject') => void;
}> = ({ req, onDecide }) => {
  const isCritical = req.policy_level === 'CRITICAL';

  return (
    <div
      className={`p-3 rounded-xl border text-xs font-mono space-y-2 ${
        isCritical
          ? 'bg-red-950/30 border-red-500/60 shadow-red-glow'
          : 'bg-amber-950/20 border-amber-500/50 shadow-amber-glow'
      }`}
    >
      {/* Header */}
      <div className="flex items-center justify-between">
        <span
          className={`px-2 py-0.5 rounded text-[10px] font-bold tracking-wider uppercase flex items-center space-x-1 ${
            isCritical ? 'bg-red-900/60 text-red-300' : 'bg-amber-900/60 text-amber-300'
          }`}
        >
          {isCritical ? <ShieldAlert className="w-3 h-3 mr-1" /> : <AlertTriangle className="w-3 h-3 mr-1" />}
          <span>{req.policy_level} OPERATION</span>
        </span>

        <span className="text-[10px] text-slate-400 flex items-center space-x-1">
          <Clock className="w-3 h-3" />
          <span>{req.ttl_remaining}s TTL</span>
        </span>
      </div>

      {/* Tool info */}
      <div>
        <div className="text-slate-300 font-semibold">{req.tool}</div>
        <pre className="text-[10px] p-2 rounded bg-obsidian-950 border border-slate-800/80 text-cyan-200 overflow-x-auto mt-1 max-h-24">
          {JSON.stringify(req.args, null, 2)}
        </pre>
      </div>

      {/* Summary warning */}
      <div className="text-[11px] text-slate-400">{req.summary}</div>

      {/* Decision Buttons */}
      <div className="flex items-center space-x-2 pt-1">
        <button
          onClick={() => onDecide(req.id, 'approve')}
          className="flex-1 py-1.5 px-3 rounded-lg bg-emerald-600/80 hover:bg-emerald-500 text-white font-bold flex items-center justify-center space-x-1 active:scale-95 transition"
        >
          <Check className="w-3.5 h-3.5" />
          <span>Approve</span>
        </button>

        <button
          onClick={() => onDecide(req.id, 'reject')}
          className="flex-1 py-1.5 px-3 rounded-lg bg-red-900/60 hover:bg-red-800 text-red-200 font-bold flex items-center justify-center space-x-1 active:scale-95 transition"
        >
          <X className="w-3.5 h-3.5" />
          <span>Reject</span>
        </button>
      </div>
    </div>
  );
};
