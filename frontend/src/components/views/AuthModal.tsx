import React, { useState } from 'react';
import { useAuthStore } from '../../stores/useAuthStore';
import { JarvisOrb } from '../JarvisOrb';
import { ShieldCheck, Key, ArrowRight, AlertCircle } from 'lucide-react';

export const AuthModal: React.FC = () => {
  const [inputToken, setInputToken] = useState('');
  const [errorMsg, setErrorMsg] = useState('');
  const [isVerifying, setIsVerifying] = useState(false);
  const { setToken, checkAuth } = useAuthStore();

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputToken.trim()) return;

    setIsVerifying(true);
    setErrorMsg('');

    try {
      const res = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token: inputToken.trim() })
      });

      if (res.ok) {
        setToken(inputToken.trim());
        await checkAuth();
      } else {
        setErrorMsg('Authentication failed: Invalid owner token.');
      }
    } catch (err) {
      setErrorMsg('Cannot reach JARVIS gateway server.');
    } finally {
      setIsVerifying(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-obsidian-950 flex items-center justify-center p-4">
      <div className="w-full max-w-md bg-obsidian-900 border border-cyan-900/40 rounded-2xl p-6 sm:p-8 space-y-6 shadow-2xl relative glow-box-cyan">
        {/* Core Orb Icon */}
        <div className="flex justify-center">
          <ShieldCheck aria-hidden="true" className="w-10 h-10 text-cyan-300" />
        </div>

        <div className="text-center space-y-1.5">
          <h1 className="text-xl font-bold tracking-widest text-cyan-300 hud-title uppercase">
            Sign in to Jarvis
          </h1>
          <p className="text-xs text-slate-400 font-mono">
            Enter the owner token from your gateway.
          </p>
        </div>

        {/* Login Form */}
        <form onSubmit={handleLogin} className="space-y-4">
          <div className="space-y-1.5">
            <label className="text-[11px] font-mono text-cyan-400 uppercase tracking-wider block font-semibold">
              Owner Security Token
            </label>
            <div className="relative">
              <input
                type="password"
                value={inputToken}
                onChange={(e) => setInputToken(e.target.value)}
                placeholder="Enter JARVIS_AUTH_TOKEN..."
                className="w-full bg-obsidian-950 border border-slate-800 rounded-xl px-4 py-3 text-sm text-slate-100 placeholder-slate-600 focus:outline-none focus:border-cyan-500 font-mono pl-10"
                autoFocus
              />
              <Key className="w-4 h-4 text-slate-500 absolute left-3.5 top-3.5" />
            </div>
          </div>

          {errorMsg && (
            <div className="p-2.5 rounded-lg bg-red-950/60 border border-red-800/80 text-red-300 text-xs font-mono flex items-center space-x-2">
              <AlertCircle className="w-4 h-4 text-red-400 shrink-0" />
              <span>{errorMsg}</span>
            </div>
          )}

          <button
            type="submit"
            disabled={isVerifying || !inputToken.trim()}
            className="w-full py-3 rounded-xl bg-jarvis-cyan text-obsidian-950 font-bold font-mono text-xs uppercase tracking-wider hover:bg-cyan-400 disabled:opacity-30 transition flex items-center justify-center space-x-2 shadow-lg"
          >
            <span>{isVerifying ? 'Signing in…' : 'Open chat'}</span>
            <ArrowRight className="w-4 h-4" />
          </button>
        </form>

        <div className="text-center text-[10px] text-slate-500 font-mono">
          Token is located in your Windows laptop's <code className="text-slate-400">.env</code> file under <code className="text-slate-400">JARVIS_AUTH_TOKEN</code>.
        </div>
      </div>
    </div>
  );
};
