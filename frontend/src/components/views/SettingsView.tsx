import React, { useEffect, useState } from 'react';
import { useAudioStore } from '../../stores/useAudioStore';
import { useAuthStore } from '../../stores/useAuthStore';
import { useTelemetryStore } from '../../stores/useTelemetryStore';
import { Settings, X, Volume2, Shield, Key, Wifi, Check } from 'lucide-react';

interface SettingsViewProps {
  isOpen: boolean;
  onClose: () => void;
}

export const SettingsView: React.FC<SettingsViewProps> = ({ isOpen, onClose }) => {
  const { voices, activeVoiceId, fetchVoices, selectVoice } = useAudioStore();
  const { token, setToken } = useAuthStore();
  const { telemetry } = useTelemetryStore();
  const [tokenInput, setTokenInput] = useState(token);
  const [savedTokenMsg, setSavedTokenMsg] = useState('');

  useEffect(() => {
    if (isOpen) {
      fetchVoices();
      setTokenInput(token);
    }
  }, [isOpen, fetchVoices, token]);

  const handleSaveToken = (e: React.FormEvent) => {
    e.preventDefault();
    if (!tokenInput.trim()) return;
    setToken(tokenInput.trim());
    setSavedTokenMsg('Token updated.');
    setTimeout(() => setSavedTokenMsg(''), 3000);
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-3 sm:p-6 animate-fade-in">
      <div className="bg-obsidian-900 border border-slate-800 rounded-2xl w-full max-w-2xl max-h-[85vh] flex flex-col shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="p-4 border-b border-slate-800 flex items-center justify-between shrink-0">
          <div className="flex items-center space-x-2">
            <Settings className="w-5 h-5 text-jarvis-cyan" />
            <h2 className="text-base font-bold text-cyan-300 hud-title tracking-wider uppercase">
              System Settings & Voice Configuration
            </h2>
          </div>
          <button onClick={onClose} className="p-1 text-slate-400 hover:text-white">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content Body */}
        <div className="p-4 sm:p-6 overflow-y-auto space-y-6 text-xs font-mono">
          {/* ElevenLabs Voice Selection */}
          <div className="space-y-3">
            <div className="flex items-center space-x-2 text-sm font-bold text-cyan-300">
              <Volume2 className="w-4 h-4 text-jarvis-cyan" />
              <span>ElevenLabs Voice Persona</span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              {voices.map((v) => (
                <div
                  key={v.id}
                  onClick={() => selectVoice(v.id)}
                  className={`p-3 rounded-xl border cursor-pointer transition flex items-center justify-between ${
                    v.id === activeVoiceId
                      ? 'bg-cyan-950/60 border-cyan-500 text-cyan-200 shadow-cyan-glow'
                      : 'bg-obsidian-850 border-slate-800 text-slate-400 hover:border-slate-700 hover:text-slate-200'
                  }`}
                >
                  <div>
                    <div className="font-bold text-xs">{v.name}</div>
                    <div className="text-[10px] text-slate-500">{v.description}</div>
                  </div>
                  {v.id === activeVoiceId && <Check className="w-4 h-4 text-jarvis-cyan" />}
                </div>
              ))}
            </div>
          </div>

          {/* Network & Tailscale Telemetry */}
          <div className="space-y-3 pt-3 border-t border-slate-800">
            <div className="flex items-center space-x-2 text-sm font-bold text-cyan-300">
              <Wifi className="w-4 h-4 text-jarvis-cyan" />
              <span>Remote Access Addresses</span>
            </div>

            <div className="p-3 rounded-xl bg-obsidian-950 border border-slate-800 space-y-2 text-slate-300">
              <div className="flex justify-between">
                <span className="text-slate-500">Local Laptop URL:</span>
                <span className="text-cyan-400 font-bold">http://localhost:8000</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Private LAN Address:</span>
                <span className="text-cyan-400 font-bold">
                  {telemetry?.network.lan ? `http://${telemetry.network.lan[0]}:8000` : 'N/A'}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Tailscale Private IP:</span>
                <span className="text-emerald-400 font-bold">
                  {telemetry?.network.tailscale.length
                    ? `http://${telemetry.network.tailscale[0]}:8000`
                    : 'Not connected (Install Tailscale)'}
                </span>
              </div>
            </div>
          </div>

          {/* Authentication Token Configuration */}
          <div className="space-y-3 pt-3 border-t border-slate-800">
            <div className="flex items-center space-x-2 text-sm font-bold text-cyan-300">
              <Key className="w-4 h-4 text-jarvis-cyan" />
              <span>Owner Authentication Token</span>
            </div>

            <form onSubmit={handleSaveToken} className="space-y-2">
              <div className="flex space-x-2">
                <input
                  type="text"
                  value={tokenInput}
                  onChange={(e) => setTokenInput(e.target.value)}
                  className="flex-1 bg-obsidian-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-200 font-mono focus:outline-none focus:border-cyan-500"
                />
                <button
                  type="submit"
                  className="px-4 py-2 rounded-lg bg-cyan-950 border border-cyan-500/50 text-cyan-300 font-bold hover:bg-cyan-900/60 transition"
                >
                  Save Token
                </button>
              </div>
              {savedTokenMsg && <div className="text-emerald-400 text-xs">{savedTokenMsg}</div>}
              <div className="text-[10px] text-slate-500">
                This token authenticates your browser session with the backend gateway.
              </div>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
};
