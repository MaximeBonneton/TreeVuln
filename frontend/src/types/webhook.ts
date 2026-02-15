export interface Webhook {
  id: number;
  tree_id: number;
  name: string;
  url: string;
  has_secret: boolean;
  headers: Record<string, string>;
  events: string[];
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface WebhookCreate {
  name: string;
  url: string;
  secret?: string;
  headers?: Record<string, string>;
  events: string[];
  is_active?: boolean;
}

export interface WebhookUpdate {
  name?: string;
  url?: string;
  secret?: string;
  headers?: Record<string, string>;
  events?: string[];
  is_active?: boolean;
}

export interface WebhookLog {
  id: number;
  webhook_id: number;
  event: string;
  status_code: number | null;
  request_body: Record<string, unknown>;
  response_body: string | null;
  success: boolean;
  error_message: string | null;
  duration_ms: number | null;
  created_at: string;
}

export interface WebhookTestResult {
  success: boolean;
  status_code: number | null;
  response_body: string | null;
  error_message: string | null;
  duration_ms: number | null;
}

export const WEBHOOK_EVENTS = [
  { value: 'on_act', label: 'Act', color: '#dc2626' },
  { value: 'on_attend', label: 'Attend', color: '#f97316' },
  { value: 'on_track_star', label: 'Track*', color: '#eab308' },
  { value: 'on_track', label: 'Track', color: '#22c55e' },
  { value: 'on_batch_complete', label: 'Batch terminé', color: '#6b7280' },
] as const;
