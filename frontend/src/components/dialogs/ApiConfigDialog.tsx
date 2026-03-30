import { useState, useEffect } from 'react';
import { X, Copy, Check, Settings2 } from 'lucide-react';
import { useTreeStore } from '@/stores/treeStore';

interface ApiConfigDialogProps {
  onClose: () => void;
}

export function ApiConfigDialog({ onClose }: ApiConfigDialogProps) {
  const { treeName, treeDescription, apiEnabled, apiSlug, updateApiConfig, setTreeName, setTreeDescription, saveTree } = useTreeStore();

  const [name, setName] = useState(treeName);
  const [description, setDescription] = useState(treeDescription);
  const [enabled, setEnabled] = useState(apiEnabled);
  const [slug, setSlug] = useState(apiSlug || '');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  // Generate a default slug based on the name
  useEffect(() => {
    if (!apiSlug && treeName) {
      const generated = treeName
        .toLowerCase()
        .normalize('NFD')
        .replace(/[\u0300-\u036f]/g, '')
        .replace(/[^a-z0-9]+/g, '-')
        .replace(/^-|-$/g, '');
      setSlug(generated);
    }
  }, [treeName, apiSlug]);

  const handleSave = async () => {
    if (enabled && !slug.trim()) {
      setError('Slug is required when the API is enabled');
      return;
    }

    // Validate slug format
    const slugRegex = /^[a-z0-9][a-z0-9-]*[a-z0-9]$|^[a-z0-9]$/;
    if (enabled && !slugRegex.test(slug)) {
      setError('Slug must contain only lowercase letters, numbers, and hyphens');
      return;
    }

    const trimmedName = name.trim();
    if (!trimmedName) {
      setError('Tree name is required');
      return;
    }

    setSaving(true);
    setError(null);

    try {
      // Persist name/description to backend (no version for metadata-only changes)
      setTreeName(trimmedName);
      setTreeDescription(description);
      await saveTree(undefined, false);

      // Update API config (also refreshes sidebar tree list)
      await updateApiConfig({
        api_enabled: enabled,
        api_slug: enabled ? slug.trim() : null,
      });

      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Save error');
    } finally {
      setSaving(false);
    }
  };

  const apiUrl = slug ? `${window.location.origin}/api/v1/evaluate/tree/${slug}` : '';

  const handleCopy = () => {
    navigator.clipboard.writeText(apiUrl);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-lg">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b">
          <div className="flex items-center gap-2">
            <Settings2 size={20} className="text-blue-600" />
            <h2 className="text-lg font-semibold">Tree Configuration</h2>
          </div>
          <button
            onClick={onClose}
            className="p-1 hover:bg-gray-100 rounded-md"
          >
            <X size={20} className="text-gray-500" />
          </button>
        </div>

        {/* Content */}
        <div className="p-4 space-y-4">
          {/* Tree name */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Tree name
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="My tree"
              className="w-full px-3 py-2 border rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>

          {/* Description */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Description
            </label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Tree description..."
              rows={2}
              className="w-full px-3 py-2 border rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500 resize-none"
            />
          </div>

          <hr className="border-gray-200" />

          {/* Toggle activation */}
          <div className="flex items-center justify-between">
            <div>
              <label className="font-medium text-gray-800">
                Enable dedicated API endpoint
              </label>
              <p className="text-sm text-gray-500">
                Evaluate vulnerabilities via a URL specific to this tree
              </p>
            </div>
            <button
              onClick={() => setEnabled(!enabled)}
              className={`
                relative w-12 h-6 rounded-full transition-colors
                ${enabled ? 'bg-blue-500' : 'bg-gray-300'}
              `}
            >
              <span
                className={`
                  absolute top-1 w-4 h-4 bg-white rounded-full transition-transform
                  ${enabled ? 'left-7' : 'left-1'}
                `}
              />
            </button>
          </div>

          {/* Slug configuration */}
          {enabled && (
            <div className="space-y-3 pt-3 border-t">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  URL Slug
                </label>
                <input
                  type="text"
                  value={slug}
                  onChange={(e) => setSlug(e.target.value.toLowerCase())}
                  placeholder="my-tree"
                  className="w-full px-3 py-2 border rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                />
                <p className="text-xs text-gray-500 mt-1">
                  Lowercase letters, numbers, and hyphens only
                </p>
              </div>

              {/* URL preview */}
              {slug && (
                <div className="bg-gray-50 rounded-lg p-3">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-medium text-gray-700">API URL</span>
                    <button
                      onClick={handleCopy}
                      className="flex items-center gap-1 text-sm text-blue-600 hover:text-blue-800"
                    >
                      {copied ? (
                        <>
                          <Check size={14} />
                          Copied
                        </>
                      ) : (
                        <>
                          <Copy size={14} />
                          Copy
                        </>
                      )}
                    </button>
                  </div>
                  <code className="block text-xs bg-white p-2 rounded border break-all">
                    {apiUrl}
                  </code>
                </div>
              )}

              {/* Documentation */}
              <div className="bg-blue-50 rounded-lg p-3">
                <h4 className="text-sm font-medium text-blue-800 mb-2">
                  Usage example
                </h4>
                <pre className="text-xs bg-white p-2 rounded border overflow-x-auto">
{`curl -X POST '${apiUrl || '/api/v1/evaluate/tree/{slug}'}' \\
  -H 'Content-Type: application/json' \\
  -d '{
    "vulnerability": {
      "cve_id": "CVE-2024-1234",
      "cvss_score": 9.8,
      "kev": true,
      "asset_id": "srv-prod-001"
    }
  }'`}
                </pre>
              </div>
            </div>
          )}

          {/* Error message */}
          {error && (
            <div className="bg-red-50 text-red-600 text-sm p-3 rounded-lg">
              {error}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex justify-end gap-2 p-4 border-t bg-gray-50 rounded-b-lg">
          <button
            onClick={onClose}
            className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-md"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={saving}
            className="px-4 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600 disabled:opacity-50"
          >
            {saving ? 'Saving...' : 'Save'}
          </button>
        </div>
      </div>
    </div>
  );
}

export default ApiConfigDialog;
