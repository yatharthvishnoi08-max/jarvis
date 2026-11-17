import React, { useEffect } from 'react';
import { useTelemetryStore } from '../../stores/useTelemetryStore';
import { Cpu, Activity, HardDrive, Wifi, Server, Shield, X } from 'lucide-react';

interface SystemViewProps {
  isOpen: boolean;
  onClose: () => void;
}

export const SystemView: React.FC<SystemViewProps> = ({ isOpen, onClose }) => {
  const { telemetry, fetchTelemetry } = useTelemetryStore();

  useEffect(() => {
    if (isOpen) {
      fetchTelemetry();
    }
  }, [isOpen, fetchTelemetry]);

  if (!isOpen) return null;

  const formatUptime = (seconds?: number) => {
    if (!seconds) return '--';
    const hrs = Math.floor(seconds / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    return `${hrs}h ${mins}m`;
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-3 sm:p-6 animate-fade-in">
      <div className="bg-obsidian-900 border border-slate-800 rounded-2xl w-full max-w-2xl max-h-[85vh] flex flex-col shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="p-4 border-b border-slate-800 flex items-center justify-between shrink-0">
          <div className="flex items-center space-x-2">
            <Server className="w-5 h-5 text-jarvis-cyan" />
            <h2 className="text-base font-bold text-cyan-300 hud-title tracking-wider uppercase">
              Host System Telemetry
            </h2>
          </div>
          <button onClick={onClose} className="p-1 text-slate-400 hover:text-white">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content Body */}
        <div className="p-4 sm:p-6 overflow-y-auto space-y-4 font-mono text-xs">
          {/* Hardware Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div className="p-4 rounded-xl bg-obsidian-950 border border-slate-800 space-y-1">
              <div className="text-slate-500 text-[10px] uppercase font-bold flex items-center space-x-1.5">
                <Cpu className="w-4 h-4 text-cyan-400" />
                <span>Processor</span>
              </div>
              <div className="text-xl font-bold text-cyan-300">{telemetry?.cpu_percent ?? '--'}%</div>
              <div className="text-[10px] text-slate-500">Utilization</div>
            </div>

            <div className="p-4 rounded-xl bg-obsidian-950 border border-slate-800 space-y-1">
              <div className="text-slate-500 text-[10px] uppercase font-bold flex items-center space-x-1.5">
                <Activity className="w-4 h-4 text-cyan-400" />
                <span>Memory</span>
              </div>
              <div className="text-xl font-bold text-cyan-300">{telemetry?.ram_percent ?? '--'}%</div>
              <div className="text-[10px] text-slate-500">
                {telemetry ? `${telemetry.ram_used_mb}MB / ${telemetry.ram_total_mb}MB` : '--'}
              </div>
            </div>

            <div className="p-4 rounded-xl bg-obsidian-950 border border-slate-800 space-y-1">
              <div className="text-slate-500 text-[10px] uppercase font-bold flex items-center space-x-1.5">
                <HardDrive className="w-4 h-4 text-cyan-400" />
                <span>Disk C:</span>
              </div>
              <div className="text-xl font-bold text-cyan-300">{telemetry?.disk_percent ?? '--'}%</div>
              <div className="text-[10px] text-slate-500">
                {telemetry ? `${telemetry.disk_free_gb} GB Free` : '--'}
              </div>
            </div>
          </div>

          {/* System Specs */}
          <div className="p-4 rounded-xl bg-obsidian-950 border border-slate-800 space-y-2.5 text-slate-300">
            <div className="flex justify-between border-b border-slate-800/80 pb-2">
              <span className="text-slate-500">Host Device:</span>
              <span className="font-bold text-cyan-300">{telemetry?.hostname ?? 'Windows Host'}</span>
            </div>
            <div className="flex justify-between border-b border-slate-800/80 pb-2">
              <span className="text-slate-500">Active Model Engine:</span>
              <span className="font-bold text-cyan-300">{telemetry?.active_model ?? 'Hermes'}</span>
            </div>
            <div className="flex justify-between border-b border-slate-800/80 pb-2">
              <span className="text-slate-500">Uptime:</span>
              <span className="text-cyan-300">{formatUptime(telemetry?.uptime_seconds)}</span>
            </div>
            <div className="flex justify-between border-b border-slate-800/80 pb-2">
              <span className="text-slate-500">Private LAN IP:</span>
              <span className="text-emerald-400 font-bold">{telemetry?.network.lan.join(', ') || 'None'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500">Tailscale IP:</span>
              <span className="text-emerald-400 font-bold">
                {telemetry?.network.tailscale.length ? telemetry.network.tailscale.join(', ') : 'Not Connected'}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
