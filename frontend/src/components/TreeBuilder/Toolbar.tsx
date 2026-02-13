import { Save, Upload, Download, RotateCcw, Play, Settings2, PanelLeftClose, PanelLeft, Star, Link } from 'lucide-react';
import { useTreeStore } from '@/stores/treeStore';
import { useState } from 'react';

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

  const [saveComment, setSaveComment] = useState('');
  const [showSaveDialog, setShowSaveDialog] = useState(false);

  const handleSave = async () => {
    if (hasUnsavedChanges) {
      setShowSaveDialog(true);
    }
  };

  const confirmSave = async () => {
    try {
      await saveTree(saveComment || undefined);
      setShowSaveDialog(false);
      setSaveComment('');
    } catch {
      // Error handled in store
    }
  };

  const handleExport = () => {
    const structure = useTreeStore.getState().toApiStructure();
    const blob = new Blob([JSON.stringify(structure, null, 2)], {
      type: 'application/json',
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${treeName.replace(/\s+/g, '_')}_tree.json`;
    a.click();
    URL.revokeObjectURL(url);
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
        const structure = JSON.parse(text);
        useTreeStore.getState().fromApiStructure(structure);
      } catch {
        alert('Erreur lors de l\'import du fichier');
      }
    };
    input.click();
  };

  return (
    <>
      <div className="bg-white border-b px-4 py-2 flex items-center justify-between">
        <div className="flex items-center gap-4">
          {/* Toggle sidebar */}
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="p-2 text-gray-600 hover:bg-gray-100 rounded-md"
            title={sidebarOpen ? 'Fermer le panneau' : 'Ouvrir le panneau des arbres'}
          >
            {sidebarOpen ? <PanelLeftClose size={20} /> : <PanelLeft size={20} />}
          </button>

          <div className="flex items-center gap-2">
            <h1 className="text-lg font-bold text-gray-800">{treeName}</h1>
            {isDefault && (
              <span title="Arbre par défaut">
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
              Non sauvegardé
            </span>
          )}
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => loadTree()}
            className="p-2 text-gray-600 hover:bg-gray-100 rounded-md"
            title="Recharger"
          >
            <RotateCcw size={20} />
          </button>

          <button
            onClick={handleImport}
            className="p-2 text-gray-600 hover:bg-gray-100 rounded-md"
            title="Importer JSON"
          >
            <Upload size={20} />
          </button>

          <button
            onClick={handleExport}
            className="p-2 text-gray-600 hover:bg-gray-100 rounded-md"
            title="Exporter JSON"
          >
            <Download size={20} />
          </button>

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
            title={fieldMapping ? `Mapping: ${fieldMapping.fields.length} champs` : 'Configurer le mapping des champs'}
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
            title="Tester l'arbre"
          >
            <Play size={18} />
            <span className="text-sm font-medium">Tester</span>
          </button>

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
            title="Sauvegarder (Ctrl+S)"
          >
            <Save size={18} />
            {isSaving ? 'Sauvegarde...' : 'Sauvegarder'}
          </button>
        </div>
      </div>

      {/* Dialog de sauvegarde */}
      {showSaveDialog && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl p-6 w-96">
            <h3 className="text-lg font-bold mb-4">Sauvegarder l'arbre</h3>
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Commentaire de version (optionnel)
              </label>
              <input
                type="text"
                value={saveComment}
                onChange={(e) => setSaveComment(e.target.value)}
                placeholder="Ex: Ajout condition KEV"
                className="w-full px-3 py-2 border rounded-md"
              />
            </div>
            <div className="flex justify-end gap-2">
              <button
                onClick={() => setShowSaveDialog(false)}
                className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-md"
              >
                Annuler
              </button>
              <button
                onClick={confirmSave}
                disabled={isSaving}
                className="px-4 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600"
              >
                {isSaving ? 'Sauvegarde...' : 'Sauvegarder'}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
