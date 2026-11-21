import {useEffect, useState} from 'react';
import {useAuthStore} from '../stores/useAuthStore';
export const UI_RELEASE = 'wake-2026.11.21.1';
export function RuntimeBadge() {
  const [host, setHost] = useState('Checking gateway…');
  const [mismatch, setMismatch] = useState(false);
  useEffect(() => {
    const controller = new AbortController();
    fetch('/api/runtime', {cache: 'no-store', signal: controller.signal, headers: {Authorization: 'Bearer ' + useAuthStore.getState().token}})
      .then(r => {if (!r.ok) throw new Error(); return r.json();})
      .then(data => {setHost(data.hostname); setMismatch(data.release !== UI_RELEASE);})
      .catch(() => {if (!controller.signal.aborted) {setHost('Gateway version unavailable');setMismatch(true);}});
    return () => controller.abort();
  }, []);
  return <div className="runtime-badge" role="status"><small>{UI_RELEASE} · {host}</small>{mismatch && <strong>Update mismatch — restart gateway and refresh this page.</strong>}</div>;
}
