// Client API des événements de notification ENISA (Phase 3 CRA)
import { api } from './client';

export type Milestone = 'early_warning' | 'notification' | 'final_report';
export type EnisaStatus = 'candidate' | 'confirmed' | 'dismissed' | 'closed';

export interface MilestoneState {
  due_at: string | null;
  remaining_seconds: number | null;
  overdue: boolean;
  submitted_at: string | null;
}

export interface EnisaEventSummary {
  id: number;
  tree_id: number;
  cve_id: string;
  status: EnisaStatus;
  detected_at: string;
  last_detected_at: string;
  confirmed_at: string | null;
  redetection_count: number;
  milestones: Partial<Record<Milestone, MilestoneState>>;
}

export interface EnisaEventDetail extends EnisaEventSummary {
  corrective_available_at: string | null;
  affected_assets: Array<{ asset_id: string }>;
  evaluation_context: Record<string, unknown>;
  drafts: Partial<Record<Milestone, Record<string, unknown>>>;
  confirmed_by: string | null;
  dismissed_by: string | null;
  dismiss_reason: string | null;
  close_reason: string | null;
}

export interface EnisaSummary {
  candidates: number;
  confirmed: number;
  overdue_milestones: number;
}

export async function listEnisaEvents(
  treeId: number,
  status?: string
): Promise<{ events: EnisaEventSummary[]; total: number }> {
  const params = new URLSearchParams({ tree_id: String(treeId) });
  if (status) params.set('status', status);
  return api.get<{ events: EnisaEventSummary[]; total: number }>(
    `/enisa/events?${params.toString()}`
  );
}

export async function getEnisaEvent(id: number): Promise<EnisaEventDetail> {
  return api.get<EnisaEventDetail>(`/enisa/events/${id}`);
}

export async function confirmEnisaEvent(id: number): Promise<EnisaEventDetail> {
  return api.post<EnisaEventDetail>(`/enisa/events/${id}/confirm`);
}

export async function dismissEnisaEvent(
  id: number,
  reason: string
): Promise<EnisaEventDetail> {
  return api.post<EnisaEventDetail>(`/enisa/events/${id}/dismiss`, { reason });
}

export async function reopenEnisaEvent(id: number): Promise<EnisaEventDetail> {
  return api.post<EnisaEventDetail>(`/enisa/events/${id}/reopen`);
}

export async function closeEnisaEvent(
  id: number,
  reason?: string
): Promise<EnisaEventDetail> {
  return api.post<EnisaEventDetail>(`/enisa/events/${id}/close`, { reason });
}

export async function submitEnisaMilestone(
  id: number,
  milestone: Milestone
): Promise<EnisaEventDetail> {
  return api.post<EnisaEventDetail>(`/enisa/events/${id}/submit/${milestone}`);
}

export async function saveEnisaDraft(
  id: number,
  milestone: Milestone,
  fields: Record<string, unknown>
): Promise<EnisaEventDetail> {
  return api.put<EnisaEventDetail>(`/enisa/events/${id}/draft/${milestone}`, {
    fields,
  });
}

export async function setEnisaCorrectiveDate(
  id: number,
  isoDate: string
): Promise<EnisaEventDetail> {
  return api.put<EnisaEventDetail>(`/enisa/events/${id}/corrective-date`, {
    corrective_available_at: isoDate,
  });
}

export async function exportEnisaMilestone(
  id: number,
  milestone: Milestone,
  format: 'json' | 'markdown'
): Promise<string> {
  const response = await fetch(
    `/api/v1/enisa/events/${id}/export/${milestone}?format=${format}`,
    { credentials: 'same-origin' }
  );
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Export failed' }));
    throw new Error(
      typeof error.detail === 'string' ? error.detail : 'Export failed'
    );
  }
  return response.text();
}

export async function getEnisaSummary(treeId: number): Promise<EnisaSummary> {
  return api.get<EnisaSummary>(`/enisa/summary?tree_id=${treeId}`);
}
