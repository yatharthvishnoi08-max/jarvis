import { useEffect, useState } from 'react';
import { Bell, Check, ExternalLink, RefreshCw } from 'lucide-react';
import { useAuthStore } from '../stores/useAuthStore';

type Decision={id:string;kind:'task'|'email'|'conflict';title:string;reason:string;task_id?:number;thread_id?:string};
export function Decisions() {
  const token=useAuthStore(s=>s.token);
  const [data,setData]=useState<{items:Decision[];google_state:string}>();
  const [error,setError]=useState('');
  const [busy,setBusy]=useState('');
  const [version,reload]=useState(0);
  useEffect(()=>{
    const controller=new AbortController();
    const refresh=async()=>{
      try {
        const r=await fetch('/api/briefing',{headers:{Authorization:'Bearer '+token},signal:controller.signal});
        if(!r.ok)throw new Error();
        const body=await r.json();
        if(!Array.isArray(body.items))throw new Error();
        if(!controller.signal.aborted){setData(body);setError('');}
      } catch {if(!controller.signal.aborted)setError('Could not refresh your briefing.');}
    };
    void refresh();const timer=setInterval(refresh,30000);
    return ()=>{controller.abort();clearInterval(timer);};
  },[token,version]);
  async function handle(item:Decision){
    setBusy(item.id);
    try{
      const path=item.kind==='task'?'/api/planner/'+item.task_id+'/complete':'/api/briefing/handled';
      const r=await fetch(path,{method:'POST',headers:{Authorization:'Bearer '+token,'Content-Type':'application/json'},
        body:item.kind==='task'?undefined:JSON.stringify({id:item.id})});
      if(!r.ok)throw new Error();
      reload(v=>v+1);
    }catch{setError('Could not save your decision.');}finally{setBusy('');}
  }
  return <section className="planner-page decisions"><header><Bell/><h2>Needs you</h2></header>
    {error && <p role="alert">{error} <button onClick={()=>reload(v=>v+1)}><RefreshCw size={14}/>Retry</button></p>}
    {!data&&!error&&<p>Checking for decisions…</p>}
    {data&&<><p>{data.google_state==='connected'?'From your planner, Gmail and Calendar.':'From your planner. Google updates are unavailable.'}</p>
      {!data.items.length && <h3>No outstanding decisions.</h3>}
      <ul>{data.items.map(item=><li key={item.id}><div><small>{item.reason}</small><h3>{item.title}</h3>
        {item.thread_id&&<a href={'https://mail.google.com/mail/#all/'+encodeURIComponent(item.thread_id)} target="_blank" rel="noreferrer">Open email <ExternalLink size={12}/></a>}</div>
        <button disabled={!!busy} onClick={()=>void handle(item)}><Check size={14}/>{item.kind==='task'?'Complete':'Handled'}</button></li>)}</ul></>}
  </section>;
}
