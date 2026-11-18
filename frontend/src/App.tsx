import React, { useEffect, useState } from 'react';
import { useAuthStore } from './stores/useAuthStore';
import { useJarvisStore } from './stores/useJarvisStore';
import { TopTelemetryBar } from './components/TopTelemetryBar';
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
import { BasicChat } from './components/BasicChat';

export const App: React.FC = () => {
  const workspace = window.location.pathname === '/workspace';
  const { isAuthenticated, isLoading, checkAuth } = useAuthStore();
  const { connectWebSocket, disconnectWebSocket, pendingApprovals } = useJarvisStore();

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
    if (isAuthenticated && workspace) {
      connectWebSocket();
    } else {
      disconnectWebSocket();
    }
    return () => disconnectWebSocket();
  }, [isAuthenticated, workspace, connectWebSocket, disconnectWebSocket]);

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
  if (!workspace) return <BasicChat />;

  const handleMobileTabChange = (tab: MobileTab) => {
    setMobileTab(tab);
    if (tab === 'agents') setAgentsModalOpen(true);
    if (tab === 'system') setSystemModalOpen(true);
    if (tab === 'settings') setSettingsModalOpen(true);
    if (tab === 'activity') setActivityOpen(true);
  };

  return (
    <div className="h-screen w-screen flex flex-col bg-obsidian-950 text-slate-100 overflow-hidden relative">
      {/* Top Telemetry & Controls Bar */}
      <TopTelemetryBar
        onToggleSidebar={() => setSidebarOpen(!sidebarOpen)}
        onOpenSettings={() => setSettingsModalOpen(true)}
      />

      {/* Main Multi-Panel Workspace */}
      <a href="/" className="self-start px-4 py-2 text-sm text-cyan-300">← Back to chat</a>
      <div className="flex-1 flex overflow-hidden relative">
        {/* Left Navigation Sidebar (Desktop + Drawer) */}
        <LeftSidebar
          isOpen={sidebarOpen}
          onClose={() => setSidebarOpen(false)}
          onOpenAgents={() => setAgentsModalOpen(true)}
          onOpenMemory={() => setMemoryModalOpen(true)}
          onOpenSettings={() => setSettingsModalOpen(true)}
        />

        {/* Central Chat & Voice HUD */}
        <main className="flex-1 flex flex-col h-full overflow-hidden bg-obsidian-950 relative">
          <ChatArea />
          <Composer />
        </main>

        {/* Right Activity & Approvals Panel (Desktop + Drawer) */}
        <RightActivityPanel
          isOpen={activityOpen}
          onClose={() => setActivityOpen(false)}
        />
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
