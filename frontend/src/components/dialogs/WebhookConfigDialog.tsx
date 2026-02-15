import { useState, useEffect } from 'react';
import {
  X,
  Bell,
  Plus,
  Trash2,
  Play,
  Check,
  AlertCircle,
  Clock,
  ChevronDown,
  ChevronRight,
} from 'lucide-react';
import { webhooksApi } from '@/api';
import { useConfirm } from '@/hooks/useConfirm';
import { ConfirmDialog } from '@/components/ui/ConfirmDialog';
import type {
  Webhook,
  WebhookCreate,
  WebhookUpdate,
  WebhookLog,
  WebhookTestResult,
} from '@/types';
import { WEBHOOK_EVENTS } from '@/types';

interface WebhookConfigDialogProps {
  treeId: number;
  treeName: string;
  onClose: () => void;
}

type View = 'list' | 'form' | 'logs';

export function WebhookConfigDialog({ treeId, treeName, onClose }: WebhookConfigDialogProps) {
  const [view, setView] = useState<View>('list');
  const [webhooks, setWebhooks] = useState<Webhook[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editingWebhook, setEditingWebhook] = useState<Webhook | null>(null);
  const [logsWebhookId, setLogsWebhookId] = useState<number | null>(null);
  const { confirm, confirmDialogProps } = useConfirm();

  const loadWebhooks = async () => {
    setLoading(true);
    try {
      const data = await webhooksApi.list(treeId);
      setWebhooks(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erreur de chargement');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadWebhooks();
  }, [treeId]);

  const handleCreate = () => {
    setEditingWebhook(null);
    setView('form');
  };

  const handleEdit = (webhook: Webhook) => {
    setEditingWebhook(webhook);
    setView('form');
  };

  const handleShowLogs = (webhookId: number) => {
    setLogsWebhookId(webhookId);
    setView('logs');
  };

  const handleDelete = async (webhookId: number) => {
    const ok = await confirm('Supprimer le webhook', 'Supprimer ce webhook et tout son historique ?');
    if (!ok) return;
    try {
      await webhooksApi.delete(treeId, webhookId);
      await loadWebhooks();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erreur de suppression');
    }
  };

  const handleToggleActive = async (webhook: Webhook) => {
    try {
      await webhooksApi.update(treeId, webhook.id, { is_active: !webhook.is_active });
      await loadWebhooks();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erreur de mise à jour');
    }
  };

  const handleSaved = async () => {
    await loadWebhooks();
    setView('list');
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-2xl max-h-[80vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b">
          <div className="flex items-center gap-2">
            <Bell size={20} className="text-orange-600" />
            <h2 className="text-lg font-semibold">Webhooks sortants</h2>
            <span className="text-sm text-gray-500">- {treeName}</span>
          </div>
          <button onClick={onClose} className="p-1 hover:bg-gray-100 rounded-md">
            <X size={20} className="text-gray-500" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-4">
          {error && (
            <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-md text-red-700 text-sm flex items-center gap-2">
              <AlertCircle size={16} />
              {error}
              <button onClick={() => setError(null)} className="ml-auto">
                <X size={14} />
              </button>
            </div>
          )}

          {view === 'list' && (
            <WebhookList
              treeId={treeId}
              webhooks={webhooks}
              loading={loading}
              onCreate={handleCreate}
              onEdit={handleEdit}
              onDelete={handleDelete}
              onToggleActive={handleToggleActive}
              onShowLogs={handleShowLogs}
            />
          )}

          {view === 'form' && (
            <WebhookForm
              treeId={treeId}
              webhook={editingWebhook}
              onSaved={handleSaved}
              onCancel={() => setView('list')}
            />
          )}

          {view === 'logs' && logsWebhookId && (
            <WebhookLogs
              treeId={treeId}
              webhookId={logsWebhookId}
              onBack={() => setView('list')}
            />
          )}
        </div>
      </div>
      <ConfirmDialog {...confirmDialogProps} />
    </div>
  );
}

function WebhookList({
  treeId,
  webhooks,
  loading,
  onCreate,
  onEdit,
  onDelete,
  onToggleActive,
  onShowLogs,
}: {
  treeId: number;
  webhooks: Webhook[];
  loading: boolean;
  onCreate: () => void;
  onEdit: (w: Webhook) => void;
  onDelete: (id: number) => void;
  onToggleActive: (w: Webhook) => void;
  onShowLogs: (id: number) => void;
}) {
  const [testing, setTesting] = useState<number | null>(null);
  const [testResult, setTestResult] = useState<{ id: number; result: WebhookTestResult } | null>(null);

  const handleTest = async (webhookId: number) => {
    setTesting(webhookId);
    setTestResult(null);
    try {
      const result = await webhooksApi.test(treeId, webhookId);
      setTestResult({ id: webhookId, result });
    } catch {
      setTestResult({
        id: webhookId,
        result: { success: false, status_code: null, response_body: null, error_message: 'Erreur de test', duration_ms: null },
      });
    } finally {
      setTesting(null);
    }
  };

  if (loading) {
    return <div className="text-center text-gray-500 py-8">Chargement...</div>;
  }

  return (
    <div className="space-y-3">
      <div className="flex justify-end">
        <button
          onClick={onCreate}
          className="flex items-center gap-1 px-3 py-1.5 text-sm bg-blue-500 text-white rounded-md hover:bg-blue-600"
        >
          <Plus size={16} />
          Nouveau webhook
        </button>
      </div>

      {webhooks.length === 0 ? (
        <div className="text-center text-gray-500 py-8">
          <Bell size={32} className="mx-auto mb-2 opacity-50" />
          <p className="text-sm">Aucun webhook configuré</p>
        </div>
      ) : (
        webhooks.map((webhook) => (
          <div key={webhook.id} className="border rounded-lg p-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <button
                  onClick={() => onToggleActive(webhook)}
                  className={`w-2 h-2 rounded-full cursor-pointer ${webhook.is_active ? 'bg-green-500' : 'bg-gray-300'}`}
                  title={webhook.is_active ? 'Actif — cliquer pour désactiver' : 'Inactif — cliquer pour activer'}
                />
                <span className="font-medium text-sm">{webhook.name}</span>
                {webhook.has_secret && (
                  <span className="text-xs text-gray-400" title="Secret HMAC configuré">🔑</span>
                )}
              </div>
              <div className="flex items-center gap-1">
                <button
                  onClick={() => handleTest(webhook.id)}
                  disabled={testing === webhook.id}
                  className="p-1 hover:bg-gray-100 rounded text-sm"
                  title="Tester"
                >
                  <Play size={14} className="text-blue-500" />
                </button>
                <button
                  onClick={() => onShowLogs(webhook.id)}
                  className="p-1 hover:bg-gray-100 rounded text-sm"
                  title="Historique"
                >
                  <Clock size={14} className="text-gray-500" />
                </button>
                <button
                  onClick={() => onEdit(webhook)}
                  className="p-1 hover:bg-gray-100 rounded text-sm text-gray-500"
                >
                  Modifier
                </button>
                <button
                  onClick={() => onDelete(webhook.id)}
                  className="p-1 hover:bg-red-50 rounded"
                >
                  <Trash2 size={14} className="text-red-500" />
                </button>
              </div>
            </div>
            <div className="text-xs text-gray-500 mt-1 font-mono truncate">{webhook.url}</div>
            <div className="flex gap-1 mt-2 flex-wrap">
              {webhook.events.map((evt) => {
                const eventInfo = WEBHOOK_EVENTS.find((e) => e.value === evt);
                return (
                  <span
                    key={evt}
                    className="px-1.5 py-0.5 rounded text-xs text-white"
                    style={{ backgroundColor: eventInfo?.color || '#6b7280' }}
                  >
                    {eventInfo?.label || evt}
                  </span>
                );
              })}
            </div>

            {/* Test result */}
            {testResult?.id === webhook.id && (
              <div className={`mt-2 p-2 rounded text-xs ${testResult.result.success ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-700'}`}>
                {testResult.result.success ? (
                  <span className="flex items-center gap-1"><Check size={12} /> OK ({testResult.result.status_code}) - {testResult.result.duration_ms}ms</span>
                ) : (
                  <span className="flex items-center gap-1"><AlertCircle size={12} /> {testResult.result.error_message}</span>
                )}
              </div>
            )}
          </div>
        ))
      )}
    </div>
  );
}

function WebhookForm({
  treeId,
  webhook,
  onSaved,
  onCancel,
}: {
  treeId: number;
  webhook: Webhook | null;
  onSaved: () => void;
  onCancel: () => void;
}) {
  const [name, setName] = useState(webhook?.name || '');
  const [url, setUrl] = useState(webhook?.url || '');
  const [secret, setSecret] = useState('');
  const [events, setEvents] = useState<string[]>(webhook?.events || []);
  const [isActive, setIsActive] = useState(webhook?.is_active ?? true);
  const [headers, setHeaders] = useState<Array<{ key: string; value: string }>>(
    webhook?.headers
      ? Object.entries(webhook.headers).map(([key, value]) => ({ key, value }))
      : []
  );
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const toggleEvent = (event: string) => {
    setEvents((prev) =>
      prev.includes(event) ? prev.filter((e) => e !== event) : [...prev, event]
    );
  };

  const addHeader = () => {
    setHeaders([...headers, { key: '', value: '' }]);
  };

  const removeHeader = (index: number) => {
    setHeaders(headers.filter((_, i) => i !== index));
  };

  const updateHeader = (index: number, field: 'key' | 'value', val: string) => {
    const newHeaders = [...headers];
    newHeaders[index] = { ...newHeaders[index], [field]: val };
    setHeaders(newHeaders);
  };

  const handleSave = async () => {
    if (!name.trim() || !url.trim() || events.length === 0) {
      setError('Nom, URL et au moins un événement sont requis');
      return;
    }

    setSaving(true);
    setError(null);

    try {
      // Convertit les headers en Record
      const headersRecord: Record<string, string> = {};
      for (const h of headers) {
        if (h.key.trim()) {
          headersRecord[h.key.trim()] = h.value;
        }
      }

      if (webhook) {
        // Mode édition
        const data: WebhookUpdate = {
          name: name.trim(),
          url: url.trim(),
          events,
          is_active: isActive,
          headers: headersRecord,
        };
        // N'envoyer le secret que s'il a été modifié
        if (secret) {
          data.secret = secret;
        }
        await webhooksApi.update(treeId, webhook.id, data);
      } else {
        // Mode création
        const data: WebhookCreate = {
          name: name.trim(),
          url: url.trim(),
          secret: secret.trim() || undefined,
          events,
          is_active: isActive,
          headers: headersRecord,
        };
        await webhooksApi.create(treeId, data);
      }
      onSaved();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erreur de sauvegarde');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-4">
      <h3 className="font-medium">
        {webhook ? 'Modifier le webhook' : 'Nouveau webhook'}
      </h3>

      {error && (
        <div className="p-2 bg-red-50 text-red-600 text-sm rounded">{error}</div>
      )}

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Nom</label>
        <input
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          className="w-full px-3 py-2 border rounded-md text-sm"
          placeholder="Ex: Notification SIEM"
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">URL</label>
        <input
          type="url"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          className="w-full px-3 py-2 border rounded-md text-sm font-mono"
          placeholder="https://example.com/webhook"
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Secret (HMAC-SHA256)
        </label>
        <input
          type="password"
          value={secret}
          onChange={(e) => setSecret(e.target.value)}
          className="w-full px-3 py-2 border rounded-md text-sm font-mono"
          placeholder={webhook?.has_secret ? 'Secret configuré — laisser vide pour conserver' : 'Optionnel — pour signer les requêtes'}
        />
        {webhook?.has_secret && !secret && (
          <p className="text-xs text-gray-400 mt-1">Un secret est déjà configuré. Saisissez une nouvelle valeur pour le remplacer.</p>
        )}
      </div>

      {/* Headers custom */}
      <div>
        <div className="flex items-center justify-between mb-2">
          <label className="block text-sm font-medium text-gray-700">
            Headers HTTP
          </label>
          <button
            onClick={addHeader}
            className="text-xs text-blue-600 hover:underline"
          >
            + Ajouter
          </button>
        </div>
        {headers.length === 0 ? (
          <p className="text-xs text-gray-400">Aucun header custom</p>
        ) : (
          <div className="space-y-2">
            {headers.map((h, i) => (
              <div key={i} className="flex gap-2 items-center">
                <input
                  type="text"
                  value={h.key}
                  onChange={(e) => updateHeader(i, 'key', e.target.value)}
                  className="flex-1 px-2 py-1 border rounded text-sm font-mono"
                  placeholder="Header-Name"
                />
                <input
                  type="text"
                  value={h.value}
                  onChange={(e) => updateHeader(i, 'value', e.target.value)}
                  className="flex-1 px-2 py-1 border rounded text-sm font-mono"
                  placeholder="Valeur"
                />
                <button
                  onClick={() => removeHeader(i)}
                  className="p-1 hover:bg-red-50 rounded"
                >
                  <X size={14} className="text-red-400" />
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Événements déclencheurs
        </label>
        <div className="flex flex-wrap gap-2">
          {WEBHOOK_EVENTS.map((evt) => (
            <button
              key={evt.value}
              onClick={() => toggleEvent(evt.value)}
              className={`px-3 py-1.5 rounded-md text-sm border transition-colors ${
                events.includes(evt.value)
                  ? 'text-white border-transparent'
                  : 'text-gray-600 border-gray-300 hover:border-gray-400'
              }`}
              style={
                events.includes(evt.value)
                  ? { backgroundColor: evt.color }
                  : undefined
              }
            >
              {evt.label}
            </button>
          ))}
        </div>
      </div>

      <div className="flex items-center gap-2">
        <button
          onClick={() => setIsActive(!isActive)}
          className={`relative w-10 h-5 rounded-full transition-colors ${
            isActive ? 'bg-green-500' : 'bg-gray-300'
          }`}
        >
          <span
            className={`absolute top-0.5 w-4 h-4 bg-white rounded-full transition-transform ${
              isActive ? 'left-5' : 'left-0.5'
            }`}
          />
        </button>
        <span className="text-sm text-gray-700">Actif</span>
      </div>

      <div className="flex justify-end gap-2 pt-2">
        <button
          onClick={onCancel}
          className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-md text-sm"
        >
          Annuler
        </button>
        <button
          onClick={handleSave}
          disabled={saving}
          className="px-4 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600 text-sm disabled:opacity-50"
        >
          {saving ? 'Sauvegarde...' : 'Sauvegarder'}
        </button>
      </div>
    </div>
  );
}

function WebhookLogs({ treeId, webhookId, onBack }: { treeId: number; webhookId: number; onBack: () => void }) {
  const [logs, setLogs] = useState<WebhookLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [expandedLog, setExpandedLog] = useState<number | null>(null);

  useEffect(() => {
    const loadLogs = async () => {
      try {
        const data = await webhooksApi.getLogs(treeId, webhookId);
        setLogs(data);
      } catch {
        // silently fail
      } finally {
        setLoading(false);
      }
    };
    loadLogs();
  }, [treeId, webhookId]);

  if (loading) {
    return <div className="text-center text-gray-500 py-8">Chargement...</div>;
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        <button onClick={onBack} className="text-sm text-blue-600 hover:underline">
          Retour
        </button>
        <span className="text-sm text-gray-500">Historique des envois</span>
      </div>

      {logs.length === 0 ? (
        <div className="text-center text-gray-500 py-8 text-sm">Aucun envoi</div>
      ) : (
        logs.map((log) => (
          <div key={log.id} className="border rounded-lg text-sm">
            <div
              className="flex items-center justify-between p-3 cursor-pointer hover:bg-gray-50"
              onClick={() => setExpandedLog(expandedLog === log.id ? null : log.id)}
            >
              <div className="flex items-center gap-2">
                {expandedLog === log.id ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                <span className={`w-2 h-2 rounded-full ${log.success ? 'bg-green-500' : 'bg-red-500'}`} />
                <span className="font-medium">{log.event}</span>
                {log.status_code && (
                  <span className="text-gray-500">HTTP {log.status_code}</span>
                )}
                {log.duration_ms && (
                  <span className="text-gray-400">{log.duration_ms}ms</span>
                )}
              </div>
              <span className="text-xs text-gray-400">
                {new Date(log.created_at).toLocaleString()}
              </span>
            </div>

            {expandedLog === log.id && (
              <div className="border-t p-3 bg-gray-50 space-y-2">
                {log.error_message && (
                  <div className="text-red-600 text-xs">{log.error_message}</div>
                )}
                <div>
                  <div className="text-xs font-medium text-gray-500 mb-1">Payload</div>
                  <pre className="text-xs bg-white p-2 rounded border overflow-x-auto max-h-32">
                    {JSON.stringify(log.request_body, null, 2)}
                  </pre>
                </div>
                {log.response_body && (
                  <div>
                    <div className="text-xs font-medium text-gray-500 mb-1">Réponse</div>
                    <pre className="text-xs bg-white p-2 rounded border overflow-x-auto max-h-32">
                      {log.response_body}
                    </pre>
                  </div>
                )}
              </div>
            )}
          </div>
        ))
      )}
    </div>
  );
}

export default WebhookConfigDialog;
