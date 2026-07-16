import { useEffect, useState } from 'react';
import { X } from 'lucide-react';
import { settingsApi, type CsafSettings } from '@/api';
import { useConfirm } from '@/hooks/useConfirm';
import { ConfirmDialog } from '@/components/ui/ConfirmDialog';

const CATEGORIES = [
  'vendor',
  'coordinator',
  'discoverer',
  'other',
  'translator',
  'user',
];

interface CsafConfigDialogProps {
  onClose: () => void;
}

/**
 * Configuration CSAF (admin) : identité éditeur + clé de signature OpenPGP.
 * La clé privée n'est jamais relue depuis le serveur — seulement son empreinte.
 */
export function CsafConfigDialog({ onClose }: CsafConfigDialogProps) {
  const [settings, setSettings] = useState<CsafSettings | null>(null);
  const [name, setName] = useState('');
  const [namespace, setNamespace] = useState('');
  const [category, setCategory] = useState('vendor');
  const [signingKey, setSigningKey] = useState('');
  const [passphrase, setPassphrase] = useState('');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const { confirm, confirmDialogProps } = useConfirm();

  useEffect(() => {
    settingsApi
      .getCsafSettings()
      .then((s) => {
        setSettings(s);
        if (s.publisher) {
          setName(s.publisher.name);
          setNamespace(s.publisher.namespace);
          setCategory(s.publisher.category);
        }
      })
      .catch((e) => setError(e.message));
  }, []);

  const handleSave = async () => {
    setSaving(true);
    setError(null);
    setSuccess(false);
    try {
      const updated = await settingsApi.updateCsafSettings({
        publisher: { name, namespace, category },
        ...(signingKey
          ? {
              signing_key: signingKey,
              signing_key_passphrase: passphrase || undefined,
            }
          : {}),
      });
      setSettings(updated);
      setSigningKey('');
      setPassphrase('');
      setSuccess(true);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Save failed');
    } finally {
      setSaving(false);
    }
  };

  const handleRemoveKey = async () => {
    const ok = await confirm(
      'Remove signing key',
      'CSAF exports will no longer be signed. Continue?',
      'warning'
    );
    if (!ok) return;
    setError(null);
    try {
      const updated = await settingsApi.updateCsafSettings({
        remove_signing_key: true,
      });
      setSettings(updated);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Removal failed');
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-[520px] max-h-[85vh] overflow-y-auto">
        <div className="flex items-center justify-between p-4 border-b sticky top-0 bg-white">
          <h2 className="font-bold text-gray-800">CSAF configuration</h2>
          <button onClick={onClose} className="p-1 hover:bg-gray-100 rounded">
            <X size={20} />
          </button>
        </div>

        <div className="p-4 space-y-4">
          {error && (
            <p className="text-sm text-red-600 bg-red-50 rounded p-2">{error}</p>
          )}
          {success && (
            <p className="text-sm text-green-700 bg-green-50 rounded p-2">
              Settings saved.
            </p>
          )}

          <fieldset className="space-y-3">
            <legend className="text-sm font-semibold text-gray-700">
              Publisher identity
            </legend>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Name
              </label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="w-full px-3 py-2 border rounded-md"
                placeholder="ACME Medical"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Namespace (URL)
              </label>
              <input
                type="text"
                value={namespace}
                onChange={(e) => setNamespace(e.target.value)}
                className="w-full px-3 py-2 border rounded-md"
                placeholder="https://acme-medical.example.com"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Category
              </label>
              <select
                value={category}
                onChange={(e) => setCategory(e.target.value)}
                className="w-full px-3 py-2 border rounded-md bg-white"
              >
                {CATEGORIES.map((c) => (
                  <option key={c} value={c}>
                    {c}
                  </option>
                ))}
              </select>
            </div>
          </fieldset>

          <fieldset className="space-y-3 pt-3 border-t">
            <legend className="text-sm font-semibold text-gray-700">
              OpenPGP signing key
            </legend>
            {settings?.has_signing_key ? (
              <div className="flex items-center justify-between bg-gray-50 rounded p-2">
                <p className="text-xs font-mono text-gray-600 break-all">
                  {settings.signing_key_fingerprint}
                </p>
                <button
                  onClick={handleRemoveKey}
                  className="ml-2 text-sm text-red-600 hover:text-red-800 shrink-0"
                >
                  Remove
                </button>
              </div>
            ) : (
              <p className="text-xs text-gray-500 italic">
                No signing key configured. Unsigned exports remain possible.
              </p>
            )}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Import private key (ASCII-armored)
              </label>
              <textarea
                value={signingKey}
                onChange={(e) => setSigningKey(e.target.value)}
                rows={5}
                className="w-full px-3 py-2 border rounded-md font-mono text-xs"
                placeholder="-----BEGIN PGP PRIVATE KEY BLOCK-----"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Passphrase (optional)
              </label>
              <input
                type="password"
                value={passphrase}
                onChange={(e) => setPassphrase(e.target.value)}
                className="w-full px-3 py-2 border rounded-md"
                autoComplete="off"
              />
            </div>
          </fieldset>
        </div>

        <div className="flex justify-end gap-2 p-4 border-t sticky bottom-0 bg-white">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm text-gray-600 hover:bg-gray-100 rounded-md"
          >
            Close
          </button>
          <button
            onClick={handleSave}
            disabled={saving || !name || !namespace}
            className="px-4 py-2 text-sm bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
          >
            {saving ? 'Saving…' : 'Save'}
          </button>
        </div>
      </div>
      <ConfirmDialog {...confirmDialogProps} />
    </div>
  );
}
