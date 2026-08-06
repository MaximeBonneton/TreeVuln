import { useCallback, useEffect, useState } from 'react';
import { Eye, EyeOff, History, Pencil, Plus, RefreshCw, Satellite, Trash2 } from 'lucide-react';
import { ingestApi } from '@/api/ingest';
import { useConfirm } from '@/hooks/useConfirm';
import { Alert, Badge, Button, Card, ConfirmDialog, CopyButton, Drawer, EmptyState } from '@/components/ui';
import { IngestForm } from './IngestForm';
import type { IngestEndpoint, IngestEndpointCreate, IngestLog } from '@/types/ingest';

/** Bloc « Ingestion entrante » : endpoints à clé API (révélée une seule fois), logs ; édition en drawer (spec §3). */
export function IngestSection({ treeId }: { treeId: number }) {
  const [endpoints, setEndpoints] = useState<IngestEndpoint[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [drawer, setDrawer] = useState<{ open: boolean; endpoint: IngestEndpoint | null }>({ open: false, endpoint: null });
  // Clés en clair retournées à la création/régénération — visibles une seule fois, non persistées
  const [revealedKeys, setRevealedKeys] = useState<Record<number, string>>({});
  const [shownKeys, setShownKeys] = useState<Record<number, boolean>>({});
  const [openLogs, setOpenLogs] = useState<Record<number, IngestLog[] | 'loading'>>({});
  const { confirm, confirmDialogProps } = useConfirm();

  const reload = useCallback(async () => {
    try {
      setEndpoints(await ingestApi.list(treeId));
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Impossible de charger les endpoints.');
    } finally {
      setLoading(false);
    }
  }, [treeId]);

  useEffect(() => {
    void reload();
  }, [reload]);

  const handleSubmit = async (data: IngestEndpointCreate) => {
    try {
      if (drawer.endpoint) {
        await ingestApi.update(drawer.endpoint.id, data);
      } else {
        const created = await ingestApi.create(treeId, data);
        setRevealedKeys((prev) => ({ ...prev, [created.id]: created.api_key }));
      }
      setDrawer({ open: false, endpoint: null });
      await reload();
    } catch (e) {
      // Filet de sécurité : si le drawer a été fermé pendant la sauvegarde, IngestForm
      // est démonté et son propre setError devient un no-op — l'Alert de section reste
      // le seul retour visible. On re-throw pour que le form encore monté (cas normal)
      // affiche aussi son erreur inline.
      setError(e instanceof Error ? e.message : "Échec de la sauvegarde de l'endpoint.");
      throw e;
    }
  };

  const handleRegenerate = async (endpoint: IngestEndpoint) => {
    const ok = await confirm(
      'Régénérer la clé API ?',
      `L'ancienne clé de « ${endpoint.name} » cessera immédiatement de fonctionner.`,
      'warning'
    );
    if (!ok) return;
    try {
      const updated = await ingestApi.regenerateKey(endpoint.id);
      setRevealedKeys((prev) => ({ ...prev, [endpoint.id]: updated.api_key }));
      setShownKeys((prev) => ({ ...prev, [endpoint.id]: false }));
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Échec de la régénération de la clé.');
    }
  };

  const handleDelete = async (endpoint: IngestEndpoint) => {
    const ok = await confirm(
      'Supprimer cet endpoint ?',
      `« ${endpoint.name} » et son historique d'ingestion seront supprimés.`
    );
    if (!ok) return;
    try {
      await ingestApi.delete(endpoint.id);
      await reload();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Échec de la suppression.');
    }
  };

  const toggleLogs = async (endpoint: IngestEndpoint) => {
    if (openLogs[endpoint.id]) {
      setOpenLogs((prev) => {
        const next = { ...prev };
        delete next[endpoint.id];
        return next;
      });
      return;
    }
    setOpenLogs((prev) => ({ ...prev, [endpoint.id]: 'loading' }));
    try {
      const logs = await ingestApi.getLogs(endpoint.id);
      setOpenLogs((prev) => ({ ...prev, [endpoint.id]: logs }));
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Impossible de charger les logs.');
      setOpenLogs((prev) => {
        const next = { ...prev };
        delete next[endpoint.id];
        return next;
      });
    }
  };

  const ingestUrl = (slug: string) => `${window.location.origin}/api/v1/ingest/${slug}`;

  return (
    <section aria-label="Ingestion entrante">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-base font-semibold tracking-tight text-slate-900">Ingestion entrante</h2>
        {endpoints.length > 0 && (
          <Button variant="secondary" size="sm" onClick={() => setDrawer({ open: true, endpoint: null })}>
            <Plus size={14} aria-hidden="true" /> Nouvel endpoint
          </Button>
        )}
      </div>

      {error && <div className="mb-3"><Alert variant="error">{error}</Alert></div>}

      {loading ? (
        <p className="text-sm text-slate-500">Chargement…</p>
      ) : endpoints.length === 0 ? (
        <Card>
          <EmptyState
            icon={Satellite}
            title="Aucun endpoint d'ingestion"
            description="Recevez des vulnérabilités en temps réel depuis vos scanners, avec clé API dédiée."
            action={
              <Button onClick={() => setDrawer({ open: true, endpoint: null })}>
                Créer le premier endpoint
              </Button>
            }
          />
        </Card>
      ) : (
        <div className="space-y-3">
          {endpoints.map((endpoint) => {
            const revealed = revealedKeys[endpoint.id];
            const shown = shownKeys[endpoint.id];
            const logs = openLogs[endpoint.id];
            return (
              <Card key={endpoint.id}>
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <p className="font-medium text-slate-900">{endpoint.name}</p>
                      {endpoint.auto_evaluate && <Badge variant="indigo">auto-éval</Badge>}
                      {!endpoint.is_active && <Badge variant="neutral">inactif</Badge>}
                    </div>
                    <p className="mt-0.5 flex items-center gap-1 font-mono text-xs text-slate-500">
                      <span className="truncate">POST {ingestUrl(endpoint.slug)}</span>
                      <CopyButton value={ingestUrl(endpoint.slug)} label={`Copier l'URL de ${endpoint.name}`} />
                    </p>

                    <div className="mt-1.5 flex items-center gap-1 text-xs text-slate-600">
                      <span className="font-medium">Clé API :</span>
                      {revealed ? (
                        <>
                          <code className="font-mono">{shown ? revealed : '••••••••'}</code>
                          <button
                            type="button"
                            aria-label={shown ? 'Masquer la clé' : 'Révéler la clé'}
                            onClick={() => setShownKeys((prev) => ({ ...prev, [endpoint.id]: !shown }))}
                            className="rounded-md p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-600"
                          >
                            {shown ? <EyeOff size={13} /> : <Eye size={13} />}
                          </button>
                          <CopyButton value={revealed} label={`Copier la clé de ${endpoint.name}`} />
                        </>
                      ) : (
                        <span className="text-slate-500">
                          {endpoint.has_api_key ? 'Clé chiffrée — copiez-la à la création' : 'Non configurée'}
                        </span>
                      )}
                    </div>
                    <p className="mt-1 text-xs text-slate-500">
                      Authentification : en-tête <code className="font-mono">X-API-Key</code>
                    </p>

                    {Object.keys(endpoint.field_mapping).length > 0 && (
                      <div className="mt-1.5 flex flex-wrap gap-1">
                        {Object.entries(endpoint.field_mapping).map(([src, dst]) => (
                          <span key={src} className="rounded bg-slate-100 px-1.5 py-0.5 font-mono text-[10px] text-slate-600">
                            {src} → {dst}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>

                  <div className="flex shrink-0 items-center gap-1">
                    <button type="button" aria-label={`Régénérer la clé de ${endpoint.name}`} title="Régénérer la clé"
                      onClick={() => handleRegenerate(endpoint)}
                      className="rounded-md p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-600">
                      <RefreshCw size={14} />
                    </button>
                    <button type="button" aria-label={`Historique de ${endpoint.name}`} title="Historique" onClick={() => toggleLogs(endpoint)}
                      className="rounded-md p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-600">
                      <History size={14} />
                    </button>
                    <button type="button" aria-label={`Modifier ${endpoint.name}`} title="Modifier"
                      onClick={() => setDrawer({ open: true, endpoint })}
                      className="rounded-md p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-600">
                      <Pencil size={14} />
                    </button>
                    <button type="button" aria-label={`Supprimer ${endpoint.name}`} title="Supprimer" onClick={() => handleDelete(endpoint)}
                      className="rounded-md p-1.5 text-slate-400 hover:bg-red-50 hover:text-red-600">
                      <Trash2 size={14} />
                    </button>
                  </div>
                </div>

                {logs && (
                  <div className="mt-3 border-t border-slate-200 pt-3">
                    {logs === 'loading' ? (
                      <p className="text-sm text-slate-500">Chargement des logs…</p>
                    ) : logs.length === 0 ? (
                      <p className="text-sm text-slate-500">Aucune ingestion pour l'instant.</p>
                    ) : (
                      <ul className="space-y-1">
                        {logs.map((entry) => (
                          <li key={entry.id} className="flex items-center gap-2 text-xs text-slate-600">
                            <span className={`h-1.5 w-1.5 shrink-0 rounded-full ${entry.error_count === 0 ? 'bg-emerald-500' : 'bg-amber-500'}`} />
                            <span>{entry.vuln_count} vulnérabilité{entry.vuln_count > 1 ? 's' : ''}</span>
                            <span>({entry.success_count} ok, {entry.error_count} err)</span>
                            {entry.duration_ms != null && <span>{entry.duration_ms} ms</span>}
                            {entry.source_ip && <span className="font-mono">{entry.source_ip}</span>}
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
        onClose={() => setDrawer({ open: false, endpoint: null })}
        title={drawer.endpoint ? `Modifier ${drawer.endpoint.name}` : 'Nouvel endpoint'}
      >
        <IngestForm
          key={drawer.endpoint?.id ?? 'new'}
          endpoint={drawer.endpoint}
          onSubmit={handleSubmit}
          onCancel={() => setDrawer({ open: false, endpoint: null })}
        />
      </Drawer>

      <ConfirmDialog {...confirmDialogProps} />
    </section>
  );
}
