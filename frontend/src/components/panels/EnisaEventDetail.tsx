import { useCallback, useEffect, useState } from 'react';
import { X, FileJson, FileText, CheckCircle2, RotateCcw } from 'lucide-react';
import {
  getEnisaEvent,
  confirmEnisaEvent,
  dismissEnisaEvent,
  reopenEnisaEvent,
  closeEnisaEvent,
  submitEnisaMilestone,
  saveEnisaDraft,
  setEnisaCorrectiveDate,
  exportEnisaMilestone,
  type EnisaEventDetail as EnisaEventDetailData,
  type Milestone,
} from '@/api/enisa';
import { useConfirm } from '@/hooks/useConfirm';
import { ConfirmDialog } from '@/components/ui/ConfirmDialog';
import { MILESTONE_LABELS, STATUS_LABELS, MilestoneCountdown } from './enisaShared';

interface EnisaEventDetailProps {
  eventId: number;
  onClose: () => void;
  onChanged: () => void; // rafraîchit la liste du panel parent après mutation
}

const MILESTONES: Milestone[] = ['early_warning', 'notification', 'final_report'];

// datetime-local (heure locale, sans fuseau) <-> ISO 8601 UTC
// Exportées (nommées) pour être testées isolément : régression silencieuse
// sinon en cas d'erreur de fuseau/format.
export function isoToDatetimeLocal(iso: string | null): string {
  if (!iso) return '';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return '';
  const pad = (n: number) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

export function datetimeLocalToIso(value: string): string | null {
  if (!value) return null;
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return null;
  return d.toISOString();
}

function downloadText(content: string, filename: string, mimeType: string): void {
  const blob = new Blob([content], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

/**
 * Détail d'un événement ENISA : cycle de vie (confirmer/rejeter/réouvrir/
 * clôturer), échéances des trois jalons, formulaire de brouillon éditable
 * et export. Ouvert depuis EnisaPanel au clic sur une ligne.
 */
export function EnisaEventDetail({ eventId, onClose, onChanged }: EnisaEventDetailProps) {
  const [detail, setDetail] = useState<EnisaEventDetailData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const { confirm, confirmDialogProps } = useConfirm();

  // Rejet : motif saisi en ligne
  const [showDismissForm, setShowDismissForm] = useState(false);
  const [dismissReason, setDismissReason] = useState('');

  // Clôture : motif optionnel (obligatoire si des jalons ne sont pas soumis)
  const [showCloseForm, setShowCloseForm] = useState(false);
  const [closeReason, setCloseReason] = useState('');

  // Date de correctif disponible
  const [correctiveDate, setCorrectiveDate] = useState('');

  // Formulaire de jalon en cours d'édition
  const [editingMilestone, setEditingMilestone] = useState<Milestone | null>(null);
  const [draftFields, setDraftFields] = useState<Record<string, string>>({});
  const [draftLoading, setDraftLoading] = useState(false);

  const refresh = useCallback(async () => {
    try {
      const data = await getEnisaEvent(eventId);
      setDetail(data);
      setCorrectiveDate(isoToDatetimeLocal(data.corrective_available_at));
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Loading failed');
    }
  }, [eventId]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const afterMutation = (data: EnisaEventDetailData) => {
    setDetail(data);
    onChanged();
  };

  const handleConfirm = async () => {
    const ok = await confirm(
      'Confirm event',
      'Confirmation anchors the notification clock (early warning / notification / final report). Continue?'
    );
    if (!ok) return;
    setBusy(true);
    try {
      afterMutation(await confirmEnisaEvent(eventId));
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Action failed');
    } finally {
      setBusy(false);
    }
  };

  const handleDismissSubmit = async () => {
    if (!dismissReason.trim()) return;
    setBusy(true);
    try {
      afterMutation(await dismissEnisaEvent(eventId, dismissReason.trim()));
      setShowDismissForm(false);
      setDismissReason('');
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Action failed');
    } finally {
      setBusy(false);
    }
  };

  const handleReopen = async () => {
    const ok = await confirm('Reopen event', 'The event returns to candidate status. Continue?');
    if (!ok) return;
    setBusy(true);
    try {
      afterMutation(await reopenEnisaEvent(eventId));
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Action failed');
    } finally {
      setBusy(false);
    }
  };

  const handleCloseSubmit = async () => {
    const allSubmitted = MILESTONES.every(
      (m) => detail?.milestones[m]?.submitted_at != null
    );
    if (!allSubmitted && !closeReason.trim()) return;
    const ok = await confirm(
      'Close event',
      allSubmitted
        ? 'All milestones are submitted. Close this event?'
        : 'Some milestones are not submitted. Close anyway with this reason?',
      'warning'
    );
    if (!ok) return;
    setBusy(true);
    try {
      afterMutation(await closeEnisaEvent(eventId, closeReason.trim() || undefined));
      setShowCloseForm(false);
      setCloseReason('');
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Action failed');
    } finally {
      setBusy(false);
    }
  };

  const handleCorrectiveDateSave = async () => {
    const iso = datetimeLocalToIso(correctiveDate);
    if (!iso) return;
    setBusy(true);
    try {
      afterMutation(await setEnisaCorrectiveDate(eventId, iso));
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Action failed');
    } finally {
      setBusy(false);
    }
  };

  const handleSubmitMilestone = async (milestone: Milestone) => {
    const ok = await confirm(
      'Mark as submitted',
      `Mark "${MILESTONE_LABELS[milestone]}" as submitted on the ENISA platform?`
    );
    if (!ok) return;
    setBusy(true);
    try {
      afterMutation(await submitEnisaMilestone(eventId, milestone));
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Action failed');
    } finally {
      setBusy(false);
    }
  };

  const openMilestoneForm = async (milestone: Milestone) => {
    setEditingMilestone(milestone);
    setDraftLoading(true);
    try {
      // Pré-remplissage fusionné (contenu calculé + brouillon existant)
      const raw = await exportEnisaMilestone(eventId, milestone, 'json');
      const parsed = JSON.parse(raw) as Record<string, unknown>;
      const asStrings: Record<string, string> = {};
      for (const [key, value] of Object.entries(parsed)) {
        asStrings[key] = typeof value === 'string' ? value : JSON.stringify(value);
      }
      setDraftFields(asStrings);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Export failed');
      setDraftFields({});
    } finally {
      setDraftLoading(false);
    }
  };

  const handleSaveDraft = async () => {
    if (!editingMilestone) return;
    setBusy(true);
    try {
      afterMutation(await saveEnisaDraft(eventId, editingMilestone, draftFields));
      setEditingMilestone(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Save failed');
    } finally {
      setBusy(false);
    }
  };

  const handleExport = async (milestone: Milestone, format: 'json' | 'markdown') => {
    try {
      const content = await exportEnisaMilestone(eventId, milestone, format);
      const ext = format === 'json' ? 'json' : 'md';
      const mimeType = format === 'json' ? 'application/json' : 'text/markdown';
      downloadText(content, `${detail?.cve_id ?? eventId}_${milestone}.${ext}`, mimeType);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Export failed');
    }
  };

  if (!detail) {
    return (
      <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-[60]">
        <div className="bg-white rounded-lg shadow-xl w-[600px] p-6">
          {error ? (
            <p className="text-sm text-red-600">{error}</p>
          ) : (
            <p className="text-sm text-gray-500 italic">Chargement…</p>
          )}
        </div>
      </div>
    );
  }

  // Contexte d'évaluation : décision + champs de vulnérabilité, sans l'audit trail (trop volumineux)
  const contextEntries = Object.entries(detail.evaluation_context).filter(
    ([key]) => key !== 'audit_trail'
  );

  // Clôture possible librement si les 3 jalons sont soumis, sinon motif requis
  const allMilestonesSubmitted = MILESTONES.every(
    (m) => detail.milestones[m]?.submitted_at != null
  );
  const closeBlocked = !allMilestonesSubmitted && !closeReason.trim();

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-[60]">
      <div className="bg-white rounded-lg shadow-xl w-[640px] max-h-[85vh] flex flex-col">
        <div className="flex items-center justify-between p-4 border-b">
          <div>
            <h2 className="font-bold text-gray-800 font-mono">{detail.cve_id}</h2>
            <span className="text-xs text-gray-500">{STATUS_LABELS[detail.status]}</span>
          </div>
          <button onClick={onClose} className="p-1 hover:bg-gray-100 rounded">
            <X size={20} />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {error && (
            <p className="text-sm text-amber-700 bg-amber-50 rounded p-2">{error}</p>
          )}

          {/* Actions de cycle de vie selon le statut */}
          <div className="border rounded-md p-3 space-y-2">
            {detail.status === 'candidate' && (
              <div className="flex items-center gap-2">
                <button
                  onClick={handleConfirm}
                  disabled={busy}
                  className="px-3 py-1.5 text-sm bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
                >
                  Confirmer
                </button>
                {!showDismissForm ? (
                  <button
                    onClick={() => setShowDismissForm(true)}
                    className="px-3 py-1.5 text-sm text-red-600 hover:bg-red-50 rounded-md"
                  >
                    Rejeter
                  </button>
                ) : (
                  <div className="flex-1 flex items-center gap-2">
                    <input
                      type="text"
                      value={dismissReason}
                      onChange={(e) => setDismissReason(e.target.value)}
                      placeholder="Motif du rejet…"
                      autoFocus
                      className="flex-1 px-2 py-1 text-sm border rounded"
                    />
                    <button
                      onClick={handleDismissSubmit}
                      disabled={busy || !dismissReason.trim()}
                      className="px-2 py-1 text-sm bg-red-600 text-white rounded-md hover:bg-red-700 disabled:opacity-50"
                    >
                      Envoyer
                    </button>
                    <button
                      onClick={() => {
                        setShowDismissForm(false);
                        setDismissReason('');
                      }}
                      className="p-1 hover:bg-gray-100 rounded"
                    >
                      <X size={16} />
                    </button>
                  </div>
                )}
              </div>
            )}

            {detail.status === 'dismissed' && (
              <div className="space-y-2">
                {detail.dismiss_reason && (
                  <p className="text-sm text-gray-600">
                    Motif : {detail.dismiss_reason}
                    {detail.dismissed_by && ` (${detail.dismissed_by})`}
                  </p>
                )}
                <button
                  onClick={handleReopen}
                  disabled={busy}
                  className="flex items-center gap-1 px-3 py-1.5 text-sm bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
                >
                  <RotateCcw size={14} />
                  Réouvrir
                </button>
              </div>
            )}

            {detail.status === 'confirmed' && (
              <div className="space-y-3">
                <div className="flex items-center gap-2">
                  <label className="text-sm text-gray-600">Correctif disponible le :</label>
                  <input
                    type="datetime-local"
                    value={correctiveDate}
                    onChange={(e) => setCorrectiveDate(e.target.value)}
                    className="px-2 py-1 text-sm border rounded"
                  />
                  <button
                    onClick={handleCorrectiveDateSave}
                    disabled={busy || !correctiveDate}
                    className="px-2 py-1 text-sm bg-gray-600 text-white rounded-md hover:bg-gray-700 disabled:opacity-50"
                  >
                    Enregistrer
                  </button>
                </div>

                {!showCloseForm ? (
                  <button
                    onClick={() => setShowCloseForm(true)}
                    className="px-3 py-1.5 text-sm text-gray-700 hover:bg-gray-100 rounded-md border"
                  >
                    Clôturer
                  </button>
                ) : (
                  <div className="flex items-center gap-2">
                    <input
                      type="text"
                      value={closeReason}
                      onChange={(e) => setCloseReason(e.target.value)}
                      placeholder="Motif (requis si jalons non soumis)…"
                      className="flex-1 px-2 py-1 text-sm border rounded"
                    />
                    <button
                      onClick={handleCloseSubmit}
                      disabled={busy || closeBlocked}
                      title={closeBlocked ? 'Motif requis : des jalons ne sont pas soumis' : undefined}
                      className="px-2 py-1 text-sm bg-gray-700 text-white rounded-md hover:bg-gray-800 disabled:opacity-50"
                    >
                      Confirmer la clôture
                    </button>
                    <button
                      onClick={() => {
                        setShowCloseForm(false);
                        setCloseReason('');
                      }}
                      className="p-1 hover:bg-gray-100 rounded"
                    >
                      <X size={16} />
                    </button>
                  </div>
                )}
              </div>
            )}

            {detail.status === 'closed' && detail.close_reason && (
              <p className="text-sm text-gray-600">Motif de clôture : {detail.close_reason}</p>
            )}

            {detail.redetection_count > 0 && (
              <p className="text-xs text-amber-700">
                {detail.status === 'dismissed'
                  ? 'Rejeté mais toujours détecté'
                  : `Re-détecté ×${detail.redetection_count}`}
              </p>
            )}
          </div>

          {/* Chronologie des jalons */}
          <div className="border rounded-md divide-y">
            {MILESTONES.map((m) => {
              const state = detail.milestones[m];
              return (
                <div key={m} className="p-3 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium text-gray-800">
                      {MILESTONE_LABELS[m]}
                    </span>
                    {state && <MilestoneCountdown milestone={m} state={state} />}
                  </div>
                  <div className="text-xs text-gray-500 space-y-0.5">
                    {state?.due_at && <div>Échéance : {new Date(state.due_at).toLocaleString()}</div>}
                    {state?.submitted_at && <div>Soumis le {new Date(state.submitted_at).toLocaleString()}</div>}
                  </div>
                  {detail.status === 'confirmed' && (
                    <div className="flex items-center gap-1 flex-wrap">
                      <button
                        onClick={() => openMilestoneForm(m)}
                        className="px-2 py-1 text-xs text-gray-600 hover:bg-gray-100 rounded border"
                      >
                        Éditer le formulaire
                      </button>
                      <button
                        onClick={() => handleExport(m, 'json')}
                        className="flex items-center gap-1 px-2 py-1 text-xs text-gray-600 hover:bg-gray-100 rounded border"
                      >
                        <FileJson size={12} />
                        JSON
                      </button>
                      <button
                        onClick={() => handleExport(m, 'markdown')}
                        className="flex items-center gap-1 px-2 py-1 text-xs text-gray-600 hover:bg-gray-100 rounded border"
                      >
                        <FileText size={12} />
                        Markdown
                      </button>
                      {!state?.submitted_at && (
                        <button
                          onClick={() => handleSubmitMilestone(m)}
                          disabled={busy}
                          className="flex items-center gap-1 px-2 py-1 text-xs text-green-700 hover:bg-green-50 rounded border disabled:opacity-50"
                        >
                          <CheckCircle2 size={12} />
                          Marquer comme soumis
                        </button>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          {/* Formulaire de brouillon du jalon en cours d'édition */}
          {editingMilestone && (
            <div className="border rounded-md p-3 space-y-2">
              <h3 className="text-sm font-medium text-gray-800">
                Brouillon — {MILESTONE_LABELS[editingMilestone]}
              </h3>
              {draftLoading ? (
                <p className="text-sm text-gray-500 italic">Chargement…</p>
              ) : (
                <>
                  {Object.entries(draftFields).map(([key, value]) => (
                    <div key={key} className="flex items-center gap-2">
                      <label className="text-xs text-gray-500 w-32 shrink-0 truncate" title={key}>
                        {key}
                      </label>
                      <input
                        type="text"
                        value={value}
                        onChange={(e) =>
                          setDraftFields((prev) => ({ ...prev, [key]: e.target.value }))
                        }
                        className="flex-1 px-2 py-1 text-sm border rounded"
                      />
                    </div>
                  ))}
                  <div className="flex items-center gap-2 pt-1">
                    <button
                      onClick={handleSaveDraft}
                      disabled={busy}
                      className="px-3 py-1.5 text-sm bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
                    >
                      Enregistrer le brouillon
                    </button>
                    <button
                      onClick={() => setEditingMilestone(null)}
                      className="px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-100 rounded-md"
                    >
                      Annuler
                    </button>
                  </div>
                </>
              )}
            </div>
          )}

          {/* Contexte d'évaluation et assets touchés */}
          <div className="border rounded-md p-3 space-y-2">
            <h3 className="text-sm font-medium text-gray-800">Contexte</h3>
            <div className="text-xs text-gray-600 space-y-0.5">
              {contextEntries.map(([key, value]) => (
                <div key={key}>
                  <span className="text-gray-400">{key} :</span> {String(value)}
                </div>
              ))}
            </div>
            {detail.affected_assets.length > 0 && (
              <div className="text-xs text-gray-600">
                Assets touchés : {detail.affected_assets.map((a) => a.asset_id).join(', ')}
              </div>
            )}
          </div>
        </div>
      </div>
      <ConfirmDialog {...confirmDialogProps} />
    </div>
  );
}

export default EnisaEventDetail;
