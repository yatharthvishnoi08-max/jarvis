import { useEffect, useRef, useState } from 'react';
import { Activity, AudioLines, Brain, CalendarDays, FileText, Folder, HardDrive, Instagram, Mail, MessageSquare, Monitor, Notebook, Radio, Sheet, Users, Youtube } from 'lucide-react';

import { useAuthStore } from '../stores/useAuthStore';

export type Destination = 'Talk' | 'Dashboard' | 'Memory' | 'Assistant' | 'Files' | 'Voice' | 'Inbox' | 'Calendar';
const nodes = [
  {name:'Voice', x:49, y:22, icon:AudioLines, action:'Voice'},
  {name:'Chat', x:69, y:41, icon:MessageSquare, action:'Talk'},
  {name:'Files', x:36, y:71, icon:Folder, action:'Files'},
  {name:'Memory', x:61, y:72, icon:Brain, action:'Memory'},
  {name:'Windows', x:29, y:42, icon:Monitor, action:'Dashboard'},
  {name:'Agents', x:47, y:88, icon:Users, action:'Assistant'},
  {name:'Gmail', x:59, y:9, icon:Mail, color:'#ed918f'},
  {name:'Calendar', x:75, y:20, icon:CalendarDays, color:'#8faff0'},
  {name:'Drive', x:86, y:38, icon:HardDrive, color:'#e7cb7d'},
  {name:'Docs', x:87, y:61, icon:FileText, color:'#91b9fc'},
  {name:'Sheets', x:76, y:81, icon:Sheet, color:'#79c9a8'},
  {name:'Notion', x:60, y:90, icon:Notebook},
  {name:'Instagram', x:18, y:72, icon:Instagram},
  {name:'YouTube', x:30, y:86, icon:Youtube},
  {name:'Podcasts', x:20, y:18, icon:Radio},
] as const;

function NeuralCore() {
  const canvas = useRef<HTMLCanvasElement>(null);
  useEffect(() => {
    const ctx = canvas.current?.getContext('2d');
    if (!ctx) return;
    ctx.clearRect(0,0,320,320);
    // Project a rippled sphere into a fixed-size, high-density canvas.
    function point(lat:number, lon:number) {
      const r = 119 + 5*Math.sin(7*lon+3*lat)*Math.cos(lat)**2 + 3*Math.sin(9*lat-2*lon)*Math.cos(lat);
      const x = r*Math.cos(lat)*Math.cos(lon), y = r*Math.sin(lat), z = r*Math.cos(lat)*Math.sin(lon);
      return [160+x*.91-y*.38,160+(x*.38+y*.91)*.94+z*.17,z];
    }
    const fill = ctx.createRadialGradient(120,90,10,160,160,130);
    fill.addColorStop(0,'#622843'); fill.addColorStop(.67,'#2a1428'); fill.addColorStop(.9,'#51263d'); fill.addColorStop(1,'#f38bc7');
    ctx.beginPath();ctx.arc(160,160,116,0,2*Math.PI);ctx.fillStyle=fill;ctx.fill();
    for(let i=0;i<32;i++) for(let j=0;j<56;j++) {
      const a=-Math.PI/2+i*Math.PI/32,b=j*2*Math.PI/56;
      const p=point(a,b); if(p[2]<-7)continue;
      const q=point(a+Math.PI/32,b+.052*Math.sin(a*8)),s=point(a,b+2*Math.PI/56);
      const alpha=.09+.28*(.5+.5*Math.sin(i*.7+j*.39))+.34*(1-Math.max(0,p[2])/125)**3;
      ctx.strokeStyle='rgba(255,145,209,'+alpha+')'; ctx.lineWidth=1;
      ctx.beginPath();ctx.moveTo(q[0],q[1]);ctx.lineTo(p[0],p[1]);ctx.lineTo(s[0],s[1]);ctx.stroke();
    }
  },[]);
  return <canvas ref={canvas} width="320" height="320" aria-hidden="true"/>;
}

export function NetworkMap({online, onOpen, onActivity, approvals}:{
  online:boolean; onOpen:(d:Destination)=>void; onActivity:()=>void; approvals:number
}) {
  const [info,setInfo]=useState('');
  const [googleOnline,setGoogleOnline]=useState(false);
  const token=useAuthStore(s=>s.token);
  useEffect(()=>{
    const controller=new AbortController();
    async function check(){
      try {
        const r=await fetch('/api/workspace/status',{headers:{Authorization:'Bearer '+token},signal:controller.signal});
        const status=r.ok?await r.json():null;
        if(!controller.signal.aborted)setGoogleOnline(status?.state==='connected');
      } catch {if(!controller.signal.aborted)setGoogleOnline(false);}
    }
    void check(); const timer=setInterval(check,30000);
    return ()=>{controller.abort();clearInterval(timer);};
  },[token]);
  function linked(n:typeof nodes[number]){
    return 'action' in n ? online : googleOnline && (n.name==='Gmail'||n.name==='Calendar');
  }
  return <section className="network-map" aria-label="Jarvis network">
    <div className="map-meta"><small>Neural network</small><p>{online ? 'Gateway connected' : 'Gateway offline'}</p></div>
    <div className="map-tools"><span className="map-live">{online ? 'Live' : 'Offline'}</span>
      <button onClick={onActivity}><Activity size={14}/> Activity {approvals || ''}</button></div>
    <div className="map-space">
      <svg className="map-lines" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">
        {nodes.map((n,i)=><g key={n.name}><line x1="50" y1="51" x2={n.x} y2={n.y} className={linked(n) ? 'on' : ''}/>
          <line x1={n.x} y1={n.y} x2={nodes[(i+4)%nodes.length].x} y2={nodes[(i+4)%nodes.length].y} className="mesh"/></g>)}
      </svg>
      <button className="map-core" aria-label="Start voice conversation" onClick={()=>onOpen('Voice')}><NeuralCore/></button>
      {nodes.map(n=><button key={n.name} className={'map-node '+(linked(n) ? 'local' : 'external')} style={{left:n.x+'%',top:n.y+'%'}}
        title={'action' in n ? 'Open '+n.name : n.name==='Gmail'||n.name==='Calendar'?'Open '+n.name:n.name+' · Not connected'}
        onClick={()=>{if('action' in n) {setInfo(''); onOpen(n.action);} else if(n.name==='Gmail' || n.name==='Calendar') onOpen(n.name==='Gmail'?'Inbox':'Calendar'); else setInfo(n.name+' is not connected.');}}>
        <span style={{color:'color' in n?n.color:undefined}}><n.icon/></span><small>{n.name}</small>
      </button>)}
    </div>
    {info && <button className="map-info" onClick={()=>setInfo('')} role="status">{info} ×</button>}
  </section>;
}
