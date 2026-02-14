import { useEffect, useState } from 'react';
import {
  Trees,
  Plus,
  Copy,
  Star,
  StarOff,
  Trash2,
  Settings,
  ChevronRight,
  X,
  Check,
  Link,
  Upload,
  Bell,
  Download,
} from 'lucide-react';
import { useTreeStore } from '@/stores/treeStore';
import { useConfirm } from '@/hooks/useConfirm';
import { ConfirmDialog } from '@/components/ui/ConfirmDialog';
import type { TreeListItem } from '@/types';

interface TreeSidebarProps {
  onOpenCreateDialog: () => void;
  onOpenApiConfig: () => void;
  onOpenAssetImport?: () => void;
  onOpenWebhookConfig?: () => void;
  onOpenIngestConfig?: () => void;
}

export function TreeSidebar({ onOpenCreateDialog, onOpenApiConfig, onOpenAssetImport, onOpenWebhookConfig, onOpenIngestConfig }: TreeSidebarProps) {
  const {
    trees,
    treeId,
    isDefault,
    hasUnsavedChanges,
    loadTrees,
    selectTree,
    duplicateTree,
    setAsDefault,
    deleteCurrentTree,
    sidebarOpen,
    setSidebarOpen,
  } = useTreeStore();

  const { confirm, confirmDialogProps } = useConfirm();
  const [duplicating, setDuplicating] = useState<number | null>(null);
  const [duplicateName, setDuplicateName] = useState('');

  // Charge la liste des arbres au montage
  useEffect(() => {
    loadTrees();
  }, [loadTrees]);

  const handleDuplicateStart = (tree: TreeListItem, e: React.MouseEvent) => {
    e.stopPropagation();
    setDuplicating(tree.id);
    setDuplicateName(`${tree.name} (copie)`);
  };

  const handleDuplicateConfirm = async (treeIdToDuplicate: number) => {
    if (!duplicateName.trim()) return;
    try {
      await duplicateTree(treeIdToDuplicate, {
        new_name: duplicateName.trim(),
        include_assets: true,
      });
      setDuplicating(null);
      setDuplicateName('');
    } catch {
      // Error handled in store
    }
  };

  const handleDuplicateCancel = () => {
    setDuplicating(null);
    setDuplicateName('');
  };

  const handleSetDefault = async (e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await setAsDefault();
    } catch {
      // Error handled in store
    }
  };

  const handleDelete = async (e: React.MouseEvent) => {
    e.stopPropagation();
    const ok = await confirm('Supprimer l\'arbre', 'Supprimer cet arbre et tous ses assets ? Cette action est irréversible.');
    if (!ok) return;
    try {
      await deleteCurrentTree();
    } catch {
      // Error handled in store
    }
  };

  if (!sidebarOpen) {
    return (
      <button
        onClick={() => setSidebarOpen(true)}
        className="fixed left-0 top-1/2 -translate-y-1/2 bg-white border border-l-0 rounded-r-lg p-2 shadow-md hover:bg-gray-50 z-10"
        title="Ouvrir la liste des arbres"
      >
        <ChevronRight size={20} className="text-gray-600" />
      </button>
    );
  }

  return (
    <div className="w-72 bg-white border-r flex flex-col h-full">
      {/* Header */}
      <div className="p-3 border-b flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Trees size={20} className="text-blue-600" />
          <span className="font-semibold text-gray-800">Arbres</span>
          <span className="text-xs bg-gray-100 px-2 py-0.5 rounded-full">
            {trees.length}
          </span>
        </div>
        <div className="flex items-center gap-1">
          <button
            onClick={onOpenCreateDialog}
            className="p-1.5 hover:bg-gray-100 rounded-md"
            title="Nouvel arbre"
          >
            <Plus size={18} className="text-gray-600" />
          </button>
          <button
            onClick={() => setSidebarOpen(false)}
            className="p-1.5 hover:bg-gray-100 rounded-md"
            title="Fermer"
          >
            <X size={18} className="text-gray-600" />
          </button>
        </div>
      </div>

      {/* Liste des arbres */}
      <div className="flex-1 overflow-y-auto p-2 space-y-1">
        {trees.map((tree) => (
          <div
            key={tree.id}
            onClick={async () => {
              if (hasUnsavedChanges) {
                const ok = await confirm(
                  'Modifications non sauvegardées',
                  'Vous avez des modifications non sauvegardées. Voulez-vous continuer ?',
                  'warning'
                );
                if (!ok) return;
              }
              selectTree(tree.id);
            }}
            className={`
              relative p-3 rounded-lg cursor-pointer transition-colors
              ${tree.id === treeId
                ? 'bg-blue-50 border border-blue-200'
                : 'hover:bg-gray-50 border border-transparent'
              }
            `}
          >
            {/* Mode duplication */}
            {duplicating === tree.id ? (
              <div className="space-y-2" onClick={(e) => e.stopPropagation()}>
                <input
                  type="text"
                  value={duplicateName}
                  onChange={(e) => setDuplicateName(e.target.value)}
                  className="w-full px-2 py-1 text-sm border rounded"
                  placeholder="Nom de la copie"
                  autoFocus
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') handleDuplicateConfirm(tree.id);
                    if (e.key === 'Escape') handleDuplicateCancel();
                  }}
                />
                <div className="flex justify-end gap-1">
                  <button
                    onClick={handleDuplicateCancel}
                    className="p-1 hover:bg-gray-100 rounded"
                    title="Annuler"
                  >
                    <X size={16} className="text-gray-500" />
                  </button>
                  <button
                    onClick={() => handleDuplicateConfirm(tree.id)}
                    className="p-1 hover:bg-green-100 rounded"
                    title="Confirmer"
                  >
                    <Check size={16} className="text-green-600" />
                  </button>
                </div>
              </div>
            ) : (
              <>
                {/* Contenu normal */}
                <div className="flex items-start justify-between">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-gray-800 truncate">
                        {tree.name}
                      </span>
                      {tree.is_default && (
                        <Star size={14} className="text-yellow-500 fill-yellow-500 flex-shrink-0" />
                      )}
                    </div>
                    <div className="text-xs text-gray-500 mt-0.5">
                      {tree.node_count} noeuds
                    </div>
                    {tree.api_enabled && tree.api_slug && (
                      <div className="flex items-center gap-1 text-xs text-green-600 mt-1">
                        <Link size={12} />
                        <span className="truncate">{tree.api_slug}</span>
                      </div>
                    )}
                  </div>
                </div>

                {/* Actions (visibles uniquement pour l'arbre sélectionné) */}
                {tree.id === treeId && (
                  <div className="flex items-center gap-1 mt-2 pt-2 border-t border-gray-200 flex-wrap">
                    <button
                      onClick={(e) => handleDuplicateStart(tree, e)}
                      className="p-1.5 hover:bg-gray-100 rounded-md"
                      title="Dupliquer"
                    >
                      <Copy size={16} className="text-gray-500" />
                    </button>
                    <button
                      onClick={onOpenApiConfig}
                      className="p-1.5 hover:bg-gray-100 rounded-md"
                      title="Configurer API"
                    >
                      <Settings size={16} className="text-gray-500" />
                    </button>
                    {onOpenAssetImport && (
                      <button
                        onClick={(e) => { e.stopPropagation(); onOpenAssetImport(); }}
                        className="p-1.5 hover:bg-blue-50 rounded-md"
                        title="Importer des assets"
                      >
                        <Upload size={16} className="text-gray-500" />
                      </button>
                    )}
                    {onOpenWebhookConfig && (
                      <button
                        onClick={(e) => { e.stopPropagation(); onOpenWebhookConfig(); }}
                        className="p-1.5 hover:bg-orange-50 rounded-md"
                        title="Webhooks sortants"
                      >
                        <Bell size={16} className="text-gray-500" />
                      </button>
                    )}
                    {onOpenIngestConfig && (
                      <button
                        onClick={(e) => { e.stopPropagation(); onOpenIngestConfig(); }}
                        className="p-1.5 hover:bg-green-50 rounded-md"
                        title="Webhooks entrants"
                      >
                        <Download size={16} className="text-gray-500" />
                      </button>
                    )}
                    {!isDefault && (
                      <>
                        <button
                          onClick={handleSetDefault}
                          className="p-1.5 hover:bg-yellow-50 rounded-md"
                          title="Définir comme défaut"
                        >
                          <StarOff size={16} className="text-gray-500" />
                        </button>
                        <button
                          onClick={handleDelete}
                          className="p-1.5 hover:bg-red-50 rounded-md ml-auto"
                          title="Supprimer"
                        >
                          <Trash2 size={16} className="text-red-500" />
                        </button>
                      </>
                    )}
                  </div>
                )}
              </>
            )}
          </div>
        ))}

        {trees.length === 0 && (
          <div className="text-center text-gray-500 py-8">
            <Trees size={32} className="mx-auto mb-2 opacity-50" />
            <p className="text-sm">Aucun arbre</p>
            <button
              onClick={onOpenCreateDialog}
              className="text-blue-500 hover:underline text-sm mt-2"
            >
              Créer un arbre
            </button>
          </div>
        )}
      </div>
      <ConfirmDialog {...confirmDialogProps} />
    </div>
  );
}

export default TreeSidebar;
