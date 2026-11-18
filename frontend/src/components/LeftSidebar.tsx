import React from 'react';
import { useJarvisStore } from '../stores/useJarvisStore';
import { useAuthStore } from '../stores/useAuthStore';
import { Plus, MessageSquare, Trash2, Users, Brain, Activity, Settings, LogOut, X, Terminal, LayoutDashboard } from 'lucide-react';

interface LeftSidebarProps {
  isOpen: boolean;
  onClose: () => void;
  onOpenAgents: () => void;
  onOpenMemory: () => void;
  onOpenSettings: () => void;
  currentView?: 'chat' | 'dashboard';
  onViewChange?: (view: 'chat' | 'dashboard') => void;
}

export const LeftSidebar: React.FC<LeftSidebarProps> = ({
  isOpen,
  onClose,
  onOpenAgents,
  onOpenMemory,
  onOpenSettings,
  currentView = 'chat',
  onViewChange
}) => {
  const { sessions, currentSessionId, switchSession, createSession, deleteSession } = useJarvisStore();
  const { logout } = useAuthStore();

  return (
    <>
      {/* Mobile Backdrop */}
      {isOpen && (
        <div
          onClick={onClose}
          className="fixed inset-0 bg-black/60 backdrop-blur-sm z-40 lg:hidden"
        />
      )}

      <aside
        className={`fixed lg:static top-0 left-0 h-full w-64 bg-obsidian-900 border-r border-slate-800/80 flex flex-col z-50 transition-transform duration-300 ease-in-out ${
          isOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'
        }`}
      >
        {/* Sidebar Header */}
        <div className="p-3.5 border-b border-slate-800 flex items-center justify-between shrink-0">
          <button
            onClick={() => {
              createSession();
              onClose();
            }}
            className="flex-1 flex items-center justify-center space-x-2 py-2 px-3 rounded-lg bg-cyan-950/60 border border-cyan-500/40 text-cyan-300 text-xs font-mono font-semibold hover:bg-cyan-900/60 active:scale-95 transition shadow-sm"
          >
            <Plus className="w-4 h-4 text-jarvis-cyan" />
            <span>NEW SESSION</span>
          </button>
          <button onClick={onClose} className="p-1.5 ml-2 text-slate-400 hover:text-white lg:hidden">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Primary View Switcher */}
        {onViewChange && (
          <div className="px-3 pt-3 pb-2 space-y-1 border-b border-slate-800/80 font-mono text-xs">
            <button
              onClick={() => {
                onViewChange('chat');
                onClose();
              }}
              className={`w-full flex items-center space-x-2.5 px-3 py-2 rounded-lg transition ${
                currentView === 'chat'
                  ? 'bg-cyan-950/80 border border-cyan-500/50 text-cyan-200 font-bold shadow-sm'
                  : 'text-slate-400 hover:bg-obsidian-850 hover:text-cyan-300'
              }`}
            >
              <Terminal className="w-4 h-4 text-cyan-400" />
              <span>Command HUD Chat</span>
            </button>

            <button
              onClick={() => {
                onViewChange('dashboard');
                onClose();
              }}
              className={`w-full flex items-center space-x-2.5 px-3 py-2 rounded-lg transition ${
                currentView === 'dashboard'
                  ? 'bg-cyan-950/80 border border-cyan-500/50 text-cyan-200 font-bold shadow-sm'
                  : 'text-slate-400 hover:bg-obsidian-850 hover:text-cyan-300'
              }`}
            >
              <LayoutDashboard className="w-4 h-4 text-cyan-400" />
              <span>Mission Control</span>
            </button>
          </div>
        )}

        {/* Sessions List */}
        <div className="flex-1 overflow-y-auto px-2 py-3 space-y-1">
          <div className="px-2 pb-1.5 text-[10px] font-mono uppercase tracking-wider text-slate-500">
            Recent Conversations
          </div>

          {sessions.length === 0 ? (
            <div className="px-3 py-6 text-center text-xs text-slate-500 font-mono">
              No previous sessions.
            </div>
          ) : (
            sessions.map((sess) => {
              const isActive = sess.id === currentSessionId;
              return (
                <div
                  key={sess.id}
                  onClick={() => {
                    switchSession(sess.id);
                    onClose();
                  }}
                  className={`group flex items-center justify-between px-3 py-2.5 rounded-lg text-xs font-mono transition cursor-pointer ${
                    isActive
                      ? 'bg-cyan-950/40 border border-cyan-800/60 text-cyan-200'
                      : 'text-slate-400 hover:bg-obsidian-850 hover:text-slate-200 border border-transparent'
                  }`}
                >
                  <div className="flex items-center space-x-2.5 truncate">
                    <MessageSquare className={`w-3.5 h-3.5 shrink-0 ${isActive ? 'text-cyan-400' : 'text-slate-500'}`} />
                    <span className="truncate">{sess.title}</span>
                  </div>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      deleteSession(sess.id);
                    }}
                    className="opacity-0 group-hover:opacity-100 p-1 text-slate-500 hover:text-red-400 transition"
                    title="Delete session"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              );
            })
          )}
        </div>

        {/* Management Shortcuts */}
        <div className="p-2 border-t border-slate-800/80 space-y-1 text-xs font-mono">
          <button
            onClick={() => {
              onOpenAgents();
              onClose();
            }}
            className="w-full flex items-center space-x-2.5 px-3 py-2 rounded-lg text-slate-400 hover:bg-obsidian-850 hover:text-cyan-300 transition"
          >
            <Users className="w-4 h-4 text-cyan-400" />
            <span>Employee Roster</span>
          </button>

          <button
            onClick={() => {
              onOpenMemory();
              onClose();
            }}
            className="w-full flex items-center space-x-2.5 px-3 py-2 rounded-lg text-slate-400 hover:bg-obsidian-850 hover:text-cyan-300 transition"
          >
            <Brain className="w-4 h-4 text-cyan-400" />
            <span>Learned Rules & Memory</span>
          </button>

          <button
            onClick={() => {
              onOpenSettings();
              onClose();
            }}
            className="w-full flex items-center space-x-2.5 px-3 py-2 rounded-lg text-slate-400 hover:bg-obsidian-850 hover:text-cyan-300 transition"
          >
            <Settings className="w-4 h-4 text-cyan-400" />
            <span>Settings & Keys</span>
          </button>
        </div>

        {/* User Status & Logout */}
        <div className="p-3 border-t border-slate-800 bg-obsidian-950/60 flex items-center justify-between text-xs font-mono">
          <div className="flex items-center space-x-2 text-slate-400 truncate">
            <div className="w-2 h-2 rounded-full bg-emerald-400 shrink-0" />
            <span className="truncate">Owner Authenticated</span>
          </div>
          <button
            onClick={logout}
            className="p-1.5 text-slate-500 hover:text-amber-400 transition"
            title="Log out"
          >
            <LogOut className="w-4 h-4" />
          </button>
        </div>
      </aside>
    </>
  );
};
