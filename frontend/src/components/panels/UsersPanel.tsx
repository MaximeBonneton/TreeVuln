import { useState, useEffect, useCallback } from 'react';
import { X, Plus, Trash2, KeyRound, Shield, ShieldOff } from 'lucide-react';
import { usersApi, type UserResponse } from '@/api/users';
import { useConfirm } from '@/hooks/useConfirm';
import { ConfirmDialog } from '@/components/ui/ConfirmDialog';
import { CreateUserDialog } from '@/components/dialogs/CreateUserDialog';
import { useTreeStore } from '@/stores/treeStore';

interface UsersPanelProps {
  onClose: () => void;
}

export function UsersPanel({ onClose }: UsersPanelProps) {
  const [users, setUsers] = useState<UserResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [resetPasswordUserId, setResetPasswordUserId] = useState<string | null>(null);
  const [newPassword, setNewPassword] = useState('');
  const [resetError, setResetError] = useState<string | null>(null);
  const { confirm, confirmDialogProps } = useConfirm();
  const currentUser = useTreeStore((s) => s.currentUser);

  // Charge la liste des utilisateurs
  const loadUsers = useCallback(async () => {
    try {
      setLoading(true);
      const data = await usersApi.list();
      setUsers(data);
      setError(null);
    } catch {
      setError('Erreur lors du chargement des utilisateurs');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadUsers();
  }, [loadUsers]);

  // Bascule le rôle d'un utilisateur
  const handleToggleRole = async (user: UserResponse) => {
    const newRole = user.role === 'admin' ? 'operator' : 'admin';
    try {
      await usersApi.update(user.id, { role: newRole });
      await loadUsers();
    } catch {
      setError('Erreur lors de la modification du rôle');
    }
  };

  // Bascule l'état actif/inactif
  const handleToggleActive = async (user: UserResponse) => {
    try {
      await usersApi.update(user.id, { is_active: !user.is_active });
      await loadUsers();
    } catch {
      setError('Erreur lors de la modification du statut');
    }
  };

  // Réinitialise le mot de passe
  const handleResetPassword = async (userId: string) => {
    if (newPassword.length < 12) {
      setResetError('Le mot de passe doit contenir au moins 12 caractères');
      return;
    }
    try {
      await usersApi.resetPassword(userId, newPassword);
      setResetPasswordUserId(null);
      setNewPassword('');
      setResetError(null);
    } catch {
      setResetError('Erreur lors de la réinitialisation');
    }
  };

  // Supprime un utilisateur
  const handleDelete = async (user: UserResponse) => {
    const ok = await confirm(
      'Supprimer l\'utilisateur',
      `Supprimer l'utilisateur "${user.username}" ? Cette action est irréversible.`
    );
    if (!ok) return;
    try {
      await usersApi.delete(user.id);
      await loadUsers();
    } catch {
      setError('Erreur lors de la suppression');
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-3xl max-h-[80vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b">
          <div className="flex items-center gap-2">
            <Shield size={20} className="text-blue-600" />
            <h2 className="text-lg font-semibold text-gray-800">Gestion des utilisateurs</h2>
            <span className="text-xs bg-gray-100 px-2 py-0.5 rounded-full">
              {users.length}
            </span>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setShowCreateDialog(true)}
              className="flex items-center gap-1 px-3 py-1.5 bg-blue-500 text-white text-sm rounded-md hover:bg-blue-600"
            >
              <Plus size={16} />
              Nouvel utilisateur
            </button>
            <button
              onClick={onClose}
              className="p-1 hover:bg-gray-100 rounded-md"
            >
              <X size={20} className="text-gray-500" />
            </button>
          </div>
        </div>

        {/* Contenu */}
        <div className="flex-1 overflow-y-auto p-4">
          {error && (
            <div className="bg-red-50 text-red-600 text-sm p-3 rounded-lg mb-4">
              {error}
            </div>
          )}

          {loading ? (
            <div className="text-center text-gray-500 py-8">Chargement...</div>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-gray-500 border-b">
                  <th className="pb-2 font-medium">Utilisateur</th>
                  <th className="pb-2 font-medium">Email</th>
                  <th className="pb-2 font-medium">Rôle</th>
                  <th className="pb-2 font-medium">Statut</th>
                  <th className="pb-2 font-medium text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {users.map((user) => {
                  const isSelf = currentUser?.id === user.id;
                  return (
                    <tr key={user.id} className="hover:bg-gray-50">
                      <td className="py-3">
                        <div className="flex items-center gap-2">
                          <span className="font-medium text-gray-800">{user.username}</span>
                          {isSelf && (
                            <span className="text-xs text-gray-400">(vous)</span>
                          )}
                        </div>
                      </td>
                      <td className="py-3 text-gray-600">
                        {user.email || <span className="text-gray-400 italic">-</span>}
                      </td>
                      <td className="py-3">
                        <span
                          className={`text-xs px-2 py-0.5 rounded font-medium ${
                            user.role === 'admin'
                              ? 'bg-blue-100 text-blue-700'
                              : 'bg-gray-100 text-gray-600'
                          }`}
                        >
                          {user.role}
                        </span>
                      </td>
                      <td className="py-3">
                        <span
                          className={`text-xs px-2 py-0.5 rounded font-medium ${
                            user.is_active
                              ? 'bg-green-100 text-green-700'
                              : 'bg-red-100 text-red-600'
                          }`}
                        >
                          {user.is_active ? 'Actif' : 'Inactif'}
                        </span>
                      </td>
                      <td className="py-3">
                        {/* Ligne de réinitialisation de mot de passe */}
                        {resetPasswordUserId === user.id ? (
                          <div className="flex items-center gap-2 justify-end">
                            <input
                              type="text"
                              value={newPassword}
                              onChange={(e) => { setNewPassword(e.target.value); setResetError(null); }}
                              placeholder="Nouveau mot de passe (12+ car.)"
                              className="w-48 px-2 py-1 text-sm border rounded-md focus:outline-none focus:ring-1 focus:ring-blue-500"
                              autoFocus
                              onKeyDown={(e) => {
                                if (e.key === 'Enter') handleResetPassword(user.id);
                                if (e.key === 'Escape') { setResetPasswordUserId(null); setNewPassword(''); setResetError(null); }
                              }}
                            />
                            <button
                              onClick={() => handleResetPassword(user.id)}
                              className="px-2 py-1 text-xs bg-blue-500 text-white rounded hover:bg-blue-600"
                            >
                              OK
                            </button>
                            <button
                              onClick={() => { setResetPasswordUserId(null); setNewPassword(''); setResetError(null); }}
                              className="px-2 py-1 text-xs text-gray-500 hover:bg-gray-100 rounded"
                            >
                              Annuler
                            </button>
                          </div>
                        ) : (
                          <div className="flex items-center gap-1 justify-end">
                            {/* Bascule rôle */}
                            <button
                              onClick={() => handleToggleRole(user)}
                              disabled={isSelf}
                              className="p-1.5 hover:bg-gray-100 rounded-md disabled:opacity-30 disabled:cursor-not-allowed"
                              title={user.role === 'admin' ? 'Passer en opérateur' : 'Passer en admin'}
                            >
                              {user.role === 'admin' ? (
                                <ShieldOff size={16} className="text-gray-500" />
                              ) : (
                                <Shield size={16} className="text-blue-500" />
                              )}
                            </button>
                            {/* Bascule actif/inactif */}
                            <button
                              onClick={() => handleToggleActive(user)}
                              disabled={isSelf}
                              className={`px-2 py-1 text-xs rounded font-medium disabled:opacity-30 disabled:cursor-not-allowed ${
                                user.is_active
                                  ? 'text-orange-600 hover:bg-orange-50'
                                  : 'text-green-600 hover:bg-green-50'
                              }`}
                              title={user.is_active ? 'Désactiver' : 'Activer'}
                            >
                              {user.is_active ? 'Désactiver' : 'Activer'}
                            </button>
                            {/* Réinitialiser le mot de passe */}
                            <button
                              onClick={() => { setResetPasswordUserId(user.id); setNewPassword(''); setResetError(null); }}
                              className="p-1.5 hover:bg-gray-100 rounded-md"
                              title="Réinitialiser le mot de passe"
                            >
                              <KeyRound size={16} className="text-gray-500" />
                            </button>
                            {/* Supprimer */}
                            <button
                              onClick={() => handleDelete(user)}
                              disabled={isSelf}
                              className="p-1.5 hover:bg-red-50 rounded-md disabled:opacity-30 disabled:cursor-not-allowed"
                              title="Supprimer"
                            >
                              <Trash2 size={16} className="text-red-500" />
                            </button>
                          </div>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}

          {/* Erreur réinitialisation mot de passe */}
          {resetError && (
            <div className="bg-red-50 text-red-600 text-sm p-2 rounded mt-2">
              {resetError}
            </div>
          )}
        </div>
      </div>

      <ConfirmDialog {...confirmDialogProps} />

      {/* Dialog de création d'utilisateur */}
      {showCreateDialog && (
        <CreateUserDialog
          onClose={() => setShowCreateDialog(false)}
          onCreated={() => { setShowCreateDialog(false); loadUsers(); }}
        />
      )}
    </div>
  );
}
