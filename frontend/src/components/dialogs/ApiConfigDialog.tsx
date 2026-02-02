import { useState, useEffect } from 'react';
import { X, Link, Copy, Check } from 'lucide-react';
import { useTreeStore } from '@/stores/treeStore';

interface ApiConfigDialogProps {
  onClose: () => void;
}

export function ApiConfigDialog({ onClose }: ApiConfigDialogProps) {
  const { treeName, apiEnabled, apiSlug, updateApiConfig } = useTreeStore();

  const [enabled, setEnabled] = useState(apiEnabled);
  const [slug, setSlug] = useState(apiSlug || '');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  // Génère un slug par défaut basé sur le nom
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
      setError('Le slug est requis quand l\'API est activée');
      return;
    }

    // Valide le format du slug
    const slugRegex = /^[a-z0-9][a-z0-9-]*[a-z0-9]$|^[a-z0-9]$/;
    if (enabled && !slugRegex.test(slug)) {
      setError('Le slug doit contenir uniquement des lettres minuscules, chiffres et tirets');
      return;
    }

    setSaving(true);
    setError(null);

    try {
      await updateApiConfig({
        api_enabled: enabled,
        api_slug: enabled ? slug.trim() : null,
      });
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erreur de sauvegarde');
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
            <Link size={20} className="text-blue-600" />
            <h2 className="text-lg font-semibold">Configuration API</h2>
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
          {/* Toggle activation */}
          <div className="flex items-center justify-between">
            <div>
              <label className="font-medium text-gray-800">
                Activer l'endpoint API dédié
              </label>
              <p className="text-sm text-gray-500">
                Permet d'évaluer des vulnérabilités via une URL spécifique à cet arbre
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
                  Slug de l'URL
                </label>
                <input
                  type="text"
                  value={slug}
                  onChange={(e) => setSlug(e.target.value.toLowerCase())}
                  placeholder="mon-arbre"
                  className="w-full px-3 py-2 border rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                />
                <p className="text-xs text-gray-500 mt-1">
                  Lettres minuscules, chiffres et tirets uniquement
                </p>
              </div>

              {/* URL preview */}
              {slug && (
                <div className="bg-gray-50 rounded-lg p-3">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-medium text-gray-700">URL de l'API</span>
                    <button
                      onClick={handleCopy}
                      className="flex items-center gap-1 text-sm text-blue-600 hover:text-blue-800"
                    >
                      {copied ? (
                        <>
                          <Check size={14} />
                          Copié
                        </>
                      ) : (
                        <>
                          <Copy size={14} />
                          Copier
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
                  Exemple d'utilisation
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
            Annuler
          </button>
          <button
            onClick={handleSave}
            disabled={saving}
            className="px-4 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600 disabled:opacity-50"
          >
            {saving ? 'Sauvegarde...' : 'Sauvegarder'}
          </button>
        </div>
      </div>
    </div>
  );
}

export default ApiConfigDialog;
