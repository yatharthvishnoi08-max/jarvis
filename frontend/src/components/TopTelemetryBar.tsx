import React, { useEffect } from 'react';
import { useTelemetryStore } from '../stores/useTelemetryStore';
import { useJarvisStore } from '../stores/useJarvisStore';
import { Cpu, Activity, HardDrive, ShieldAlert, Wifi, Volume2, VolumeX, Menu, Terminal, LayoutDashboard } from 'lucide-react';

interface TopTelemetryBarProps {
  onToggleSidebar?: () => void;
  onOpenSettings?: () => void;
  currentView?: 'chat' | 'dashboard';
  onViewChange?: (view: 'chat' | 'dashboard') => void;
}

export const TopTelemetryBar: React.FC<TopTelemetryBarProps> = ({
  onToggleSidebar,
  onOpenSettings,
  currentView = 'chat',
  onViewChange
}) => {
  const { telemetry, fetchTelemetry } = useTelemetryStore();
  const {
    orbState,
    voiceEnabled,
    setVoiceEnabled,
    triggerEmergencyStop,
    isEmergencyStopped
  } = useJarvisStore();

  useEffect(() => {
    fetchTelemetry();
    const interval = setInterval(fetchTelemetry, 4000);
    return () => clearInterval(interval);
  }, [fetchTelemetry]);

  const hasTailscale = (telemetry?.network.tailscale.length ?? 0) > 0;

  return (
    <header className="h-14 border-b border-cyan-900/40 bg-obsidian-900/90 backdrop-blur-md px-3 sm:px-4 flex items-center justify-between shrink-0 z-30">
      {/* Brand & State */}
      <div className="flex items-center space-x-3">
        <button
          onClick={onToggleSidebar}
          className="lg:hidden p-1.5 rounded-lg bg-obsidian-800 text-slate-300 hover:text-cyan-400"
          aria-label="Toggle Navigation"
        >
          <Menu className="w-5 h-5" />
        </button>

        <div className="flex items-center space-x-2">
          <span className="font-extrabold tracking-widest text-jarvis-cyan text-base font-hud">
            J.A.R.V.I.S.
          </span>
          <span className="text-[10px] uppercase px-1.5 py-0.5 rounded bg-cyan-950/80 text-cyan-400 border border-cyan-800/60 font-mono">
            v3.0-OWNER
          </span>
        </div>

        {/* State Pill */}
        <div className="hidden sm:flex items-center space-x-1.5 text-xs font-mono text-slate-400">
          <div
            className={`w-2 h-2 rounded-full ${
              orbState === 'disconnected'
                ? 'bg-amber-400'
                : orbState === 'error'
                ? 'bg-red-500 animate-pulse'
                : 'bg-emerald-400'
            }`}
          />
          <span className="capitalize">{orbState}</span>
        </div>

        {/* View Switcher Pill */}
        {onViewChange && (
          <div className="flex items-center rounded-lg bg-obsidian-950 p-0.5 border border-slate-800 text-xs font-mono ml-2">
            <button
              onClick={() => onViewChange('chat')}
              className={`px-2.5 py-1 rounded-md transition flex items-center space-x-1.5 ${
                currentView === 'chat'
                  ? 'bg-cyan-950/90 border border-cyan-500/50 text-cyan-300 font-bold shadow-sm'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <Terminal className="w-3.5 h-3.5" />
              <span className="hidden md:inline">HUD Chat</span>
            </button>
            <button
              onClick={() => onViewChange('dashboard')}
              className={`px-2.5 py-1 rounded-md transition flex items-center space-x-1.5 ${
                currentView === 'dashboard'
                  ? 'bg-cyan-950/90 border border-cyan-500/50 text-cyan-300 font-bold shadow-sm'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <LayoutDashboard className="w-3.5 h-3.5" />
              <span className="hidden md:inline">Dashboard</span>
            </button>
          </div>
        )}
      </div>

      {/* Live System Gauges */}
      <div className="hidden md:flex items-center space-x-3 text-xs font-mono text-slate-300">
        <div className="flex items-center space-x-1.5 bg-obsidian-850 px-2.5 py-1 rounded border border-slate-800">
          <Cpu className="w-3.5 h-3.5 text-jarvis-cyan" />
          <span>CPU:</span>
          <span className="text-cyan-300 font-bold">
            {telemetry ? `${telemetry.cpu_percent}%` : '--%'}
          </span>
        </div>

        <div className="flex items-center space-x-1.5 bg-obsidian-850 px-2.5 py-1 rounded border border-slate-800">
          <Activity className="w-3.5 h-3.5 text-jarvis-cyan" />
          <span>RAM:</span>
          <span className="text-cyan-300 font-bold">
            {telemetry ? `${telemetry.ram_percent}%` : '--%'}
          </span>
        </div>

        <div className="flex items-center space-x-1.5 bg-obsidian-850 px-2.5 py-1 rounded border border-slate-800">
          <HardDrive className="w-3.5 h-3.5 text-jarvis-cyan" />
          <span>Disk:</span>
          <span className="text-cyan-300 font-bold">
            {telemetry ? `${telemetry.disk_free_gb} GB` : '--'}
          </span>
        </div>

        {/* Tailscale / Network Status Indicator */}
        <div
          className={`flex items-center space-x-1.5 px-2.5 py-1 rounded border text-xs ${
            hasTailscale
              ? 'bg-emerald-950/40 border-emerald-800/60 text-emerald-300'
              : 'bg-obsidian-850 border-slate-800 text-slate-400'
          }`}
          title={hasTailscale ? `Tailscale IP: ${telemetry?.network.tailscale.join(', ')}` : 'Local LAN Only'}
        >
          <Wifi className="w-3.5 h-3.5 text-cyan-400" />
          <span>{hasTailscale ? 'Tailscale' : 'LAN'}</span>
        </div>
      </div>

      {/* Control Actions */}
      <div className="flex items-center space-x-2">
        {/* Voice Toggle Button */}
        <button
          onClick={() => setVoiceEnabled(!voiceEnabled)}
          className={`p-2 rounded-lg border transition text-xs flex items-center space-x-1.5 ${
            voiceEnabled
              ? 'bg-obsidian-850 border-cyan-800/60 text-jarvis-cyan hover:bg-cyan-950/40'
              : 'bg-obsidian-850 border-slate-800 text-slate-500 hover:bg-obsidian-800'
          }`}
          title={voiceEnabled ? 'Mute Voice' : 'Enable Voice'}
        >
          {voiceEnabled ? <Volume2 className="w-4 h-4" /> : <VolumeX className="w-4 h-4" />}
          <span className="hidden xl:inline font-mono">{voiceEnabled ? 'Voice ON' : 'Muted'}</span>
        </button>

        {/* Emergency Stop Button */}
        <button
          onClick={triggerEmergencyStop}
          className={`px-3 py-1.5 rounded-lg border text-xs font-mono font-bold flex items-center space-x-1.5 transition ${
            isEmergencyStopped
              ? 'bg-red-700 text-white border-red-500 animate-pulse'
              : 'bg-red-950/40 text-red-400 border-red-800/80 hover:bg-red-900/60 active:scale-95'
          }`}
          title="Emergency Stop: Halt running tools, cancel task, stop audio immediately"
        >
          <ShieldAlert className="w-4 h-4" />
          <span className="hidden sm:inline">EMERGENCY STOP</span>
        </button>
      </div>
    </header>
  );
};
