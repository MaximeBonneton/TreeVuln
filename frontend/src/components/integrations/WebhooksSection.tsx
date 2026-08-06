import { useCallback, useEffect, useState } from 'react';
import { History, Play, Pencil, Plus, Trash2, Webhook as WebhookIcon } from 'lucide-react';
import { webhooksApi } from '@/api/webhooks';
import { useConfirm } from '@/hooks/useConfirm';
import { Alert, Badge, Button, Card, ConfirmDialog, Drawer, EmptyState, Switch } from '@/components/ui';
import { WebhookForm } from './WebhookForm';
import { WEBHOOK_EVENTS, type Webhook, type WebhookCreate, type WebhookLog, type WebhookTestResult } from '@/types/webhook';

const EVENT_COLORS = Object.fromEntries(WEBHOOK_EVENTS.map((e) => [e.value, e.color]));

/** Bloc « Webhooks sortants » : cards avec statut, test, logs dépliables ; édition en drawer (spec §3). */
export function WebhooksSection({ treeId }: { treeId: number }) {
  const [webhooks, setWebhooks] = useState<Webhook[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [drawer, setDrawer] = useState<{ open: boolean; webhook: Webhook | null }>({ open: false, webhook: null });
  const [testResults, setTestResults] = useState<Record<number, WebhookTestResult>>({});
  const [openLogs, setOpenLogs] = useState<Record<number, WebhookLog[] | 'loading'>>({});
  const { confirm, confirmDialogProps } = useConfirm();

  const reload = useCallback(async () => {
    try {
      setWebhooks(await webhooksApi.list(treeId));
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Impossible de charger les webhooks.');
    } finally {
      setLoading(false);
    }
  }, [treeId]);

  useEffect(() => {
    void reload();
  }, [reload]);

  const handleSubmit = async (data: WebhookCreate) => {
    if (drawer.webhook) await webhooksApi.update(treeId, drawer.webhook.id, data);
    else await webhooksApi.create(treeId, data);
    setDrawer({ open: false, webhook: null });
    await reload();
  };

  const handleToggle = async (webhook: Webhook) => {
    try {
      await webhooksApi.update(treeId, webhook.id, { is_active: !webhook.is_active });
      await reload();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Échec du changement de statut.');
    }
  };

  const handleTest = async (webhook: Webhook) => {
    try {
      const result = await webhooksApi.test(treeId, webhook.id);
      setTestResults((prev) => ({ ...prev, [webhook.id]: result }));
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Échec du test du webhook.');
    }
  };

  const toggleLogs = async (webhook: Webhook) => {
    if (openLogs[webhook.id]) {
      setOpenLogs((prev) => {
        const next = { ...prev };
        delete next[webhook.id];
        return next;
      });
      return;
    }
    setOpenLogs((prev) => ({ ...prev, [webhook.id]: 'loading' }));
    try {
      const logs = await webhooksApi.getLogs(treeId, webhook.id);
      setOpenLogs((prev) => ({ ...prev, [webhook.id]: logs }));
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Impossible de charger les logs.');
      setOpenLogs((prev) => {
        const next = { ...prev };
        delete next[webhook.id];
        return next;
      });
    }
  };

  const handleDelete = async (webhook: Webhook) => {
    const ok = await confirm(
      'Supprimer ce webhook ?',
      `« ${webhook.name} » et tout son historique seront supprimés.`
    );
    if (!ok) return;
    try {
      await webhooksApi.delete(treeId, webhook.id);
      await reload();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Échec de la suppression.');
    }
  };

  return (
    <section aria-label="Webhooks sortants">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-base font-semibold tracking-tight text-slate-900">Webhooks sortants</h2>
        {webhooks.length > 0 && (
          <Button variant="secondary" size="sm" onClick={() => setDrawer({ open: true, webhook: null })}>
            <Plus size={14} aria-hidden="true" /> Nouveau webhook
          </Button>
        )}
      </div>

      {error && <div className="mb-3"><Alert variant="error">{error}</Alert></div>}

      {loading ? (
        <p className="text-sm text-slate-500">Chargement…</p>
      ) : webhooks.length === 0 ? (
        <Card>
          <EmptyState
            icon={WebhookIcon}
            title="Aucun webhook configuré"
            description="Notifiez votre ticketing ou votre SIEM à chaque décision."
            action={
              <Button onClick={() => setDrawer({ open: true, webhook: null })}>
                Créer le premier webhook
              </Button>
            }
          />
        </Card>
      ) : (
        <div className="space-y-3">
          {webhooks.map((webhook) => {
            const logs = openLogs[webhook.id];
            const test = testResults[webhook.id];
            return (
              <Card key={webhook.id}>
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <p className="font-medium text-slate-900">{webhook.name}</p>
                      {webhook.has_secret && <Badge variant="indigo">secret configuré</Badge>}
                      {!webhook.is_active && <Badge variant="neutral">inactif</Badge>}
                    </div>
                    <p className="mt-0.5 truncate font-mono text-xs text-slate-500">{webhook.url}</p>
                    <div className="mt-1.5 flex flex-wrap gap-1">
                      {webhook.events.map((ev) => (
                        <span
                          key={ev}
                          className="rounded-full px-2 py-0.5 text-[10px] font-medium text-white"
                          style={{ backgroundColor: EVENT_COLORS[ev] ?? '#64748b' }}
                        >
                          {ev}
                        </span>
                      ))}
                    </div>
                  </div>
                  <div className="flex shrink-0 items-center gap-1">
                    <Switch checked={webhook.is_active} onChange={() => handleToggle(webhook)} label="Webhook actif" />
                    <button type="button" aria-label={`Tester ${webhook.name}`} title="Tester" onClick={() => handleTest(webhook)}
                      className="rounded-md p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-600">
                      <Play size={14} />
                    </button>
                    <button type="button" aria-label={`Historique de ${webhook.name}`} title="Historique" onClick={() => toggleLogs(webhook)}
                      className="rounded-md p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-600">
                      <History size={14} />
                    </button>
                    <button type="button" aria-label={`Modifier ${webhook.name}`} title="Modifier"
                      onClick={() => setDrawer({ open: true, webhook })}
                      className="rounded-md p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-600">
                      <Pencil size={14} />
                    </button>
                    <button type="button" aria-label={`Supprimer ${webhook.name}`} title="Supprimer" onClick={() => handleDelete(webhook)}
                      className="rounded-md p-1.5 text-slate-400 hover:bg-red-50 hover:text-red-600">
                      <Trash2 size={14} />
                    </button>
                  </div>
                </div>

                {test && (
                  <div className="mt-3">
                    <Alert variant={test.success ? 'success' : 'error'}>
                      Test : {test.success ? 'succès' : 'échec'} — statut {test.status_code ?? '—'}
                      {test.duration_ms != null && `, ${test.duration_ms} ms`}
                      {test.error_message && ` — ${test.error_message}`}
                    </Alert>
                  </div>
                )}

                {logs && (
                  <div className="mt-3 border-t border-slate-200 pt-3">
                    {logs === 'loading' ? (
                      <p className="text-sm text-slate-500">Chargement des logs…</p>
                    ) : logs.length === 0 ? (
                      <p className="text-sm text-slate-500">Aucun envoi pour l'instant.</p>
                    ) : (
                      <ul className="space-y-1">
                        {logs.map((entry) => (
                          <li key={entry.id} className="flex items-center gap-2 text-xs text-slate-600">
                            <span className={`h-1.5 w-1.5 shrink-0 rounded-full ${entry.success ? 'bg-emerald-500' : 'bg-red-500'}`} />
                            <span data-testid="log-event" className="font-medium">{entry.event}</span>
                            <span>{entry.status_code ?? '—'}</span>
                            {entry.duration_ms != null && <span>{entry.duration_ms} ms</span>}
                            <span className="ml-auto text-slate-400">{new Date(entry.created_at).toLocaleString()}</span>
                          </li>
                        ))}
                      </ul>
                    )}
                  </div>
                )}
              </Card>
            );
          })}
        </div>
      )}

      <Drawer
        open={drawer.open}
        onClose={() => setDrawer({ open: false, webhook: null })}
        title={drawer.webhook ? `Modifier ${drawer.webhook.name}` : 'Nouveau webhook'}
      >
        <WebhookForm
          key={drawer.webhook?.id ?? 'new'}
          webhook={drawer.webhook}
          onSubmit={handleSubmit}
          onCancel={() => setDrawer({ open: false, webhook: null })}
        />
      </Drawer>

      <ConfirmDialog {...confirmDialogProps} />
    </section>
  );
}
