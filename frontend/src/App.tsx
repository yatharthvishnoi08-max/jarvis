import { useEffect, useState } from 'react';
import { Activity, AudioLines, Brain, ChevronsUpDown, CircleUser, Folder, Inbox, LayoutDashboard, ListChecks, LogOut, Menu, Network, Plus, Settings2, ShieldAlert, Trash2, Users, Volume2, VolumeX, X } from 'lucide-react';
import { useAuthStore } from './stores/useAuthStore';
import { useJarvisStore } from './stores/useJarvisStore';
import { useAudioStore } from './stores/useAudioStore';
import { BasicChat } from './components/BasicChat';
import { ChatArea } from './components/ChatArea';
import { WorkspaceInbox } from './components/WorkspaceInbox';
import { Planner } from './components/Planner';
import { Composer } from './components/Composer';
import { NetworkMap, Destination } from './components/NetworkMap';
import { RightActivityPanel } from './components/RightActivityPanel';
import { AuthModal } from './components/views/AuthModal';
import { AgentsView } from './components/views/AgentsView';
import { MemoryView } from './components/views/MemoryView';
import { SettingsView } from './components/views/SettingsView';
import { SystemView } from './components/views/SystemView';
import './conversation.css';
import './network.css';

const navigation = [
  ['Network', Network], ['Planner', ListChecks], ['Inbox', Inbox], ['Dashboard', LayoutDashboard], ['Talk', AudioLines],
  ['Activity', Activity], ['Files', Folder], ['Memory', Brain], ['Assistant', Users], ['Settings', Settings2]
] as const;
type View = typeof navigation[number][0] | 'Account';

export function App() {
  const {isAuthenticated,isLoading,checkAuth,logout}=useAuthStore();
  const {connectWebSocket,disconnectWebSocket,ws,sessions,currentSessionId,switchSession,createSession,deleteSession,
    messages,orbState,voiceEnabled,setVoiceEnabled,pendingApprovals,isListening,triggerEmergencyStop}=useJarvisStore();
  const [page,setPage]=useState<'Network'|'Talk'|'Planner'|'Inbox'|'Calendar'>('Network');
  const [panel,setPanel]=useState<View|null>(null);
  const [menu,setMenu]=useState(false);
  const [draft,setDraft]=useState('');
  const [sessionError,setSessionError]=useState('');
  const online=ws?.readyState===WebSocket.OPEN;
  useEffect(()=>{void checkAuth();},[checkAuth]);
  useEffect(()=>{
    if(isAuthenticated) connectWebSocket();
    return ()=>disconnectWebSocket();
  },[isAuthenticated,connectWebSocket,disconnectWebSocket]);
  useEffect(()=>{
    function escape(e:KeyboardEvent){if(e.key==='Escape'){setMenu(false);setPanel(null);}}
    window.addEventListener('keydown',escape);return ()=>window.removeEventListener('keydown',escape);
  },[]);
  function open(view:View|Destination) {
    setMenu(false);setPanel(null);
    if(view==='Network'||view==='Talk'||view==='Planner'||view==='Inbox'||view==='Calendar') setPage(view);
    else if(view==='Files') {setDraft('Show my recent downloads.');setPage('Talk');}
    else if(view==='Voice') {document.querySelector<HTMLButtonElement>('.jarvis-composer button[type="button"]')?.focus();}
    else setPanel(view);
  }
  if(isLoading) return <div className="p-6">Opening Jarvis…</div>;
  if(!isAuthenticated) return <AuthModal/>;
  if(new URLSearchParams(location.search).get('view') === 'basic') return <BasicChat/>;
  const latestUser=messages.filter(m=>m.role==='user').slice(-1)[0];
  const latestReply=messages.filter(m=>m.role==='assistant' && m.content).slice(-1)[0];
  const busy=orbState==='thinking'||orbState==='acting';
  const phase=orbState==='error' && !pendingApprovals.length?'Check gateway status':!online?'Gateway offline':pendingApprovals.length?'Approval needed':isListening?'Listening':busy?'Working on your request':'Ready to talk';
  return <div className="jarvis-shell network-shell">
    {menu && <button className="rail-backdrop" onClick={()=>setMenu(false)} aria-label="Close navigation"/>}
    <aside className={'network-rail '+(menu?'opened':'')} aria-label="Sidebar">
      <div className="rail-brand"><span className="mini-core"/>Jarvis<button onClick={()=>setMenu(false)} aria-label="Close navigation"><X size={18}/></button></div>
      <button className="rail-new" onClick={async()=>{if(await createSession()){setDraft('');setSessionError('');open('Talk');}else setSessionError('Could not start a conversation.');}}><Plus size={16}/> New conversation</button>
      {sessionError && <small role="alert">{sessionError}</small>}
      <nav aria-label="Workspace navigation">{navigation.map(([name,Icon])=><button key={name} className={(panel||page)===name?'selected':''} onClick={()=>open(name)}><Icon size={17}/>{name}</button>)}</nav>
      <section className="rail-history"><small>History</small>{sessions.length?sessions.map(s=><div key={s.id}>
        <button title={s.title} aria-current={s.id===currentSessionId} onClick={()=>{void switchSession(s.id);setDraft('');open('Talk');}}>{s.title}</button>
        <button title="Delete conversation" onClick={()=>void deleteSession(s.id)}><Trash2 size={13}/></button>
      </div>):<p>No conversations yet</p>}</section>
      <button className="rail-account" onClick={()=>open('Account')}><CircleUser/><span>Owner account</span><ChevronsUpDown size={14}/></button>
    </aside>
    <div className="network-workspace"><header className="network-title"><button onClick={()=>setMenu(true)} aria-label="Open navigation"><Menu size={18}/></button>
      <h1>{page}</h1><button className="halt" onClick={triggerEmergencyStop} aria-label="Emergency stop" title="Emergency stop"><ShieldAlert size={16}/></button></header>
      <main className="network-surface">
        {page==='Planner' ? <Planner/> : page==='Inbox'||page==='Calendar' ? <WorkspaceInbox key={page} initial={page}/> : <>
        {page==='Network'?<><NetworkMap online={online} approvals={pendingApprovals.length} onOpen={open} onActivity={()=>open('Activity')}/>
          <div className="network-transcript" aria-live="polite">
            {latestUser && <small>You · {latestUser.content}</small>}
            <p>{busy?'Jarvis is working…':latestReply?.content||'Start a conversation with Jarvis.'}</p>
            {messages.length>0 && <button onClick={()=>open('Talk')}>Open conversation ↗</button>}
          </div></>:<ChatArea/>}
        <div className="voice-strip"><span aria-live="polite">{phase}</span><button aria-label="Voice replies" aria-pressed={voiceEnabled} title={voiceEnabled?'Mute replies':'Enable voice replies'} onClick={()=>{if(voiceEnabled)useAudioStore.getState().stopAudio();setVoiceEnabled(!voiceEnabled);}}>{voiceEnabled?<Volume2 size={15}/>:<VolumeX size={15}/>}</button></div>
        <Composer text={draft} setText={setDraft}/>
        </>}
      </main>
    </div>
    {panel==='Activity' && <RightActivityPanel isOpen onClose={()=>setPanel(null)}/>}
    <AgentsView isOpen={panel==='Assistant'} onClose={()=>setPanel(null)}/>
    <MemoryView isOpen={panel==='Memory'} onClose={()=>setPanel(null)}/>
    <SettingsView isOpen={panel==='Settings'} onClose={()=>setPanel(null)}/>
    <SystemView isOpen={panel==='Dashboard'} onClose={()=>setPanel(null)}/>
    {panel==='Account' && <div className="account-overlay"><section role="dialog" aria-label="Owner account"><button onClick={()=>setPanel(null)} aria-label="Close account"><X size={17}/></button>
      <h2>Owner account</h2><p>Signed in to this Jarvis gateway.</p><button onClick={logout}><LogOut size={16}/> Sign out</button></section></div>}
  </div>;
}
