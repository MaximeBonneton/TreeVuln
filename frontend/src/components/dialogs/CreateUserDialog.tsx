import { useState } from 'react';
import { X, Shield, RefreshCw, Copy, Check } from 'lucide-react';
import { usersApi } from '@/api/users';

interface CreateUserDialogProps {
  onClose: () => void;
  onCreated: () => void;
}

// Génère un mot de passe aléatoire de 16 caractères
function generatePassword(): string {
  const chars = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%&*-_=+';
  const array = new Uint8Array(16);
  crypto.getRandomValues(array);
  return Array.from(array, (byte) => chars[byte % chars.length]).join('');
}

export function CreateUserDialog({ onClose, onCreated }: CreateUserDialogProps) {
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [role, setRole] = useState<'admin' | 'operator'>('operator');
  const [password, setPassword] = useState('');
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const handleGenerate = () => {
    const pwd = generatePassword();
    setPassword(pwd);
    setCopied(false);
  };

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(password);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Fallback : sélection manuelle
    }
  };

  const handleCreate = async () => {
    if (!username.trim()) {
      setError('Le nom d\'utilisateur est requis');
      return;
    }
    if (password.length < 12) {
      setError('Le mot de passe doit contenir au moins 12 caractères');
      return;
    }

    setCreating(true);
    setError(null);

    try {
      await usersApi.create({
        username: username.trim(),
        password,
        role,
        email: email.trim() || undefined,
      });
      onCreated();
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Erreur lors de la création';
      setError(message);
      setCreating(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-[60]">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-md">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b">
          <div className="flex items-center gap-2">
            <Shield size={20} className="text-blue-600" />
            <h2 className="text-lg font-semibold">Nouvel utilisateur</h2>
          </div>
          <button
            onClick={onClose}
            className="p-1 hover:bg-gray-100 rounded-md"
          >
            <X size={20} className="text-gray-500" />
          </button>
        </div>

        {/* Contenu */}
        <div className="p-4 space-y-4">
          {/* Nom d'utilisateur */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Nom d'utilisateur *
            </label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="Ex: jean.dupont"
              className="w-full px-3 py-2 border rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              autoFocus
            />
          </div>

          {/* Email */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Email (optionnel)
            </label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="Ex: jean.dupont@example.com"
              className="w-full px-3 py-2 border rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>

          {/* Rôle */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Rôle
            </label>
            <select
              value={role}
              onChange={(e) => setRole(e.target.value as 'admin' | 'operator')}
              className="w-full px-3 py-2 border rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500 bg-white"
            >
              <option value="operator">Opérateur</option>
              <option value="admin">Administrateur</option>
            </select>
            <p className="text-xs text-gray-500 mt-1">
              {role === 'admin'
                ? 'Peut modifier les arbres, gérer les utilisateurs et configurer le système.'
                : 'Peut consulter et tester les arbres en lecture seule.'}
            </p>
          </div>

          {/* Mot de passe */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Mot de passe *
            </label>
            <div className="flex gap-2">
              <input
                type="text"
                value={password}
                onChange={(e) => { setPassword(e.target.value); setCopied(false); }}
                placeholder="12 caractères minimum"
                className="flex-1 px-3 py-2 border rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500 font-mono text-sm"
              />
              <button
                onClick={handleGenerate}
                className="px-3 py-2 text-gray-600 hover:bg-gray-100 border rounded-md flex items-center gap-1"
                title="Générer un mot de passe"
                type="button"
              >
                <RefreshCw size={16} />
                <span className="text-sm">Générer</span>
              </button>
            </div>
            {/* Bouton copier (visible si mot de passe rempli) */}
            {password && (
              <button
                onClick={handleCopy}
                className="flex items-center gap-1 mt-1 text-xs text-blue-600 hover:text-blue-800"
                type="button"
              >
                {copied ? (
                  <>
                    <Check size={12} />
                    Copié !
                  </>
                ) : (
                  <>
                    <Copy size={12} />
                    Copier le mot de passe
                  </>
                )}
              </button>
            )}
          </div>

          {/* Info */}
          <div className="bg-blue-50 rounded-lg p-3 text-sm text-blue-800">
            <p>
              L'utilisateur devra changer son mot de passe lors de sa première connexion.
            </p>
          </div>

          {/* Erreur */}
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
            onClick={handleCreate}
            disabled={creating || !username.trim() || password.length < 12}
            className="px-4 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {creating ? 'Création...' : 'Créer'}
          </button>
        </div>
      </div>
    </div>
  );
}

export default CreateUserDialog;
