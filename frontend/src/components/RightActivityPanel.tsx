import React, { useEffect, useRef, useState } from 'react';
import { useJarvisStore } from '../stores/useJarvisStore';
import { useActivityStore } from '../stores/useActivityStore';
import { ApprovalRequest } from '../types';
import { Activity, AlertTriangle, Check, Clock, ShieldCheck, X } from 'lucide-react';
import './activity-panel.css';

const actionNames: Record<string, string> = {
  open_app: 'Open an app', focus_window: 'Focus a window', keyboard_type: 'Type text',
  keyboard_hotkey: 'Use a keyboard shortcut', keyboard_press: 'Press a key',
  mouse_click: 'Click on screen', capture_screen: 'Inspect the screen', analyze_image: 'Review an image',
  read_file: 'Read a file', write_file: 'Write a file', add_task: 'Add a task', complete_task: 'Complete a task',
};
const actionName = (name: string) => actionNames[name] || name.replace(/_/g, ' ');
const statusNames: Record<string, string> = {
  SUCCESS: 'Finished', ERROR: 'Failed', BLOCKED: 'Blocked', RUNNING: 'Working', ATTEMPT: 'Requested',
  PENDING: 'Approval requested', STOPPED: 'Stopped', APPROVED: 'Approved', REJECTED: 'Declined', CANCELLED: 'Stopped', EXPIRED: 'Expired',
};

export const RightActivityPanel: React.FC<{ isOpen: boolean; onClose: () => void }> = ({ isOpen, onClose }) => {
  const { pendingApprovals, decideApproval, actionError } = useJarvisStore();
  const { events, fetchActivity } = useActivityStore();
  const closeButton = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!isOpen) return;
    const previous = document.activeElement as HTMLElement | null;
    closeButton.current?.focus();
    fetchActivity();
    const timer = setInterval(fetchActivity, 5000);
    return () => { clearInterval(timer); previous?.focus(); };
  }, [isOpen, fetchActivity]);

  if (!isOpen) return null;
  const trapKeys = (event: React.KeyboardEvent<HTMLElement>) => {
    if (event.key === 'Escape') { event.preventDefault(); onClose(); }
    if (event.key !== 'Tab') return;
    const controls = Array.from(event.currentTarget.querySelectorAll<HTMLElement>(
      'button:not([disabled]), summary, a[href], [tabindex="0"]'
    )).filter(element => element.getClientRects().length > 0);
    const first = controls[0], last = controls[controls.length - 1];
    if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last?.focus(); }
    else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first?.focus(); }
  };

  return <>
    <div className="activity-backdrop" onClick={onClose} />
    <aside className="activity-sheet" role="dialog" aria-modal="true" aria-labelledby="activity-title" onKeyDown={trapKeys}>
      <header className="activity-heading">
        <div><span className="activity-eyebrow">JARVIS / WORK LOG</span><h2 id="activity-title"><Activity size={20}/>Activity</h2></div>
        <button ref={closeButton} onClick={onClose} className="activity-icon-button" aria-label="Close activity"><X size={20}/></button>
      </header>
      <div className="activity-scroll">
        {actionError && <p role="alert" className="activity-action-error">{actionError}</p>}
        <section aria-labelledby="decisions-title">
          <div className="activity-section-heading"><h3 id="decisions-title">Your decisions</h3><span>{pendingApprovals.length}</span></div>
          {pendingApprovals.length ? pendingApprovals.map(request =>
            <ApprovalCard key={request.id} request={request} onDecide={async (id, decision) => { await decideApproval(id, decision); await fetchActivity(); }}/>
          ) : <div className="activity-empty"><ShieldCheck size={20}/><div><strong>Nothing waiting on you</strong><p>Requests that need your approval appear here.</p></div></div>}
        </section>
        <section aria-labelledby="work-title">
          <div className="activity-section-heading"><h3 id="work-title">Recent work</h3><span className="activity-refresh"><Clock size={13}/>Updates every 5s</span></div>
          {!events.length && <p className="activity-empty-copy">Jarvis’s actions and their outcomes will appear here.</p>}
          <ol className="activity-events">{events.map((event, index) => {
            const failed = ['ERROR', 'BLOCKED', 'REJECTED'].includes(event.status);
            const status = statusNames[event.status] || event.status;
            return <li key={`${event.timestamp}-${index}`} className="activity-event" data-failed={failed}>
              <div className="activity-event-top"><span className="activity-status" data-state={event.status}>{failed ? <AlertTriangle size={13}/> : event.status === 'SUCCESS' ? <Check size={13}/> : <Clock size={13}/>}{status}</span><time dateTime={new Date(event.timestamp * 1000).toISOString()}>{new Date(event.timestamp * 1000).toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'})}</time></div>
              <h4>{event.tool ? actionName(event.tool) : event.event_type === 'TURN_FAILED' ? 'Conversation interrupted' : actionName(event.event_type).toLowerCase()}</h4>
              {event.detail && <p className="activity-event-detail">{event.detail}</p>}
              {event.args && <details><summary>View details</summary><pre>{typeof event.args === 'string' ? event.args : JSON.stringify(event.args, null, 2)}</pre></details>}
            </li>;
          })}</ol>
        </section>
      </div>
      <footer className="activity-footer">Finished means the action returned. Check its result before retrying a task.</footer>
    </aside>
  </>;
};

const ApprovalCard: React.FC<{request: ApprovalRequest; onDecide: (id:string, decision:'approve'|'reject') => Promise<void>}> = ({request, onDecide}) => {
  const [now, setNow] = useState(Date.now());
  const [submitting, setSubmitting] = useState(false);
  const decide = async (decision: 'approve' | 'reject') => {
    if (submitting) return;
    setSubmitting(true);
    try { await onDecide(request.id, decision); } finally { setSubmitting(false); }
  };
  useEffect(() => { const timer = setInterval(() => setNow(Date.now()), 1000); return () => clearInterval(timer); }, []);
  const remaining = Math.max(0, Math.ceil(request.expires_at - now / 1000));
  const expired = remaining === 0;
  return <article className="activity-approval" data-critical={request.policy_level === 'CRITICAL'}>
    <div className="activity-approval-meta"><span><ShieldCheck size={15}/>{request.policy_level === 'CRITICAL' ? 'Sensitive action' : 'Approval needed'}</span><span>{expired ? 'Expired' : `${remaining}s left`}</span></div>
    <h4>{actionName(request.tool)}</h4>
    <pre aria-label="Requested action details">{JSON.stringify(request.args, null, 2)}</pre>
    <p>{expired ? 'This request has expired. Ask Jarvis to prepare the action again.' : request.summary}</p>
    <div className="activity-decisions"><button disabled={expired || submitting} onClick={() => decide('reject')}><X size={16}/>Decline</button><button disabled={expired || submitting} className="activity-approve" onClick={() => decide('approve')}><Check size={16}/>Approve</button></div>
  </article>;
};
