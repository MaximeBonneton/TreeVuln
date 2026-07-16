import { Save, Upload, Download, RotateCcw, Play, Settings2, PanelLeftClose, PanelLeft, Star, Link, LayoutGrid, Image } from 'lucide-react';
import { useTreeStore } from '@/stores/treeStore';
import { treeApi } from '@/api';
import { useState } from 'react';
import { toPng, toSvg } from 'html-to-image';
import type { TreeExportFile } from '@/types';
import { useConfirm } from '@/hooks/useConfirm';
import { ConfirmDialog } from '@/components/ui/ConfirmDialog';

interface ToolbarProps {
  onTest?: () => void;
  onOpenMapping?: () => void;
}

export function Toolbar({ onTest, onOpenMapping }: ToolbarProps) {
  const {
    treeName,
    hasUnsavedChanges,
    isSaving,
    saveTree,
    loadTree,
    fieldMapping,
    isDefault,
    apiEnabled,
    apiSlug,
    sidebarOpen,
    setSidebarOpen,
  } = useTreeStore();

  const isAdminUser = useTreeStore((s) => s.isAdmin);
  const { confirm, confirmDialogProps } = useConfirm();

  const [saveComment, setSaveComment] = useState('');
  const [showSaveDialog, setShowSaveDialog] = useState(false);

  // F-1 : recharge l'arbre COURANT (loadTree() sans argument charge l'arbre
  // par défaut) et demande confirmation si des changements seraient perdus.
  const handleReload = async () => {
    const { treeId } = useTreeStore.getState();
    if (hasUnsavedChanges) {
      const ok = await confirm(
        'Reload tree',
        'You have unsaved changes. Reloading will discard them. Continue?',
        'warning'
      );
      if (!ok) return;
    }
    await loadTree(treeId ?? undefined);
  };

  const handleSave = async () => {
    if (hasUnsavedChanges) {
      setShowSaveDialog(true);
    }
  };

  const confirmSave = async () => {
    try {
      await saveTree(saveComment || undefined);
      await useTreeStore.getState().loadTrees();
      setShowSaveDialog(false);
      setSaveComment('');
    } catch {
      // Error handled in store
    }
  };

  const handleExport = async () => {
    const { treeId } = useTreeStore.getState();
    if (!treeId) return;
    try {
      await treeApi.exportTree(treeId);
    } catch {
      alert('Export error');
    }
  };

  const handleImport = () => {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.json';
    input.onchange = async (e) => {
      const file = (e.target as HTMLInputElement).files?.[0];
      if (!file) return;

      try {
        const text = await file.text();
        const data = JSON.parse(text) as TreeExportFile;
        const newTree = await treeApi.importTree(data);
        // Navigate to the imported tree
        await useTreeStore.getState().loadTrees();
        await useTreeStore.getState().selectTree(newTree.id);
      } catch {
        alert('File import error');
      }
    };
    input.click();
  };

  const [showImageMenu, setShowImageMenu] = useState(false);

  const handleExportImage = async (format: 'png' | 'svg') => {
    setShowImageMenu(false);
    const viewport = document.querySelector('.react-flow__viewport') as HTMLElement;
    if (!viewport) return;

    try {
      const options = {
        backgroundColor: '#f9fafb',
        style: { transform: '' }, // Reset transform to capture everything
      };

      let dataUrl: string;
      let extension: string;
      if (format === 'svg') {
        dataUrl = await toSvg(viewport, options);
        extension = 'svg';
      } else {
        dataUrl = await toPng(viewport, { ...options, pixelRatio: 2 });
        extension = 'png';
      }

      const a = document.createElement('a');
      a.href = dataUrl;
      a.download = `${treeName.replace(/\s+/g, '_')}_tree.${extension}`;
      a.click();
    } catch {
      alert('Image export error');
    }
  };

  return (
    <>
      <div className="bg-white border-b px-4 py-2 flex items-center justify-between">
        <div className="flex items-center gap-4">
          {/* Toggle sidebar */}
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="p-2 text-gray-600 hover:bg-gray-100 rounded-md"
            title={sidebarOpen ? 'Close panel' : 'Open tree panel'}
          >
            {sidebarOpen ? <PanelLeftClose size={20} /> : <PanelLeft size={20} />}
          </button>

          <div className="flex items-center gap-2">
            <h1 className="text-lg font-bold text-gray-800">{treeName}</h1>
            {isDefault && (
              <span title="Default tree">
                <Star size={16} className="text-yellow-500 fill-yellow-500" />
              </span>
            )}
            {apiEnabled && apiSlug && (
              <span className="flex items-center gap-1 text-xs text-green-600 bg-green-50 px-2 py-0.5 rounded" title={`API: /evaluate/tree/${apiSlug}`}>
                <Link size={12} />
                {apiSlug}
              </span>
            )}
          </div>
          {hasUnsavedChanges && (
            <span className="text-xs text-orange-500 bg-orange-50 px-2 py-1 rounded">
              Unsaved
            </span>
          )}
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={handleReload}
            className="p-2 text-gray-600 hover:bg-gray-100 rounded-md"
            title="Reload"
          >
            <RotateCcw size={20} />
          </button>

          {isAdminUser() && (
            <button
              onClick={handleImport}
              className="p-2 text-gray-600 hover:bg-gray-100 rounded-md"
              title="Import JSON"
            >
              <Upload size={20} />
            </button>
          )}

          <button
            onClick={handleExport}
            className="p-2 text-gray-600 hover:bg-gray-100 rounded-md"
            title="Export JSON"
          >
            <Download size={20} />
          </button>

          <button
            onClick={() => useTreeStore.getState().autoLayout()}
            className="p-2 text-gray-600 hover:bg-gray-100 rounded-md"
            title="Auto-layout nodes"
          >
            <LayoutGrid size={20} />
          </button>

          <div className="relative">
            <button
              onClick={() => setShowImageMenu(!showImageMenu)}
              className="p-2 text-gray-600 hover:bg-gray-100 rounded-md"
              title="Export as image"
            >
              <Image size={20} />
            </button>
            {showImageMenu && (
              <div className="absolute right-0 top-full mt-1 bg-white border rounded-lg shadow-lg py-1 z-50">
                <button
                  onClick={() => handleExportImage('png')}
                  className="w-full px-4 py-2 text-sm text-left hover:bg-gray-100"
                >
                  Export as PNG
                </button>
                <button
                  onClick={() => handleExportImage('svg')}
                  className="w-full px-4 py-2 text-sm text-left hover:bg-gray-100"
                >
                  Export as SVG
                </button>
              </div>
            )}
          </div>

          <div className="w-px h-6 bg-gray-300 mx-2" />

          <button
            onClick={onOpenMapping}
            className={`
              flex items-center gap-2 px-3 py-2 rounded-md
              ${
                fieldMapping
                  ? 'text-green-600 bg-green-50 hover:bg-green-100'
                  : 'text-gray-600 hover:bg-gray-100'
              }
            `}
            title={fieldMapping ? `Mapping: ${fieldMapping.fields.length} fields` : 'Configure field mapping'}
          >
            <Settings2 size={18} />
            <span className="text-sm font-medium">Mapping</span>
            {fieldMapping && (
              <span className="text-xs bg-green-200 text-green-700 px-1.5 py-0.5 rounded">
                {fieldMapping.fields.length}
              </span>
            )}
          </button>

          <button
            onClick={onTest}
            className="flex items-center gap-2 px-3 py-2 text-purple-600 bg-purple-50 hover:bg-purple-100 rounded-md"
            title="Test tree"
          >
            <Play size={18} />
            <span className="text-sm font-medium">Test</span>
          </button>

          {isAdminUser() && (
            <button
              onClick={handleSave}
              disabled={!hasUnsavedChanges || isSaving}
              className={`
                flex items-center gap-2 px-4 py-2 rounded-md font-medium text-sm
                ${
                  hasUnsavedChanges
                    ? 'bg-blue-500 text-white hover:bg-blue-600'
                    : 'bg-gray-100 text-gray-400 cursor-not-allowed'
                }
              `}
              title="Save (Ctrl+S)"
            >
              <Save size={18} />
              {isSaving ? 'Saving...' : 'Save'}
            </button>
          )}
        </div>
      </div>

      {/* Save dialog */}
      {showSaveDialog && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl p-6 w-96">
            <h3 className="text-lg font-bold mb-4">Save tree</h3>
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Version comment (optional)
              </label>
              <input
                type="text"
                value={saveComment}
                onChange={(e) => setSaveComment(e.target.value)}
                placeholder="E.g.: Add KEV condition"
                className="w-full px-3 py-2 border rounded-md"
              />
            </div>
            <div className="flex justify-end gap-2">
              <button
                onClick={() => setShowSaveDialog(false)}
                className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-md"
              >
                Cancel
              </button>
              <button
                onClick={confirmSave}
                disabled={isSaving}
                className="px-4 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600"
              >
                {isSaving ? 'Saving...' : 'Save'}
              </button>
            </div>
          </div>
        </div>
      )}

      <ConfirmDialog {...confirmDialogProps} />
    </>
  );
}
