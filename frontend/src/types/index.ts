export type OrbState =
  | 'idle'
  | 'listening'
  | 'thinking'
  | 'acting'
  | 'speaking'
  | 'disconnected'
  | 'error';

export interface ToolCall {
  id: string;
  type: string;
  function: {
    name: string;
    arguments: string;
  };
}

export interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system' | 'tool';
  content: string;
  timestamp: number;
  tool_calls?: ToolCall[];
  tool_call_id?: string;
  audio_id?: string;
  audio_url?: string;
}

export interface SessionMeta {
  id: string;
  title: string;
  created_at: number;
  updated_at: number;
  message_count?: number;
}

export interface ApprovalRequest {
  id: string;
  session_id: string;
  tool: string;
  args: Record<string, any>;
  policy_level: 'CONFIRM' | 'CRITICAL';
  summary: string;
  created_at: number;
  expires_at: number;
  status: 'PENDING' | 'APPROVED' | 'REJECTED' | 'EXPIRED' | 'CANCELLED';
  ttl_remaining: number;
}

export interface Telemetry {
  cpu_percent: number;
  ram_percent: number;
  ram_used_mb: number;
  ram_total_mb: number;
  disk_percent: number;
  disk_free_gb: number;
  disk_total_gb: number;
  uptime_seconds: number;
  hostname: string;
  network: {
    lan: string[];
    tailscale: string[];
  };
  active_model: string;
  voice_configured: boolean;
}

export interface VoiceMeta {
  id: string;
  name: string;
  description: string;
  is_active: boolean;
}

export interface AuditEvent {
  timestamp: number;
  iso_time: string;
  event_type: string;
  session_id: string;
  action: string;
  tool: string;
  args: any;
  policy: string;
  status: string;
  detail: string;
}

export interface Employee {
  name: string;
  summary: string;
  sop: string;
}
