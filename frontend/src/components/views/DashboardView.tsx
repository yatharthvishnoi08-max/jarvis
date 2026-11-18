import React, { useState, useEffect, useCallback } from 'react';
import { useTelemetryStore } from '../../stores/useTelemetryStore';
import { useJarvisStore } from '../../stores/useJarvisStore';
import { useAuthStore } from '../../stores/useAuthStore';
import {
  Cpu,
  Activity,
  HardDrive,
  Server,
  Shield,
  ShieldAlert,
  ShieldCheck,
  Wifi,
  Zap,
  Brain,
  Users,
  Terminal,
  Volume2,
  RefreshCw,
  Play,
  CheckCircle2,
  XCircle,
  Clock,
  CloudSun,
  Globe,
  Sparkles,
  ExternalLink,
  Lock,
  ArrowRight
} from 'lucide-react';

interface DashboardViewProps {
  onSwitchToChat: () => void;
  onOpenAgentsModal: () => void;
  onOpenMemoryModal: () => void;
  onOpenSettingsModal: () => void;
}

interface SkillItem {
  name: string;
  description: string;
  tags?: string[];
}

interface TeamMember {
  name: string;
  summary: string;
}

interface DigestData {
  markdown: string;
  spoken_script: string;
  timestamp: string;
}

interface TracesSummary {
  total_traces: number;
  exemplars_count: number;
}

interface ActivityEvent {
  timestamp: number;
  event_type: string;
  tool: string;
  status: string;
  detail: string;
  policy: string;
}

export const DashboardView: React.FC<DashboardViewProps> = ({
  onSwitchToChat,
  onOpenAgentsModal,
  onOpenMemoryModal,
  onOpenSettingsModal
}) => {
  const { telemetry, fetchTelemetry } = useTelemetryStore();
  const {
    orbState,
    pendingApprovals,
    decideApproval,
    triggerEmergencyStop,
    isEmergencyStopped,
    sendMessage
  } = useJarvisStore();
  const { token } = useAuthStore();

  const [skills, setSkills] = useState<SkillItem[]>([]);
  const [team, setTeam] = useState<TeamMember[]>([]);
  const [digest, setDigest] = useState<DigestData | null>(null);
  const [traces, setTraces] = useState<TracesSummary>({ total_traces: 0, exemplars_count: 0 });
  const [recentEvents, setRecentEvents] = useState<ActivityEvent[]>([]);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [isEvolving, setIsEvolving] = useState(false);
  const [evolveMessage, setEvolveMessage] = useState<string | null>(null);
  const [isPlayingDigestAudio, setIsPlayingDigestAudio] = useState(false);

  // Load all dashboard auxiliary endpoints
  const loadDashboardData = useCallback(async () => {
    if (!token) return;
    setIsRefreshing(true);
    try {
      // 1. Telemetry
      await fetchTelemetry();

      // 2. Skills
      try {
        const res = await fetch('/api/skills', { headers: { Authorization: `Bearer ${token}` } });
        if (res.ok) {
          const data = await res.json();
          setSkills(data.skills || []);
        }
      } catch {}

      // 3. Team
      try {
        const res = await fetch('/api/team', { headers: { Authorization: `Bearer ${token}` } });
        if (res.ok) {
          const data = await res.json();
          setTeam(data.employees || []);
        }
      } catch {}

      // 4. Digest
      try {
        const res = await fetch('/api/digest', { headers: { Authorization: `Bearer ${token}` } });
        if (res.ok) {
          const data = await res.json();
          setDigest(data);
        }
      } catch {}

      // 5. Traces
      try {
        const res = await fetch('/api/traces', { headers: { Authorization: `Bearer ${token}` } });
        if (res.ok) {
          const data = await res.json();
          setTraces({
            total_traces: data.total_traces || (data.traces ? data.traces.length : 0),
            exemplars_count: data.exemplars ? data.exemplars.length : 0
          });
        }
      } catch {}

      // 6. Recent Activity
      try {
        const res = await fetch('/api/activity', { headers: { Authorization: `Bearer ${token}` } });
        if (res.ok) {
          const data = await res.json();
          setRecentEvents(data.events ? data.events.slice(-8).reverse() : []);
        }
      } catch {}
    } finally {
      setIsRefreshing(false);
    }
  }, [token, fetchTelemetry]);

  useEffect(() => {
    loadDashboardData();
    const interval = setInterval(loadDashboardData, 8000);
    return () => clearInterval(interval);
  }, [loadDashboardData]);

  // Trigger continuous learning self-evolution
  const handleEvolvePrompt = async () => {
    if (!token || isEvolving) return;
    setIsEvolving(true);
    setEvolveMessage(null);
    try {
      const res = await fetch('/api/learning/evolve', {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setEvolveMessage(
          data.status === 'optimal'
            ? 'Memory optimal. System rules current.'
            : `Evolved successfully: ${data.new_rules_applied?.length || 0} rules updated.`
        );
      } else {
        setEvolveMessage('Evolution skipped. No negative feedback traces.');
      }
    } catch {
      setEvolveMessage('Unable to trigger evolution.');
    } finally {
      setIsEvolving(false);
      setTimeout(() => setEvolveMessage(null), 5000);
    }
  };

  // Launch a skill directly in chat
  const handleLaunchSkill = (skillName: string) => {
    sendMessage(`Execute skill: ${skillName}`);
    onSwitchToChat();
  };

  const formatUptime = (seconds?: number) => {
    if (!seconds) return '--';
    const hrs = Math.floor(seconds / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    return `${hrs}h ${mins}m`;
  };

  return (
    <div className="flex-1 h-full overflow-y-auto bg-obsidian-950 p-4 sm:p-6 lg:p-8 space-y-6 font-mono text-slate-200">
      {/* 1. Executive Mission Control Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-cyan-900/40 pb-5">
        <div>
          <div className="flex items-center space-x-2.5">
            <div className="w-3 h-3 rounded-full bg-cyan-400 animate-pulse shadow-[0_0_10px_#22d3ee]" />
            <h1 className="text-xl sm:text-2xl font-hud font-black text-white tracking-widest uppercase">
              J.A.R.V.I.S. MISSION CONTROL
            </h1>
            <span className="text-[10px] px-2 py-0.5 rounded bg-cyan-950 text-cyan-300 border border-cyan-800 uppercase tracking-wider font-bold">
              DEFCON 5 // SECURE
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Autonomous Operating System & Zero-Trust Intelligence Hub (Nous Hermes Brain)
          </p>
        </div>

        {/* Header Action Controls */}
        <div className="flex flex-wrap items-center gap-2 text-xs">
          <button
            onClick={loadDashboardData}
            disabled={isRefreshing}
            className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-obsidian-850 hover:bg-obsidian-800 border border-slate-700/80 text-cyan-300 transition active:scale-95"
            title="Refresh all metrics"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isRefreshing ? 'animate-spin text-cyan-400' : ''}`} />
            <span>Sync</span>
          </button>

          <button
            onClick={onSwitchToChat}
            className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-cyan-950/80 hover:bg-cyan-900 border border-cyan-500/50 text-cyan-300 font-bold transition shadow-sm active:scale-95"
          >
            <Terminal className="w-3.5 h-3.5 text-cyan-400" />
            <span>Open Chat Deck</span>
            <ArrowRight className="w-3 h-3" />
          </button>

          <button
            onClick={triggerEmergencyStop}
            className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-lg border font-bold transition active:scale-95 ${
              isEmergencyStopped
                ? 'bg-red-700 text-white border-red-500 animate-pulse'
                : 'bg-red-950/40 text-red-400 border-red-800/80 hover:bg-red-900/60'
            }`}
          >
            <ShieldAlert className="w-3.5 h-3.5" />
            <span>Abort</span>
          </button>
        </div>
      </div>

      {/* 2. Critical Alert Banner: Pending Tool Approvals */}
      {pendingApprovals.length > 0 && (
        <div className="p-4 rounded-xl bg-amber-950/40 border border-amber-600/60 text-amber-200 animate-pulse flex flex-col sm:flex-row sm:items-center justify-between gap-3 shadow-lg">
          <div className="flex items-center space-x-3">
            <ShieldAlert className="w-6 h-6 text-amber-400 shrink-0" />
            <div>
              <div className="font-bold text-sm">SECURITY APPROVAL REQUIRED ({pendingApprovals.length} PENDING)</div>
              <div className="text-xs text-amber-300/80">
                A tool execution request requires your explicit authorization before running on this host.
              </div>
            </div>
          </div>
          <div className="flex items-center space-x-2 shrink-0">
            {pendingApprovals.slice(0, 1).map((req) => (
              <div key={req.id} className="flex space-x-2">
                <button
                  onClick={() => decideApproval(req.id, 'approve')}
                  className="px-3 py-1.5 rounded bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs shadow"
                >
                  Authorize ({req.tool})
                </button>
                <button
                  onClick={() => decideApproval(req.id, 'reject')}
                  className="px-3 py-1.5 rounded bg-red-600 hover:bg-red-500 text-white font-bold text-xs"
                >
                  Block
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 3. Row 1: Executive KPI Stat Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Processor (CPU) Card */}
        <div className="p-4 rounded-xl bg-obsidian-900/90 border border-cyan-900/40 relative overflow-hidden shadow-md flex flex-col justify-between">
          <div className="flex items-center justify-between text-slate-400 text-xs">
            <span className="uppercase tracking-wider font-bold flex items-center space-x-1.5">
              <Cpu className="w-4 h-4 text-cyan-400" />
              <span>Host Processor</span>
            </span>
            <span className="text-[10px] text-cyan-400/80 font-mono">
              {telemetry?.hostname || 'Host'}
            </span>
          </div>
          <div className="my-3 flex items-baseline space-x-2">
            <div className="text-3xl font-black text-cyan-300 font-hud">
              {telemetry ? `${telemetry.cpu_percent}%` : '--%'}
            </div>
            <div className="text-[10px] text-slate-400 uppercase">Load Utilization</div>
          </div>
          {/* Progress Bar */}
          <div className="w-full h-1.5 bg-obsidian-950 rounded-full overflow-hidden border border-slate-800">
            <div
              className="h-full bg-gradient-to-r from-cyan-500 to-cyan-300 transition-all duration-500"
              style={{ width: `${Math.min(100, telemetry?.cpu_percent || 0)}%` }}
            />
          </div>
        </div>

        {/* System Memory (RAM) Card */}
        <div className="p-4 rounded-xl bg-obsidian-900/90 border border-cyan-900/40 relative overflow-hidden shadow-md flex flex-col justify-between">
          <div className="flex items-center justify-between text-slate-400 text-xs">
            <span className="uppercase tracking-wider font-bold flex items-center space-x-1.5">
              <Activity className="w-4 h-4 text-cyan-400" />
              <span>Memory (RAM)</span>
            </span>
            <span className="text-[10px] text-slate-400">
              {telemetry ? `${telemetry.ram_used_mb}MB / ${telemetry.ram_total_mb}MB` : '--'}
            </span>
          </div>
          <div className="my-3 flex items-baseline space-x-2">
            <div className="text-3xl font-black text-cyan-300 font-hud">
              {telemetry ? `${telemetry.ram_percent}%` : '--%'}
            </div>
            <div className="text-[10px] text-slate-400 uppercase">Active Allocation</div>
          </div>
          <div className="w-full h-1.5 bg-obsidian-950 rounded-full overflow-hidden border border-slate-800">
            <div
              className="h-full bg-gradient-to-r from-cyan-500 to-emerald-400 transition-all duration-500"
              style={{ width: `${Math.min(100, telemetry?.ram_percent || 0)}%` }}
            />
          </div>
        </div>

        {/* Disk Storage Card */}
        <div className="p-4 rounded-xl bg-obsidian-900/90 border border-cyan-900/40 relative overflow-hidden shadow-md flex flex-col justify-between">
          <div className="flex items-center justify-between text-slate-400 text-xs">
            <span className="uppercase tracking-wider font-bold flex items-center space-x-1.5">
              <HardDrive className="w-4 h-4 text-cyan-400" />
              <span>Storage (Disk C:)</span>
            </span>
            <span className="text-[10px] text-emerald-400 font-bold">
              {telemetry ? `${telemetry.disk_free_gb} GB Free` : '--'}
            </span>
          </div>
          <div className="my-3 flex items-baseline space-x-2">
            <div className="text-3xl font-black text-cyan-300 font-hud">
              {telemetry ? `${telemetry.disk_percent}%` : '--%'}
            </div>
            <div className="text-[10px] text-slate-400 uppercase">
              Total {telemetry ? `${telemetry.disk_total_gb} GB` : '--'}
            </div>
          </div>
          <div className="w-full h-1.5 bg-obsidian-950 rounded-full overflow-hidden border border-slate-800">
            <div
              className="h-full bg-gradient-to-r from-cyan-500 to-blue-400 transition-all duration-500"
              style={{ width: `${Math.min(100, telemetry?.disk_percent || 0)}%` }}
            />
          </div>
        </div>

        {/* Neural Core & Gateway Vitals */}
        <div className="p-4 rounded-xl bg-obsidian-900/90 border border-cyan-900/40 relative overflow-hidden shadow-md flex flex-col justify-between">
          <div className="flex items-center justify-between text-slate-400 text-xs">
            <span className="uppercase tracking-wider font-bold flex items-center space-x-1.5">
              <Zap className="w-4 h-4 text-cyan-400" />
              <span>Neural Subsystems</span>
            </span>
            <span className="text-[10px] text-cyan-400 uppercase font-bold">ONLINE</span>
          </div>
          <div className="my-2 space-y-1 text-xs">
            <div className="flex justify-between">
              <span className="text-slate-500">Brain:</span>
              <span className="text-cyan-300 font-bold truncate max-w-[150px]">
                {telemetry?.active_model ? telemetry.active_model.split('/').pop() : 'Hermes-3'}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500">Voice TTS:</span>
              <span className="text-emerald-400 font-bold">ElevenLabs (Active)</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500">STT Engine:</span>
              <span className="text-cyan-300 font-bold">Local Whisper (Offline)</span>
            </div>
          </div>
          <div className="text-[10px] text-slate-500 flex justify-between pt-1 border-t border-slate-800/80">
            <span>Uptime: {formatUptime(telemetry?.uptime_seconds)}</span>
            <span className="text-emerald-400 font-bold">Encrypted TLS</span>
          </div>
        </div>
      </div>

      {/* 4. Row 2: Executive Situation Report & Daily Digest */}
      {digest && (
        <div className="p-5 rounded-xl bg-obsidian-900 border border-cyan-900/40 shadow-xl relative overflow-hidden">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-3 border-b border-slate-800/80 gap-2">
            <div className="flex items-center space-x-2">
              <CloudSun className="w-5 h-5 text-amber-400" />
              <h2 className="text-sm font-bold text-cyan-300 uppercase tracking-wider font-hud">
                Executive Situation Report & Intelligence Briefing
              </h2>
            </div>
            <div className="flex items-center space-x-2">
              <button
                onClick={() => {
                  if (digest.spoken_script) {
                    sendMessage('Read the morning executive digest out loud.');
                    onSwitchToChat();
                  }
                }}
                className="flex items-center space-x-1.5 px-3 py-1 rounded bg-cyan-950 hover:bg-cyan-900 border border-cyan-500/50 text-cyan-300 text-xs font-bold transition active:scale-95"
              >
                <Volume2 className="w-3.5 h-3.5 text-cyan-400" />
                <span>Hear Spoken Audio</span>
              </button>
            </div>
          </div>

          <div className="mt-4 grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
            {/* Weather & Location Snapshot */}
            <div className="p-3.5 rounded-lg bg-obsidian-950 border border-slate-800 space-y-2">
              <div className="text-[10px] uppercase font-bold text-slate-400 flex items-center space-x-1.5">
                <CloudSun className="w-3.5 h-3.5 text-cyan-400" />
                <span>Atmospheric Telemetry</span>
              </div>
              <div className="text-slate-300 text-xs whitespace-pre-line leading-relaxed">
                {digest.markdown.includes('## 🌤️ Weather')
                  ? digest.markdown.split('## 🌤️ Weather')[1].split('##')[0].trim().replace(/^###\s*/, '')
                  : 'Weather sensors active and calibrated.'}
              </div>
            </div>

            {/* AI & World Intelligence Briefing */}
            <div className="p-3.5 rounded-lg bg-obsidian-950 border border-slate-800 space-y-2 md:col-span-2">
              <div className="text-[10px] uppercase font-bold text-slate-400 flex items-center space-x-1.5">
                <Globe className="w-3.5 h-3.5 text-cyan-400" />
                <span>Intelligence & Technology Feed</span>
              </div>
              <div className="text-slate-300 text-xs line-clamp-3 leading-relaxed">
                {digest.spoken_script}
              </div>
              <div className="pt-2 flex justify-end">
                <button
                  onClick={onSwitchToChat}
                  className="text-cyan-400 hover:text-cyan-200 text-[11px] font-bold flex items-center space-x-1"
                >
                  <span>Read Full Dossier in Chat</span>
                  <ArrowRight className="w-3 h-3" />
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* 5. Row 3: Command Center Dual Panels */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left Column: Subagents, Expert Skills, and Continuous Learning */}
        <div className="space-y-6">
          {/* Subagent Specialized Team */}
          <div className="p-5 rounded-xl bg-obsidian-900 border border-cyan-900/40 shadow-lg space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center space-x-2">
                <Users className="w-4 h-4 text-cyan-400" />
                <h3 className="text-xs font-bold text-cyan-300 uppercase tracking-wider font-hud">
                  Active Employee Subagent Roster
                </h3>
              </div>
              <button
                onClick={onOpenAgentsModal}
                className="text-[11px] text-cyan-400 hover:text-cyan-200 flex items-center space-x-1"
              >
                <span>Manage SOPs</span>
                <ExternalLink className="w-3 h-3" />
              </button>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              {team.length > 0 ? (
                team.map((emp) => (
                  <div
                    key={emp.name}
                    className="p-3 rounded-lg bg-obsidian-950 border border-slate-800 space-y-1 hover:border-cyan-700/60 transition"
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-bold text-cyan-300 text-xs capitalize">{emp.name}</span>
                      <span className="w-2 h-2 rounded-full bg-emerald-400 shadow-[0_0_6px_#34d399]" />
                    </div>
                    <p className="text-[10px] text-slate-400 line-clamp-2">{emp.summary}</p>
                    <div className="text-[9px] text-cyan-500 font-bold uppercase tracking-wider">
                      Status: Standby
                    </div>
                  </div>
                ))
              ) : (
                <div className="col-span-3 text-slate-500 text-xs py-2">Loading employee roster...</div>
              )}
            </div>
          </div>

          {/* Expert Skills Catalog (OpenJarvis Standard) */}
          <div className="p-5 rounded-xl bg-obsidian-900 border border-cyan-900/40 shadow-lg space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center space-x-2">
                <Sparkles className="w-4 h-4 text-cyan-400" />
                <h3 className="text-xs font-bold text-cyan-300 uppercase tracking-wider font-hud">
                  Expert Skills Catalog
                </h3>
              </div>
              <span className="text-[10px] px-2 py-0.5 rounded bg-cyan-950 text-cyan-400 border border-cyan-800">
                agentskills.io
              </span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              {skills.map((skill) => (
                <div
                  key={skill.name}
                  className="p-3 rounded-lg bg-obsidian-950 border border-slate-800 space-y-2 flex flex-col justify-between hover:border-cyan-600/50 transition"
                >
                  <div>
                    <div className="font-bold text-cyan-300 text-xs capitalize">
                      {skill.name.replace(/_/g, ' ')}
                    </div>
                    <p className="text-[10px] text-slate-400 mt-1 line-clamp-2">
                      {skill.description}
                    </p>
                  </div>
                  <button
                    onClick={() => handleLaunchSkill(skill.name)}
                    className="w-full mt-2 py-1 px-2 rounded bg-cyan-950 hover:bg-cyan-900 border border-cyan-800 text-[10px] font-bold text-cyan-300 transition flex items-center justify-center space-x-1"
                  >
                    <span>Execute</span>
                    <Play className="w-2.5 h-2.5 fill-cyan-300 text-cyan-300" />
                  </button>
                </div>
              ))}
            </div>
          </div>

          {/* Continuous Learning & Traces Engine */}
          <div className="p-5 rounded-xl bg-obsidian-900 border border-cyan-900/40 shadow-lg space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center space-x-2">
                <Brain className="w-4 h-4 text-cyan-400" />
                <h3 className="text-xs font-bold text-cyan-300 uppercase tracking-wider font-hud">
                  Continuous Learning & Trace Mining
                </h3>
              </div>
              <button
                onClick={onOpenMemoryModal}
                className="text-[11px] text-cyan-400 hover:text-cyan-200 flex items-center space-x-1"
              >
                <span>View Memories</span>
                <ExternalLink className="w-3 h-3" />
              </button>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 text-xs">
              <div className="p-3 rounded-lg bg-obsidian-950 border border-slate-800">
                <div className="text-[10px] text-slate-500 uppercase font-bold">Execution Traces</div>
                <div className="text-xl font-bold text-cyan-300 mt-1">{traces.total_traces}</div>
                <div className="text-[10px] text-slate-500">Logged in traces.jsonl</div>
              </div>

              <div className="p-3 rounded-lg bg-obsidian-950 border border-slate-800">
                <div className="text-[10px] text-slate-500 uppercase font-bold">Mined Exemplars</div>
                <div className="text-xl font-bold text-emerald-400 mt-1">{traces.exemplars_count}</div>
                <div className="text-[10px] text-slate-500">High-quality pairs</div>
              </div>

              <div className="p-3 rounded-lg bg-obsidian-950 border border-slate-800 col-span-2 sm:col-span-1">
                <div className="text-[10px] text-slate-500 uppercase font-bold">Self-Improvement</div>
                <div className="text-xl font-bold text-cyan-300 mt-1">Active</div>
                <div className="text-[10px] text-slate-500">Autonomous tuning</div>
              </div>
            </div>

            <div className="pt-1 flex flex-col sm:flex-row items-center justify-between gap-2">
              <span className="text-[11px] text-slate-400">
                Learns behavioral rules from user critiques & feedback notes.
              </span>
              <button
                onClick={handleEvolvePrompt}
                disabled={isEvolving}
                className="w-full sm:w-auto px-3 py-1.5 rounded-lg bg-cyan-950 hover:bg-cyan-900 border border-cyan-500/40 text-cyan-300 text-xs font-bold transition flex items-center justify-center space-x-1.5 active:scale-95"
              >
                <Sparkles className={`w-3.5 h-3.5 ${isEvolving ? 'animate-spin' : ''}`} />
                <span>{isEvolving ? 'Evolving...' : 'Evolve System Prompts'}</span>
              </button>
            </div>

            {evolveMessage && (
              <div className="p-2.5 rounded bg-cyan-950/80 border border-cyan-600/60 text-xs text-cyan-300 text-center animate-fade-in">
                {evolveMessage}
              </div>
            )}
          </div>
        </div>

        {/* Right Column: Zero-Trust Security Shield, Live Activity Feed, and Network Connectivity */}
        <div className="space-y-6">
          {/* Zero-Trust Tool Policy & Defense Shield */}
          <div className="p-5 rounded-xl bg-obsidian-900 border border-cyan-900/40 shadow-lg space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center space-x-2">
                <ShieldCheck className="w-5 h-5 text-emerald-400" />
                <h3 className="text-xs font-bold text-cyan-300 uppercase tracking-wider font-hud">
                  Zero-Trust Tool Policy & Safety Gate
                </h3>
              </div>
              <span className="text-[10px] px-2 py-0.5 rounded bg-emerald-950 text-emerald-300 border border-emerald-800 font-bold uppercase">
                Active Shield
              </span>
            </div>

            {/* 24 Tools Categorization */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-center text-xs">
              <div className="p-3 rounded-lg bg-obsidian-950 border border-emerald-800/60">
                <div className="text-emerald-400 font-black text-lg">17</div>
                <div className="text-[10px] text-emerald-300 font-bold uppercase mt-0.5">READ Tools</div>
                <div className="text-[9px] text-slate-500 mt-1">Auto-Execute</div>
              </div>

              <div className="p-3 rounded-lg bg-obsidian-950 border border-cyan-800/60">
                <div className="text-cyan-400 font-black text-lg">4</div>
                <div className="text-[10px] text-cyan-300 font-bold uppercase mt-0.5">CONFIRM Tools</div>
                <div className="text-[9px] text-slate-500 mt-1">Approval Gate</div>
              </div>

              <div className="p-3 rounded-lg bg-obsidian-950 border border-amber-800/60">
                <div className="text-amber-400 font-black text-lg">2</div>
                <div className="text-[10px] text-amber-300 font-bold uppercase mt-0.5">CRITICAL Tools</div>
                <div className="text-[9px] text-slate-500 mt-1">Strict Warning</div>
              </div>

              <div className="p-3 rounded-lg bg-obsidian-950 border border-red-800/60">
                <div className="text-red-400 font-black text-lg">1</div>
                <div className="text-[10px] text-red-300 font-bold uppercase mt-0.5">BLOCKED Policy</div>
                <div className="text-[9px] text-slate-500 mt-1">Auto-Intercept</div>
              </div>
            </div>

            <p className="text-[11px] text-slate-400 leading-relaxed">
              PowerShell, file creation/updates, and memory modifications require single-use user authorization.
              Catastrophic actions (root formatting, credential extraction) are unconditionally blocked by policy.
            </p>
          </div>

          {/* Live System Activity & Audit Stream */}
          <div className="p-5 rounded-xl bg-obsidian-900 border border-cyan-900/40 shadow-lg space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center space-x-2">
                <Clock className="w-4 h-4 text-cyan-400" />
                <h3 className="text-xs font-bold text-cyan-300 uppercase tracking-wider font-hud">
                  Real-Time Security & Audit Trail
                </h3>
              </div>
              <span className="text-[10px] text-slate-500 font-mono">Latest Executions</span>
            </div>

            <div className="space-y-2 max-h-64 overflow-y-auto pr-1">
              {recentEvents.length > 0 ? (
                recentEvents.map((ev, i) => (
                  <div
                    key={i}
                    className="p-2.5 rounded-lg bg-obsidian-950 border border-slate-800/80 flex items-center justify-between text-xs space-x-2"
                  >
                    <div className="flex items-center space-x-2.5 truncate">
                      {ev.status === 'SUCCESS' ? (
                        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                      ) : ev.status === 'BLOCKED' ? (
                        <XCircle className="w-3.5 h-3.5 text-red-400 shrink-0" />
                      ) : (
                        <ShieldAlert className="w-3.5 h-3.5 text-amber-400 shrink-0" />
                      )}
                      <span className="font-bold text-cyan-300 truncate">
                        {ev.tool || ev.event_type}
                      </span>
                      <span className="text-slate-400 truncate text-[11px] hidden sm:inline">
                        {ev.detail || ev.status}
                      </span>
                    </div>

                    <div className="flex items-center space-x-2 shrink-0 text-[10px]">
                      <span
                        className={`px-1.5 py-0.5 rounded font-mono font-bold ${
                          ev.status === 'SUCCESS'
                            ? 'bg-emerald-950 text-emerald-400 border border-emerald-800'
                            : 'bg-red-950 text-red-400 border border-red-800'
                        }`}
                      >
                        {ev.status}
                      </span>
                      <span className="text-slate-500 font-mono">
                        {new Date(ev.timestamp * 1000).toLocaleTimeString([], {
                          hour: '2-digit',
                          minute: '2-digit',
                          second: '2-digit'
                        })}
                      </span>
                    </div>
                  </div>
                ))
              ) : (
                <div className="text-slate-500 text-xs py-4 text-center">No recent activity logged.</div>
              )}
            </div>
          </div>

          {/* Network & Device Connectivity */}
          <div className="p-5 rounded-xl bg-obsidian-900 border border-cyan-900/40 shadow-lg space-y-3">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center space-x-2">
                <Wifi className="w-4 h-4 text-cyan-400" />
                <h3 className="text-xs font-bold text-cyan-300 uppercase tracking-wider font-hud">
                  Private Network & Remote Access
                </h3>
              </div>
              <button
                onClick={onOpenSettingsModal}
                className="text-[11px] text-cyan-400 hover:text-cyan-200"
              >
                Network Settings
              </button>
            </div>

            <div className="space-y-2 text-xs">
              <div className="flex items-center justify-between p-2 rounded bg-obsidian-950 border border-slate-800">
                <span className="text-slate-400">Local Wi-Fi (LAN):</span>
                <span className="font-bold text-emerald-400">
                  {telemetry?.network.lan.map((ip) => `http://${ip}:8000`).join(', ') || 'http://127.0.0.1:8000'}
                </span>
              </div>

              <div className="flex items-center justify-between p-2 rounded bg-obsidian-950 border border-slate-800">
                <span className="text-slate-400">Tailscale Encrypted Tailnet:</span>
                <span className="font-bold text-emerald-400">
                  {telemetry?.network.tailscale.length
                    ? telemetry.network.tailscale.map((ip) => `http://${ip}:8000`).join(', ')
                    : 'Tailscale Standby'}
                </span>
              </div>

              <div className="flex items-center justify-between p-2 rounded bg-obsidian-950 border border-slate-800">
                <span className="text-slate-400">Root CA Certificate (Phone / Mac):</span>
                <a
                  href="/jarvis-ca.crt"
                  download="jarvis-ca.crt"
                  className="text-cyan-400 hover:underline flex items-center space-x-1 font-bold"
                >
                  <span>Install jarvis-ca.crt</span>
                  <ExternalLink className="w-3 h-3" />
                </a>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
