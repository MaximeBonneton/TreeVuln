import { useCallback, useEffect, useState } from 'react';
import { X, AlertTriangle } from 'lucide-react';
import {
  listEnisaEvents,
  type EnisaEventSummary,
  type EnisaStatus,
  type Milestone,
  type MilestoneState,
} from '@/api/enisa';
import { EnisaEventDetail } from './EnisaEventDetail';
import { STATUS_LABELS, STATUS_BADGE_CLASS, MILESTONE_LABELS, MilestoneCountdown } from './enisaShared';

interface EnisaPanelProps {
  open: boolean;
  onClose: () => void;
  treeId: number;
}

const REFRESH_INTERVAL_MS = 60_000;

/**
 * Panneau des événements de notification ENISA d'un arbre : liste avec
 * statut et échéances des jalons, rafraîchi toutes les 60s tant qu'ouvert.
 * Clic sur une ligne -> ouvre le détail (EnisaEventDetail).
 */
export function EnisaPanel({ open, onClose, treeId }: EnisaPanelProps) {
  const [events, setEvents] = useState<EnisaEventSummary[]>([]);
  const [statusFilter, setStatusFilter] = useState<'all' | EnisaStatus>('all');
  const [selectedEventId, setSelectedEventId] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const data = await listEnisaEvents(
        treeId,
        statusFilter === 'all' ? undefined : statusFilter
      );
      setEvents(data.events);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Loading failed');
    } finally {
      setLoading(false);
    }
  }, [treeId, statusFilter]);

  // Fetch à l'ouverture / changement d'arbre / filtre, puis polling 60s
  useEffect(() => {
    if (!open) return;
    refresh();
    const interval = setInterval(refresh, REFRESH_INTERVAL_MS);
    return () => clearInterval(interval);
  }, [open, refresh]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-[760px] max-h-[85vh] flex flex-col">
        <div className="flex items-center justify-between p-4 border-b">
          <h2 className="font-bold text-gray-800 flex items-center gap-2">
            <AlertTriangle size={18} className="text-orange-500" />
            Notifications ENISA
          </h2>
          <button onClick={onClose} className="p-1 hover:bg-gray-100 rounded">
            <X size={20} />
          </button>
        </div>

        <div className="p-3 border-b flex items-center gap-2">
          <label htmlFor="enisa-status-filter" className="text-sm text-gray-600">
            Statut :
          </label>
          <select
            id="enisa-status-filter"
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value as 'all' | EnisaStatus)}
            className="text-sm border rounded-md px-2 py-1"
          >
            <option value="all">Tous</option>
            <option value="candidate">Candidat</option>
            <option value="confirmed">Confirmé</option>
            <option value="dismissed">Rejeté</option>
            <option value="closed">Clôturé</option>
          </select>
          {loading && <span className="text-xs text-gray-400">Chargement…</span>}
        </div>

        {error && (
          <p className="mx-4 mt-3 text-sm text-amber-700 bg-amber-50 rounded p-2">{error}</p>
        )}

        <div className="flex-1 overflow-y-auto">
          {events.length === 0 && !loading ? (
            <p className="p-6 text-sm text-gray-500 italic">Aucun événement ENISA.</p>
          ) : (
            <table className="w-full text-sm">
              <thead className="sticky top-0 bg-gray-50">
                <tr className="text-left text-xs text-gray-500">
                  <th className="px-3 py-2">CVE</th>
                  <th className="px-3 py-2">Statut</th>
                  <th className="px-3 py-2">Jalons</th>
                </tr>
              </thead>
              <tbody>
                {events.map((event) => (
                  <tr
                    key={event.id}
                    onClick={() => setSelectedEventId(event.id)}
                    className="border-t hover:bg-gray-50 cursor-pointer"
                  >
                    <td className="px-3 py-2 font-mono text-xs text-gray-800 align-top">
                      {event.cve_id}
                    </td>
                    <td className="px-3 py-2 align-top">
                      <span
                        className={`inline-block text-xs px-1.5 py-0.5 rounded ${STATUS_BADGE_CLASS[event.status]}`}
                      >
                        {STATUS_LABELS[event.status]}
                      </span>
                      {event.redetection_count > 0 && (
                        <div className="text-xs text-gray-400 mt-0.5">
                          re-détecté ×{event.redetection_count}
                        </div>
                      )}
                    </td>
                    <td className="px-3 py-2">
                      <div className="flex flex-col gap-0.5">
                        {(
                          Object.entries(event.milestones) as [Milestone, MilestoneState][]
                        ).map(([m, state]) => (
                          <div key={m} className="flex items-center gap-1.5">
                            <span className="text-xs text-gray-500 w-28 shrink-0">
                              {MILESTONE_LABELS[m]}
                            </span>
                            <MilestoneCountdown milestone={m} state={state} />
                          </div>
                        ))}
                        {Object.keys(event.milestones).length === 0 && (
                          <span className="text-xs text-gray-400">—</span>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>

      {selectedEventId !== null && (
        <EnisaEventDetail
          eventId={selectedEventId}
          onClose={() => setSelectedEventId(null)}
          onChanged={refresh}
        />
      )}
    </div>
  );
}

export default EnisaPanel;
