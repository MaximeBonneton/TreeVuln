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
  LogOut,
  KeyRound,
  Users,
  Package,
} from 'lucide-react';
import { useTreeStore } from '@/stores/treeStore';
import { useConfirm } from '@/hooks/useConfirm';
import { ConfirmDialog } from '@/components/ui/ConfirmDialog';
import { authApi } from '@/api/auth';
import ChangePasswordDialog from '@/components/ChangePasswordDialog';
import { UsersPanel } from '@/components/panels/UsersPanel';
import type { TreeListItem } from '@/types';

interface TreeSidebarProps {
  onOpenCreateDialog: () => void;
  onOpenApiConfig: () => void;
  onOpenAssetImport?: () => void;
  onOpenWebhookConfig?: () => void;
  onOpenIngestConfig?: () => void;
  onOpenSbomConfig?: () => void;
}

export function TreeSidebar({ onOpenCreateDialog, onOpenApiConfig, onOpenAssetImport, onOpenWebhookConfig, onOpenIngestConfig, onOpenSbomConfig }: TreeSidebarProps) {
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
    currentUser,
    isAdmin,
  } = useTreeStore();

  const { confirm, confirmDialogProps } = useConfirm();
  const [duplicating, setDuplicating] = useState<number | null>(null);
  const [duplicateName, setDuplicateName] = useState('');
  const [showChangePassword, setShowChangePassword] = useState(false);
  const [showUsersPanel, setShowUsersPanel] = useState(false);

  // Logout
  const handleLogout = async () => {
    try {
      await authApi.logout();
    } catch {
      // Ignore logout errors
    }
    window.location.reload();
  };

  // Load tree list on mount
  useEffect(() => {
    loadTrees();
  }, [loadTrees]);

  const handleDuplicateStart = (tree: TreeListItem, e: React.MouseEvent) => {
    e.stopPropagation();
    setDuplicating(tree.id);
    setDuplicateName(`${tree.name} (copy)`);
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
    const ok = await confirm('Delete tree', 'Delete this tree and all its assets? This action is irreversible.');
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
        title="Open tree list"
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
          <span className="font-semibold text-gray-800">Trees</span>
          <span className="text-xs bg-gray-100 px-2 py-0.5 rounded-full">
            {trees.length}
          </span>
        </div>
        <div className="flex items-center gap-1">
          {isAdmin() && (
            <button
              onClick={onOpenCreateDialog}
              className="p-1.5 hover:bg-gray-100 rounded-md"
              title="New tree"
            >
              <Plus size={18} className="text-gray-600" />
            </button>
          )}
          <button
            onClick={() => setSidebarOpen(false)}
            className="p-1.5 hover:bg-gray-100 rounded-md"
            title="Close"
          >
            <X size={18} className="text-gray-600" />
          </button>
        </div>
      </div>

      {/* Tree list */}
      <div className="flex-1 overflow-y-auto p-2 space-y-1">
        {trees.map((tree) => (
          <div
            key={tree.id}
            onClick={async () => {
              if (hasUnsavedChanges) {
                const ok = await confirm(
                  'Unsaved changes',
                  'You have unsaved changes. Do you want to continue?',
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
            {/* Duplication mode */}
            {duplicating === tree.id ? (
              <div className="space-y-2" onClick={(e) => e.stopPropagation()}>
                <input
                  type="text"
                  value={duplicateName}
                  onChange={(e) => setDuplicateName(e.target.value)}
                  className="w-full px-2 py-1 text-sm border rounded"
                  placeholder="Copy name"
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
                    title="Cancel"
                  >
                    <X size={16} className="text-gray-500" />
                  </button>
                  <button
                    onClick={() => handleDuplicateConfirm(tree.id)}
                    className="p-1 hover:bg-green-100 rounded"
                    title="Confirm"
                  >
                    <Check size={16} className="text-green-600" />
                  </button>
                </div>
              </div>
            ) : (
              <>
                {/* Normal content */}
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
                      {tree.node_count} nodes
                    </div>
                    {tree.api_enabled && tree.api_slug && (
                      <div className="flex items-center gap-1 text-xs text-green-600 mt-1">
                        <Link size={12} />
                        <span className="truncate">{tree.api_slug}</span>
                      </div>
                    )}
                  </div>
                </div>

                {/* Actions (visible only for selected tree, admin only) */}
                {tree.id === treeId && isAdmin() && (
                  <div className="flex items-center gap-1 mt-2 pt-2 border-t border-gray-200 flex-wrap">
                    <button
                      onClick={(e) => handleDuplicateStart(tree, e)}
                      className="p-1.5 hover:bg-gray-100 rounded-md"
                      title="Duplicate"
                    >
                      <Copy size={16} className="text-gray-500" />
                    </button>
                    <button
                      onClick={onOpenApiConfig}
                      className="p-1.5 hover:bg-gray-100 rounded-md"
                      title="Configure API"
                    >
                      <Settings size={16} className="text-gray-500" />
                    </button>
                    {onOpenAssetImport && (
                      <button
                        onClick={(e) => { e.stopPropagation(); onOpenAssetImport(); }}
                        className="p-1.5 hover:bg-blue-50 rounded-md"
                        title="Import assets"
                      >
                        <Upload size={16} className="text-gray-500" />
                      </button>
                    )}
                    {onOpenSbomConfig && (
                      <button
                        onClick={(e) => { e.stopPropagation(); onOpenSbomConfig(); }}
                        className="p-1.5 hover:bg-purple-50 rounded-md"
                        title="SBOM"
                      >
                        <Package size={16} className="text-gray-500" />
                      </button>
                    )}
                    {onOpenWebhookConfig && (
                      <button
                        onClick={(e) => { e.stopPropagation(); onOpenWebhookConfig(); }}
                        className="p-1.5 hover:bg-orange-50 rounded-md"
                        title="Outgoing webhooks"
                      >
                        <Bell size={16} className="text-gray-500" />
                      </button>
                    )}
                    {onOpenIngestConfig && (
                      <button
                        onClick={(e) => { e.stopPropagation(); onOpenIngestConfig(); }}
                        className="p-1.5 hover:bg-green-50 rounded-md"
                        title="Incoming webhooks"
                      >
                        <Download size={16} className="text-gray-500" />
                      </button>
                    )}
                    {!isDefault && (
                      <>
                        <button
                          onClick={handleSetDefault}
                          className="p-1.5 hover:bg-yellow-50 rounded-md"
                          title="Set as default"
                        >
                          <StarOff size={16} className="text-gray-500" />
                        </button>
                        <button
                          onClick={handleDelete}
                          className="p-1.5 hover:bg-red-50 rounded-md ml-auto"
                          title="Delete"
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
            <p className="text-sm">No trees</p>
            <button
              onClick={onOpenCreateDialog}
              className="text-blue-500 hover:underline text-sm mt-2"
            >
              Create a tree
            </button>
          </div>
        )}
      </div>

      {/* User section (bottom of sidebar) */}
      {currentUser && (
        <div className="border-t p-3 space-y-2">
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium text-gray-800 truncate">
              {currentUser.username}
            </span>
            <span
              className={`text-xs px-1.5 py-0.5 rounded font-medium ${
                currentUser.role === 'admin'
                  ? 'bg-blue-100 text-blue-700'
                  : 'bg-gray-100 text-gray-600'
              }`}
            >
              {currentUser.role}
            </span>
          </div>
          <div className="flex flex-col gap-1">
            <button
              onClick={() => setShowChangePassword(true)}
              className="flex items-center gap-2 text-sm text-gray-600 hover:text-gray-800 hover:bg-gray-50 rounded px-2 py-1 w-full text-left"
            >
              <KeyRound size={14} />
              Change password
            </button>
            {isAdmin() && (
              <button
                onClick={() => setShowUsersPanel(true)}
                className="flex items-center gap-2 text-sm text-gray-600 hover:text-gray-800 hover:bg-gray-50 rounded px-2 py-1 w-full text-left"
              >
                <Users size={14} />
                Users
              </button>
            )}
            <button
              onClick={handleLogout}
              className="flex items-center gap-2 text-sm text-red-500 hover:text-red-700 hover:bg-red-50 rounded px-2 py-1 w-full text-left"
            >
              <LogOut size={14} />
              Sign out
            </button>
          </div>
        </div>
      )}

      <ConfirmDialog {...confirmDialogProps} />

      {/* Password change modal */}
      {showChangePassword && (
        <ChangePasswordDialog
          onComplete={() => setShowChangePassword(false)}
          onClose={() => setShowChangePassword(false)}
        />
      )}

      {/* User management modal (admin only) */}
      {showUsersPanel && (
        <UsersPanel onClose={() => setShowUsersPanel(false)} />
      )}
    </div>
  );
}

export default TreeSidebar;
