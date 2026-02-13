import { useState } from 'react';
import {
  X,
  Plus,
  Trash2,
  Upload,
  FileSearch,
  Save,
  ChevronDown,
  ChevronRight,
  AlertCircle,
  CheckCircle2,
} from 'lucide-react';
import { useTreeStore } from '@/stores/treeStore';
import { fieldMappingApi } from '@/api';
import { useConfirm } from '@/hooks/useConfirm';
import { ConfirmDialog } from '@/components/ui/ConfirmDialog';
import type { FieldDefinition, FieldType, ScanResult } from '@/types';
import { FIELD_TYPE_LABELS } from '@/types';
import { FieldScanDialog } from './FieldScanDialog';

interface FieldMappingPanelProps {
  onClose: () => void;
}

export function FieldMappingPanel({ onClose }: FieldMappingPanelProps) {
  const fieldMapping = useTreeStore((state) => state.fieldMapping);
  const saveFieldMapping = useTreeStore((state) => state.saveFieldMapping);
  const deleteFieldMapping = useTreeStore((state) => state.deleteFieldMapping);
  const treeId = useTreeStore((state) => state.treeId);

  const [fields, setFields] = useState<FieldDefinition[]>(
    fieldMapping?.fields || []
  );
  const [expandedField, setExpandedField] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [showScanDialog, setShowScanDialog] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const { confirm, confirmDialogProps } = useConfirm();

  const hasChanges =
    JSON.stringify(fields) !== JSON.stringify(fieldMapping?.fields || []);

  const handleSave = async () => {
    if (!treeId) return;
    setIsSaving(true);
    setError(null);

    try {
      await saveFieldMapping(fields);
      setSuccess('Mapping sauvegardé');
      setTimeout(() => setSuccess(null), 2000);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erreur de sauvegarde');
    } finally {
      setIsSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!treeId) return;
    const ok = await confirm('Supprimer le mapping', 'Supprimer le mapping des champs ? Les nœuds conserveront leurs configurations.', 'warning');
    if (!ok) return;

    try {
      await deleteFieldMapping();
      setFields([]);
      setSuccess('Mapping supprimé');
      setTimeout(() => setSuccess(null), 2000);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erreur de suppression');
    }
  };

  const addField = () => {
    const newField: FieldDefinition = {
      name: `field_${fields.length + 1}`,
      label: `Champ ${fields.length + 1}`,
      type: 'string',
      description: '',
      examples: [],
      required: false,
    };
    setFields([...fields, newField]);
    setExpandedField(newField.name);
  };

  const updateField = (index: number, updates: Partial<FieldDefinition>) => {
    const newFields = [...fields];
    newFields[index] = { ...newFields[index], ...updates };
    setFields(newFields);
  };

  const removeField = (index: number) => {
    setFields(fields.filter((_, i) => i !== index));
  };

  const handleImportJson = () => {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.json';
    input.onchange = async (e) => {
      const file = (e.target as HTMLInputElement).files?.[0];
      if (!file || !treeId) return;

      try {
        const mapping = await fieldMappingApi.importMapping(treeId, file);
        setFields(mapping.fields);
        setSuccess(`${mapping.fields.length} champs importés`);
        setTimeout(() => setSuccess(null), 2000);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Erreur d\'import');
      }
    };
    input.click();
  };

  const handleScanResult = (result: ScanResult) => {
    setFields(result.fields);
    setShowScanDialog(false);
    setSuccess(`${result.fields.length} champs détectés (${result.rows_scanned} lignes analysées)`);
    setTimeout(() => setSuccess(null), 3000);
  };

  return (
    <>
      <div className="bg-white rounded-lg shadow-xl w-[480px] max-h-[80vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b">
          <div>
            <h3 className="font-bold text-gray-800">Mapping des champs</h3>
            <p className="text-xs text-gray-500 mt-0.5">
              {fieldMapping
                ? `Version ${fieldMapping.version} • ${fieldMapping.fields.length} champs`
                : 'Aucun mapping configuré'}
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-1 hover:bg-gray-100 rounded"
          >
            <X size={20} />
          </button>
        </div>

        {/* Info mapping existant */}
        {fieldMapping && fieldMapping.fields.length > 0 && (
          <div className="mx-4 mt-4 p-3 bg-blue-50 rounded-md">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium text-blue-800">Mapping actuel</span>
              {fieldMapping.source && (
                <span className="text-xs text-blue-600 bg-blue-100 px-2 py-0.5 rounded">
                  {fieldMapping.source}
                </span>
              )}
            </div>
            <div className="flex flex-wrap gap-1">
              {fieldMapping.fields.slice(0, 8).map((f) => (
                <span
                  key={f.name}
                  className="text-xs bg-white text-blue-700 px-2 py-0.5 rounded border border-blue-200"
                >
                  {f.label || f.name}
                </span>
              ))}
              {fieldMapping.fields.length > 8 && (
                <span className="text-xs text-blue-600 px-2 py-0.5">
                  +{fieldMapping.fields.length - 8} autres
                </span>
              )}
            </div>
          </div>
        )}

        {/* Actions */}
        <div className="flex items-center gap-2 p-4 border-b bg-gray-50">
          <button
            onClick={() => setShowScanDialog(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 text-sm bg-blue-500 text-white rounded-md hover:bg-blue-600"
          >
            <FileSearch size={16} />
            Scanner fichier
          </button>
          <button
            onClick={handleImportJson}
            className="flex items-center gap-1.5 px-3 py-1.5 text-sm border rounded-md hover:bg-gray-100"
          >
            <Upload size={16} />
            Importer JSON
          </button>
          <button
            onClick={addField}
            className="flex items-center gap-1.5 px-3 py-1.5 text-sm border rounded-md hover:bg-gray-100"
          >
            <Plus size={16} />
            Ajouter
          </button>
        </div>

        {/* Messages */}
        {error && (
          <div className="mx-4 mt-4 p-3 bg-red-50 text-red-700 text-sm rounded-md flex items-center gap-2">
            <AlertCircle size={16} />
            {error}
          </div>
        )}
        {success && (
          <div className="mx-4 mt-4 p-3 bg-green-50 text-green-700 text-sm rounded-md flex items-center gap-2">
            <CheckCircle2 size={16} />
            {success}
          </div>
        )}

        {/* Liste des champs */}
        <div className="flex-1 overflow-y-auto p-4">
          {fields.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              <FileSearch size={48} className="mx-auto mb-3 opacity-50" />
              <p className="font-medium">Aucun champ configuré</p>
              <p className="text-sm mt-1">
                Scannez un fichier CSV/JSON ou ajoutez des champs manuellement
              </p>
            </div>
          ) : (
            <div className="space-y-2">
              {fields.map((field, index) => (
                <FieldEditor
                  key={`${field.name}-${index}`}
                  field={field}
                  isExpanded={expandedField === field.name}
                  onToggle={() =>
                    setExpandedField(
                      expandedField === field.name ? null : field.name
                    )
                  }
                  onChange={(updates) => updateField(index, updates)}
                  onRemove={() => removeField(index)}
                />
              ))}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between p-4 border-t bg-gray-50">
          <button
            onClick={handleDelete}
            disabled={!fieldMapping}
            className="text-red-500 hover:text-red-700 text-sm disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Supprimer le mapping
          </button>
          <button
            onClick={handleSave}
            disabled={!hasChanges || isSaving}
            className={`
              flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium
              ${
                hasChanges
                  ? 'bg-blue-500 text-white hover:bg-blue-600'
                  : 'bg-gray-200 text-gray-500 cursor-not-allowed'
              }
            `}
          >
            <Save size={16} />
            {isSaving ? 'Sauvegarde...' : 'Sauvegarder'}
          </button>
        </div>
      </div>

      {/* Dialog de scan */}
      {showScanDialog && (
        <FieldScanDialog
          onClose={() => setShowScanDialog(false)}
          onResult={handleScanResult}
        />
      )}
      <ConfirmDialog {...confirmDialogProps} />
    </>
  );
}

interface FieldEditorProps {
  field: FieldDefinition;
  isExpanded: boolean;
  onToggle: () => void;
  onChange: (updates: Partial<FieldDefinition>) => void;
  onRemove: () => void;
}

function FieldEditor({
  field,
  isExpanded,
  onToggle,
  onChange,
  onRemove,
}: FieldEditorProps) {
  return (
    <div className="border rounded-md overflow-hidden">
      {/* Header */}
      <div
        className="flex items-center gap-2 p-3 bg-gray-50 cursor-pointer hover:bg-gray-100"
        onClick={onToggle}
      >
        {isExpanded ? (
          <ChevronDown size={16} className="text-gray-500" />
        ) : (
          <ChevronRight size={16} className="text-gray-500" />
        )}
        <span className="font-medium text-gray-800 flex-1">
          {field.label || field.name}
        </span>
        <span className="text-xs text-gray-500 bg-gray-200 px-2 py-0.5 rounded">
          {FIELD_TYPE_LABELS[field.type]}
        </span>
        {field.required && (
          <span className="text-xs text-blue-600 bg-blue-50 px-2 py-0.5 rounded">
            Requis
          </span>
        )}
        <button
          onClick={(e) => {
            e.stopPropagation();
            onRemove();
          }}
          className="p-1 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded"
        >
          <Trash2 size={14} />
        </button>
      </div>

      {/* Détails */}
      {isExpanded && (
        <div className="p-3 space-y-3 bg-white">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">
                Nom technique
              </label>
              <input
                type="text"
                value={field.name}
                onChange={(e) => onChange({ name: e.target.value })}
                className="w-full px-2 py-1.5 text-sm border rounded"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">
                Label affiché
              </label>
              <input
                type="text"
                value={field.label || ''}
                onChange={(e) => onChange({ label: e.target.value })}
                className="w-full px-2 py-1.5 text-sm border rounded"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">
                Type
              </label>
              <select
                value={field.type}
                onChange={(e) => onChange({ type: e.target.value as FieldType })}
                className="w-full px-2 py-1.5 text-sm border rounded bg-white"
              >
                {Object.entries(FIELD_TYPE_LABELS).map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </select>
            </div>
            <div className="flex items-end">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={field.required}
                  onChange={(e) => onChange({ required: e.target.checked })}
                  className="w-4 h-4 text-blue-500 rounded"
                />
                <span className="text-sm text-gray-700">Champ requis</span>
              </label>
            </div>
          </div>

          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">
              Description
            </label>
            <input
              type="text"
              value={field.description || ''}
              onChange={(e) => onChange({ description: e.target.value })}
              placeholder="Description du champ..."
              className="w-full px-2 py-1.5 text-sm border rounded"
            />
          </div>

          {field.examples.length > 0 && (
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">
                Exemples
              </label>
              <div className="flex flex-wrap gap-1">
                {field.examples.slice(0, 5).map((ex, i) => (
                  <span
                    key={i}
                    className="px-2 py-0.5 bg-gray-100 text-gray-700 text-xs rounded"
                  >
                    {String(ex)}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
