import { useState, useEffect } from 'react';
import {
  X,
  Download,
  Plus,
  Trash2,
  Copy,
  Check,
  AlertCircle,
  RefreshCw,
  Clock,
  Eye,
  EyeOff,
} from 'lucide-react';
import { ingestApi } from '@/api';
import type { IngestEndpoint, IngestEndpointCreate, IngestEndpointWithKey, IngestLog } from '@/types';

interface IngestConfigDialogProps {
  treeId: number;
  treeName: string;
  onClose: () => void;
}

type View = 'list' | 'form' | 'logs';

export function IngestConfigDialog({ treeId, treeName, onClose }: IngestConfigDialogProps) {
  const [view, setView] = useState<View>('list');
  const [endpoints, setEndpoints] = useState<IngestEndpoint[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editingEndpoint, setEditingEndpoint] = useState<IngestEndpoint | null>(null);
  const [logsEndpointId, setLogsEndpointId] = useState<number | null>(null);
  // Plain-text keys returned during creation/regeneration (visible only once)
  const [revealedKeys, setRevealedKeys] = useState<Record<number, string>>({});

  const loadEndpoints = async () => {
    setLoading(true);
    try {
      const data = await ingestApi.list(treeId);
      setEndpoints(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Loading error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadEndpoints();
  }, [treeId]);

  const handleCreate = () => {
    setEditingEndpoint(null);
    setView('form');
  };

  const handleEdit = (ep: IngestEndpoint) => {
    setEditingEndpoint(ep);
    setView('form');
  };

  const handleShowLogs = (endpointId: number) => {
    setLogsEndpointId(endpointId);
    setView('logs');
  };

  const handleDelete = async (endpointId: number) => {
    if (!window.confirm('Delete this endpoint?')) return;
    try {
      await ingestApi.delete(endpointId);
      await loadEndpoints();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Delete error');
    }
  };

  const handleRegenerateKey = async (endpointId: number) => {
    if (!window.confirm('Regenerate API key? The old one will be invalidated.')) return;
    try {
      const result = await ingestApi.regenerateKey(endpointId);
      setRevealedKeys((prev) => ({ ...prev, [result.id]: result.api_key }));
      await loadEndpoints();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error');
    }
  };

  const handleSaved = async (created?: IngestEndpointWithKey) => {
    if (created) {
      setRevealedKeys((prev) => ({ ...prev, [created.id]: created.api_key }));
    }
    await loadEndpoints();
    setView('list');
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-2xl max-h-[80vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b">
          <div className="flex items-center gap-2">
            <Download size={20} className="text-green-600" />
            <h2 className="text-lg font-semibold">Incoming webhooks</h2>
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
            <EndpointList
              endpoints={endpoints}
              loading={loading}
              revealedKeys={revealedKeys}
              onCreate={handleCreate}
              onEdit={handleEdit}
              onDelete={handleDelete}
              onRegenerateKey={handleRegenerateKey}
              onShowLogs={handleShowLogs}
            />
          )}

          {view === 'form' && (
            <EndpointForm
              treeId={treeId}
              endpoint={editingEndpoint}
              onSaved={handleSaved}
              onCancel={() => setView('list')}
            />
          )}

          {view === 'logs' && logsEndpointId && (
            <EndpointLogs
              endpointId={logsEndpointId}
              onBack={() => setView('list')}
            />
          )}
        </div>
      </div>
    </div>
  );
}

function EndpointList({
  endpoints,
  loading,
  revealedKeys,
  onCreate,
  onEdit,
  onDelete,
  onRegenerateKey,
  onShowLogs,
}: {
  endpoints: IngestEndpoint[];
  loading: boolean;
  revealedKeys: Record<number, string>;
  onCreate: () => void;
  onEdit: (ep: IngestEndpoint) => void;
  onDelete: (id: number) => void;
  onRegenerateKey: (id: number) => void;
  onShowLogs: (id: number) => void;
}) {
  const [showKey, setShowKey] = useState<number | null>(null);
  const [copied, setCopied] = useState<number | null>(null);

  const handleCopyKey = (epId: number) => {
    const key = revealedKeys[epId];
    if (!key) return;
    navigator.clipboard.writeText(key);
    setCopied(epId);
    setTimeout(() => setCopied(null), 2000);
  };

  if (loading) {
    return <div className="text-center text-gray-500 py-8">Loading...</div>;
  }

  return (
    <div className="space-y-3">
      <div className="flex justify-end">
        <button
          onClick={onCreate}
          className="flex items-center gap-1 px-3 py-1.5 text-sm bg-green-500 text-white rounded-md hover:bg-green-600"
        >
          <Plus size={16} />
          New endpoint
        </button>
      </div>

      {endpoints.length === 0 ? (
        <div className="text-center text-gray-500 py-8">
          <Download size={32} className="mx-auto mb-2 opacity-50" />
          <p className="text-sm">No ingestion endpoint configured</p>
        </div>
      ) : (
        endpoints.map((ep) => (
          <div key={ep.id} className="border rounded-lg p-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className={`w-2 h-2 rounded-full ${ep.is_active ? 'bg-green-500' : 'bg-gray-300'}`} />
                <span className="font-medium text-sm">{ep.name}</span>
                {ep.auto_evaluate && (
                  <span className="text-xs bg-blue-100 text-blue-700 px-1.5 py-0.5 rounded">auto-eval</span>
                )}
              </div>
              <div className="flex items-center gap-1">
                <button
                  onClick={() => onShowLogs(ep.id)}
                  className="p-1 hover:bg-gray-100 rounded"
                  title="History"
                >
                  <Clock size={14} className="text-gray-500" />
                </button>
                <button
                  onClick={() => onEdit(ep)}
                  className="p-1 hover:bg-gray-100 rounded text-sm text-gray-500"
                >
                  Edit
                </button>
                <button
                  onClick={() => onDelete(ep.id)}
                  className="p-1 hover:bg-red-50 rounded"
                >
                  <Trash2 size={14} className="text-red-500" />
                </button>
              </div>
            </div>

            {/* URL */}
            <div className="text-xs text-gray-500 mt-1 font-mono">
              POST /api/v1/ingest/{ep.slug}
            </div>

            {/* API Key */}
            <div className="flex items-center gap-2 mt-2">
              <span className="text-xs text-gray-500">API Key:</span>
              {revealedKeys[ep.id] ? (
                <>
                  <code className="text-xs bg-gray-100 px-2 py-0.5 rounded font-mono flex-1 truncate">
                    {showKey === ep.id ? revealedKeys[ep.id] : '••••••••••••••••'}
                  </code>
                  <button
                    onClick={() => setShowKey(showKey === ep.id ? null : ep.id)}
                    className="p-1 hover:bg-gray-100 rounded"
                    title={showKey === ep.id ? 'Hide' : 'Show'}
                  >
                    {showKey === ep.id ? <EyeOff size={12} /> : <Eye size={12} />}
                  </button>
                  <button
                    onClick={() => handleCopyKey(ep.id)}
                    className="p-1 hover:bg-gray-100 rounded"
                    title="Copy"
                  >
                    {copied === ep.id ? <Check size={12} className="text-green-500" /> : <Copy size={12} />}
                  </button>
                </>
              ) : (
                <span className="text-xs text-gray-400 italic flex-1">
                  {ep.has_api_key ? 'Encrypted (copy it during creation)' : 'Not configured'}
                </span>
              )}
              <button
                onClick={() => onRegenerateKey(ep.id)}
                className="p-1 hover:bg-gray-100 rounded"
                title="Regenerate"
              >
                <RefreshCw size={12} />
              </button>
            </div>

            {/* Field mapping */}
            {Object.keys(ep.field_mapping).length > 0 && (
              <div className="mt-2 flex flex-wrap gap-1">
                {Object.entries(ep.field_mapping).map(([src, dst]) => (
                  <span key={src} className="text-xs bg-gray-100 px-1.5 py-0.5 rounded">
                    {src} → {dst}
                  </span>
                ))}
              </div>
            )}
          </div>
        ))
      )}
    </div>
  );
}

function EndpointForm({
  treeId,
  endpoint,
  onSaved,
  onCancel,
}: {
  treeId: number;
  endpoint: IngestEndpoint | null;
  onSaved: (created?: IngestEndpointWithKey) => void;
  onCancel: () => void;
}) {
  const [name, setName] = useState(endpoint?.name || '');
  const [slug, setSlug] = useState(endpoint?.slug || '');
  const [isActive, setIsActive] = useState(endpoint?.is_active ?? true);
  const [autoEval, setAutoEval] = useState(endpoint?.auto_evaluate ?? true);
  const [mappings, setMappings] = useState<[string, string][]>(
    endpoint ? Object.entries(endpoint.field_mapping) : []
  );
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const addMapping = () => setMappings([...mappings, ['', '']]);
  const removeMapping = (idx: number) => setMappings(mappings.filter((_, i) => i !== idx));
  const updateMapping = (idx: number, pos: 0 | 1, value: string) => {
    const updated = [...mappings];
    updated[idx] = [...updated[idx]] as [string, string];
    updated[idx][pos] = value;
    setMappings(updated);
  };

  const handleSave = async () => {
    if (!name.trim() || !slug.trim()) {
      setError('Name and slug are required');
      return;
    }

    setSaving(true);
    setError(null);

    try {
      const fieldMapping: Record<string, string> = {};
      for (const [src, dst] of mappings) {
        if (src.trim() && dst.trim()) {
          fieldMapping[src.trim()] = dst.trim();
        }
      }

      const data: IngestEndpointCreate = {
        name: name.trim(),
        slug: slug.trim(),
        field_mapping: fieldMapping,
        is_active: isActive,
        auto_evaluate: autoEval,
      };

      if (endpoint) {
        await ingestApi.update(endpoint.id, data);
        onSaved();
      } else {
        const created = await ingestApi.create(treeId, data);
        onSaved(created);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Save error');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-4">
      <h3 className="font-medium">
        {endpoint ? 'Edit endpoint' : 'New ingestion endpoint'}
      </h3>

      {error && (
        <div className="p-2 bg-red-50 text-red-600 text-sm rounded">{error}</div>
      )}

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Name</label>
        <input
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          className="w-full px-3 py-2 border rounded-md text-sm"
          placeholder="E.g.: Nessus Scanner"
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Slug (URL)</label>
        <div className="flex items-center gap-2">
          <span className="text-xs text-gray-500 font-mono">/api/v1/ingest/</span>
          <input
            type="text"
            value={slug}
            onChange={(e) => setSlug(e.target.value.toLowerCase().replace(/[^a-z0-9-]/g, ''))}
            className="flex-1 px-3 py-2 border rounded-md text-sm font-mono"
            placeholder="nessus"
          />
        </div>
      </div>

      {/* Field mapping */}
      <div>
        <div className="flex items-center justify-between mb-2">
          <label className="text-sm font-medium text-gray-700">Field mapping</label>
          <button
            onClick={addMapping}
            className="text-xs text-blue-600 hover:underline flex items-center gap-1"
          >
            <Plus size={12} />
            Add
          </button>
        </div>
        <p className="text-xs text-gray-500 mb-2">
          Transforms field names from source to TreeVuln
        </p>
        {mappings.length === 0 ? (
          <p className="text-xs text-gray-400 italic">No mapping (fields passed as-is)</p>
        ) : (
          <div className="space-y-2">
            {mappings.map(([src, dst], idx) => (
              <div key={idx} className="flex items-center gap-2">
                <input
                  type="text"
                  value={src}
                  onChange={(e) => updateMapping(idx, 0, e.target.value)}
                  className="flex-1 px-2 py-1 border rounded text-xs font-mono"
                  placeholder="source_field"
                />
                <span className="text-gray-400 text-xs">→</span>
                <input
                  type="text"
                  value={dst}
                  onChange={(e) => updateMapping(idx, 1, e.target.value)}
                  className="flex-1 px-2 py-1 border rounded text-xs font-mono"
                  placeholder="treevuln_field"
                />
                <button onClick={() => removeMapping(idx)} className="p-1 hover:bg-red-50 rounded">
                  <X size={12} className="text-red-500" />
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Toggles */}
      <div className="space-y-2">
        <div className="flex items-center gap-2">
          <button
            onClick={() => setAutoEval(!autoEval)}
            className={`relative w-10 h-5 rounded-full transition-colors ${
              autoEval ? 'bg-blue-500' : 'bg-gray-300'
            }`}
          >
            <span className={`absolute top-0.5 w-4 h-4 bg-white rounded-full transition-transform ${autoEval ? 'left-5' : 'left-0.5'}`} />
          </button>
          <span className="text-sm text-gray-700">Evaluate automatically</span>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setIsActive(!isActive)}
            className={`relative w-10 h-5 rounded-full transition-colors ${
              isActive ? 'bg-green-500' : 'bg-gray-300'
            }`}
          >
            <span className={`absolute top-0.5 w-4 h-4 bg-white rounded-full transition-transform ${isActive ? 'left-5' : 'left-0.5'}`} />
          </button>
          <span className="text-sm text-gray-700">Active</span>
        </div>
      </div>

      {/* Example */}
      <div className="bg-gray-50 rounded-lg p-3">
        <h4 className="text-xs font-medium text-gray-600 mb-2">Usage example</h4>
        <pre className="text-xs bg-white p-2 rounded border overflow-x-auto">
{`curl -X POST '${window.location.origin}/api/v1/ingest/${slug || '{slug}'}' \\
  -H 'Content-Type: application/json' \\
  -H 'X-API-Key: <your-api-key>' \\
  -d '[{
    "cve_id": "CVE-2024-1234",
    "cvss_score": 9.8,
    "kev": true,
    "epss_score": 0.5,
    "asset_criticality": "High"
  }]'`}
        </pre>
      </div>

      <div className="flex justify-end gap-2 pt-2">
        <button
          onClick={onCancel}
          className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-md text-sm"
        >
          Cancel
        </button>
        <button
          onClick={handleSave}
          disabled={saving}
          className="px-4 py-2 bg-green-500 text-white rounded-md hover:bg-green-600 text-sm disabled:opacity-50"
        >
          {saving ? 'Saving...' : 'Save'}
        </button>
      </div>
    </div>
  );
}

function EndpointLogs({ endpointId, onBack }: { endpointId: number; onBack: () => void }) {
  const [logs, setLogs] = useState<IngestLog[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadLogs = async () => {
      try {
        const data = await ingestApi.getLogs(endpointId);
        setLogs(data);
      } catch {
        // silently fail
      } finally {
        setLoading(false);
      }
    };
    loadLogs();
  }, [endpointId]);

  if (loading) {
    return <div className="text-center text-gray-500 py-8">Loading...</div>;
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        <button onClick={onBack} className="text-sm text-blue-600 hover:underline">
          Back
        </button>
        <span className="text-sm text-gray-500">Reception history</span>
      </div>

      {logs.length === 0 ? (
        <div className="text-center text-gray-500 py-8 text-sm">No receptions</div>
      ) : (
        logs.map((log) => (
          <div key={log.id} className="border rounded-lg p-3 text-sm">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <span className={`w-2 h-2 rounded-full ${log.error_count === 0 ? 'bg-green-500' : 'bg-yellow-500'}`} />
                <span className="font-medium">{log.vuln_count} vulns</span>
                <span className="text-green-600 text-xs">{log.success_count} OK</span>
                {log.error_count > 0 && (
                  <span className="text-red-600 text-xs">{log.error_count} errors</span>
                )}
                {log.duration_ms && (
                  <span className="text-gray-400 text-xs">{log.duration_ms}ms</span>
                )}
              </div>
              <div className="text-xs text-gray-400">
                {log.source_ip && <span className="mr-2">{log.source_ip}</span>}
                {new Date(log.created_at).toLocaleString()}
              </div>
            </div>
          </div>
        ))
      )}
    </div>
  );
}

export default IngestConfigDialog;
