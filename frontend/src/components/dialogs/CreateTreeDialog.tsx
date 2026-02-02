import { useState } from 'react';
import { X, Trees } from 'lucide-react';
import { useTreeStore } from '@/stores/treeStore';

interface CreateTreeDialogProps {
  onClose: () => void;
}

export function CreateTreeDialog({ onClose }: CreateTreeDialogProps) {
  const { createNewTree, saveTree, loadTrees } = useTreeStore();

  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleCreate = async () => {
    if (!name.trim()) {
      setError('Le nom est requis');
      return;
    }

    setCreating(true);
    setError(null);

    try {
      // Crée un nouvel arbre vide
      await createNewTree(name.trim(), description.trim() || undefined);
      // Sauvegarde immédiatement pour obtenir un ID
      await saveTree('Création initiale');
      // Recharge la liste des arbres
      await loadTrees();
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erreur de création');
      setCreating(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-md">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b">
          <div className="flex items-center gap-2">
            <Trees size={20} className="text-blue-600" />
            <h2 className="text-lg font-semibold">Nouvel arbre</h2>
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
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Nom de l'arbre *
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Ex: Priorisation SSVC Production"
              className="w-full px-3 py-2 border rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              autoFocus
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  handleCreate();
                }
              }}
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Description (optionnel)
            </label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Description de l'arbre et de son contexte d'utilisation..."
              rows={3}
              className="w-full px-3 py-2 border rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500 resize-none"
            />
          </div>

          {/* Info */}
          <div className="bg-blue-50 rounded-lg p-3 text-sm text-blue-800">
            <p>
              L'arbre sera créé vide. Vous pourrez ensuite y ajouter des noeuds
              depuis l'éditeur graphique et configurer ses assets.
            </p>
          </div>

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
            onClick={handleCreate}
            disabled={creating || !name.trim()}
            className="px-4 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600 disabled:opacity-50"
          >
            {creating ? 'Création...' : 'Créer'}
          </button>
        </div>
      </div>
    </div>
  );
}

export default CreateTreeDialog;
