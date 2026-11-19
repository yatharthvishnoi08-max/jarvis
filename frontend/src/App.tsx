import React, { useEffect, useState } from 'react';
import { useAuthStore } from './stores/useAuthStore';
import { useJarvisStore } from './stores/useJarvisStore';
import { Activity, AudioLines, History, Monitor, ShieldAlert, Volume2, VolumeX } from 'lucide-react';
import './conversation.css';
import { LeftSidebar } from './components/LeftSidebar';
import { ChatArea } from './components/ChatArea';
import { Composer } from './components/Composer';
import { RightActivityPanel } from './components/RightActivityPanel';
import { MobileNav, MobileTab } from './components/MobileNav';
import { AuthModal } from './components/views/AuthModal';
import { AgentsView } from './components/views/AgentsView';
import { MemoryView } from './components/views/MemoryView';
import { SettingsView } from './components/views/SettingsView';
import { SystemView } from './components/views/SystemView';

export const App: React.FC = () => {
  const { isAuthenticated, isLoading, checkAuth } = useAuthStore();
  const { connectWebSocket, disconnectWebSocket, pendingApprovals, ws, voiceEnabled,
    setVoiceEnabled, triggerEmergencyStop } = useJarvisStore();

  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [activityOpen, setActivityOpen] = useState(false);
  const [agentsModalOpen, setAgentsModalOpen] = useState(false);
  const [memoryModalOpen, setMemoryModalOpen] = useState(false);
  const [settingsModalOpen, setSettingsModalOpen] = useState(false);
  const [systemModalOpen, setSystemModalOpen] = useState(false);

  const [mobileTab, setMobileTab] = useState<MobileTab>('chat');

  useEffect(() => {
    checkAuth();
  }, [checkAuth]);

  useEffect(() => {
    if (isAuthenticated) {
      connectWebSocket();
    } else {
      disconnectWebSocket();
    }
    return () => disconnectWebSocket();
  }, [isAuthenticated, connectWebSocket, disconnectWebSocket]);

  if (isLoading) {
    return (
      <div className="h-screen w-screen bg-obsidian-950 flex flex-col items-center justify-center space-y-4">
        <div className="w-8 h-8 rounded-full border-2 border-cyan-400 border-t-transparent animate-spin" />
        <div className="text-xs font-mono text-cyan-300 tracking-wider uppercase">Initializing Core...</div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <AuthModal />;
  }

  const handleMobileTabChange = (tab: MobileTab) => {
    setMobileTab(tab);
    if (tab === 'agents') setAgentsModalOpen(true);
    if (tab === 'system') setSystemModalOpen(true);
    if (tab === 'settings') setSettingsModalOpen(true);
    if (tab === 'activity') setActivityOpen(true);
  };

  return (
    <div className="jarvis-shell w-screen flex flex-col text-slate-100 overflow-hidden relative">
      {/* Top Telemetry & Controls Bar */}
      <header className="jarvis-bar">
        <div className="jarvis-brand"><AudioLines aria-hidden="true"/> Jarvis</div>
        <span className="link-state" data-online={ws?.readyState === WebSocket.OPEN}>{ws?.readyState === WebSocket.OPEN ? 'Connected' : 'Offline'}</span>
        <nav aria-label="Workspace tools">
          <button aria-label="History and settings" onClick={() => setSidebarOpen(true)}><History/><span>History</span></button>
          <button aria-label="Voice replies" aria-pressed={voiceEnabled} onClick={() => setVoiceEnabled(!voiceEnabled)}>{voiceEnabled ? <Volume2/> : <VolumeX/>}</button>
          <button aria-label="System telemetry" onClick={() => setSystemModalOpen(true)}><Monitor/></button>
          <button aria-label={'Activity and approvals: ' + pendingApprovals.length} onClick={() => setActivityOpen(true)}><Activity/><span>Activity</span>{pendingApprovals.length || ''}</button>
          <button aria-label="Emergency stop" title="Emergency stop" onClick={triggerEmergencyStop}><ShieldAlert/></button>
        </nav>
      </header>

      {/* Main Multi-Panel Workspace */}
      <div className="flex-1 flex overflow-hidden relative">
        {/* Left Navigation Sidebar (Desktop + Drawer) */}
        {sidebarOpen && <LeftSidebar
          isOpen={sidebarOpen}
          onClose={() => setSidebarOpen(false)}
          onOpenAgents={() => setAgentsModalOpen(true)}
          onOpenMemory={() => setMemoryModalOpen(true)}
          onOpenSettings={() => setSettingsModalOpen(true)}
        />}

        {/* Central Chat & Voice HUD */}
        <main className="flex-1 flex flex-col h-full overflow-hidden relative">
          <ChatArea />
          <Composer />
        </main>

        {/* Right Activity & Approvals Panel (Desktop + Drawer) */}
        {activityOpen && <RightActivityPanel
          isOpen={activityOpen}
          onClose={() => setActivityOpen(false)}
        />}
      </div>

      {/* Mobile Bottom Navigation */}
      <MobileNav
        currentTab={mobileTab}
        onTabChange={handleMobileTabChange}
        pendingApprovalsCount={pendingApprovals.length}
      />

      {/* Modals & Sub-views */}
      <AgentsView isOpen={agentsModalOpen} onClose={() => setAgentsModalOpen(false)} />
      <MemoryView isOpen={memoryModalOpen} onClose={() => setMemoryModalOpen(false)} />
      <SettingsView isOpen={settingsModalOpen} onClose={() => setSettingsModalOpen(false)} />
      <SystemView isOpen={systemModalOpen} onClose={() => setSystemModalOpen(false)} />
    </div>
  );
};
