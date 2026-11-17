import React from 'react';
import { MessageSquare, Activity, Users, HardDrive, Settings } from 'lucide-react';

export type MobileTab = 'chat' | 'activity' | 'agents' | 'system' | 'settings';

interface MobileNavProps {
  currentTab: MobileTab;
  onTabChange: (tab: MobileTab) => void;
  pendingApprovalsCount: number;
}

export const MobileNav: React.FC<MobileNavProps> = ({
  currentTab,
  onTabChange,
  pendingApprovalsCount
}) => {
  const tabs = [
    { id: 'chat', label: 'Chat', icon: MessageSquare },
    { id: 'activity', label: 'Activity', icon: Activity, badge: pendingApprovalsCount },
    { id: 'agents', label: 'Agents', icon: Users },
    { id: 'system', label: 'System', icon: HardDrive },
    { id: 'settings', label: 'Settings', icon: Settings }
  ];

  return (
    <nav className="lg:hidden h-14 bg-obsidian-900 border-t border-slate-800 flex items-center justify-around px-2 shrink-0 z-30">
      {tabs.map((tab) => {
        const Icon = tab.icon;
        const isActive = currentTab === tab.id;

        return (
          <button
            key={tab.id}
            onClick={() => onTabChange(tab.id as MobileTab)}
            className={`flex flex-col items-center justify-center flex-1 py-1 transition relative ${
              isActive ? 'text-jarvis-cyan' : 'text-slate-500 hover:text-slate-300'
            }`}
          >
            <div className="relative">
              <Icon className="w-5 h-5" />
              {tab.badge && tab.badge > 0 ? (
                <span className="absolute -top-1 -right-2 w-4 h-4 rounded-full bg-red-500 text-white text-[9px] font-bold flex items-center justify-center animate-pulse">
                  {tab.badge}
                </span>
              ) : null}
            </div>
            <span className="text-[10px] font-mono mt-0.5">{tab.label}</span>
          </button>
        );
      })}
    </nav>
  );
};
