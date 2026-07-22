// Libellés et composant partagés entre EnisaPanel et EnisaEventDetail.
// Extrait dans un module dédié pour éviter le cycle d'imports
// EnisaPanel -> EnisaEventDetail -> EnisaPanel.
import type { EnisaStatus, Milestone, MilestoneState } from '@/api/enisa';

export const STATUS_LABELS: Record<EnisaStatus, string> = {
  candidate: 'Candidat',
  confirmed: 'Confirmé',
  dismissed: 'Rejeté',
  closed: 'Clôturé',
};

export const STATUS_BADGE_CLASS: Record<EnisaStatus, string> = {
  candidate: 'bg-gray-100 text-gray-600',
  confirmed: 'bg-blue-100 text-blue-700',
  dismissed: 'bg-gray-100 text-gray-400 line-through',
  closed: 'bg-green-100 text-green-700',
};

export const MILESTONE_LABELS: Record<Milestone, string> = {
  early_warning: 'Alerte précoce',
  notification: 'Notification',
  final_report: 'Rapport final',
};

// Formate un nombre de secondes restantes en "Xj" ou "Xh Ymin"
export function formatRemaining(seconds: number): string {
  const abs = Math.max(0, Math.floor(seconds));
  const hours = Math.floor(abs / 3600);
  if (hours >= 24) {
    return `${Math.floor(hours / 24)} j`;
  }
  const minutes = Math.floor((abs % 3600) / 60);
  return `${hours} h ${minutes} min`;
}

// Compte à rebours d'un jalon : vert normalement, orange sous 12h,
// rouge + "En retard" si dépassé. final_report sans due_at attend un correctif.
export function MilestoneCountdown({
  milestone,
  state,
}: {
  milestone: Milestone;
  state: MilestoneState;
}) {
  if (state.submitted_at) {
    return <span className="text-xs text-green-600">Soumis</span>;
  }
  if (milestone === 'final_report' && state.due_at === null) {
    return <span className="text-xs text-gray-500">En attente de correctif</span>;
  }
  if (state.overdue) {
    return <span className="text-xs font-medium text-red-600">En retard</span>;
  }
  const remaining = state.remaining_seconds ?? 0;
  const colorClass = remaining < 12 * 3600 ? 'text-orange-600' : 'text-green-600';
  return (
    <span className={`text-xs font-medium ${colorClass}`}>{formatRemaining(remaining)}</span>
  );
}
