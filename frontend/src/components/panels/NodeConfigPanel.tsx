import { useState } from 'react';
import { X, Plus, Trash2, Copy } from 'lucide-react';
import { useTreeStore } from '@/stores/treeStore';
import { useConfirm } from '@/hooks/useConfirm';
import { ConfirmDialog } from '@/components/ui/ConfirmDialog';
import type {
  TreeNode,
  NodeCondition,
  InputNodeConfig,
  LookupNodeConfig,
  OutputNodeConfig,
} from '@/types';
import {
  ConditionEditor,
  InputConfig,
  LookupConfig,
  OutputConfig,
} from './nodeConfig';

interface NodeConfigPanelProps {
  node: TreeNode;
  onClose: () => void;
}

export function NodeConfigPanel({ node, onClose }: NodeConfigPanelProps) {
  const updateNodeData = useTreeStore((state) => state.updateNodeData);
  const deleteNode = useTreeStore((state) => state.deleteNode);
  const duplicateNode = useTreeStore((state) => state.duplicateNode);
  const fieldMapping = useTreeStore((state) => state.fieldMapping);
  const { confirm, confirmDialogProps } = useConfirm();

  const [label, setLabel] = useState(node.data.label);
  const [config, setConfig] = useState(node.data.config);
  const [conditions, setConditions] = useState<NodeCondition[]>(
    node.data.conditions
  );

  const handleSave = () => {
    updateNodeData(node.id, { label, config, conditions });
  };

  const handleDelete = async () => {
    const ok = await confirm('Supprimer le nœud', 'Supprimer ce nœud et toutes ses connexions ?');
    if (ok) {
      deleteNode(node.id);
      onClose();
    }
  };

  const handleDuplicate = () => {
    duplicateNode(node.id);
  };

  const addCondition = () => {
    setConditions([
      ...conditions,
      { operator: 'eq', value: '', label: `Condition ${conditions.length + 1}` },
    ]);
  };

  const updateCondition = (
    index: number,
    field: keyof NodeCondition,
    value: unknown
  ) => {
    const newConditions = [...conditions];
    newConditions[index] = { ...newConditions[index], [field]: value };
    setConditions(newConditions);
  };

  const removeCondition = (index: number) => {
    setConditions(conditions.filter((_, i) => i !== index));
  };

  const moveCondition = (index: number, direction: 'up' | 'down') => {
    const newIndex = direction === 'up' ? index - 1 : index + 1;
    if (newIndex < 0 || newIndex >= conditions.length) return;

    const newConditions = [...conditions];
    [newConditions[index], newConditions[newIndex]] = [newConditions[newIndex], newConditions[index]];
    setConditions(newConditions);
  };

  return (
    <div className="bg-white rounded-lg shadow-lg w-80 max-h-[calc(100vh-100px)] overflow-y-auto">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b sticky top-0 bg-white">
        <div>
          <h3 className="font-bold text-gray-700">Configuration</h3>
          <p className="text-xs text-gray-400 font-mono">{node.id}</p>
        </div>
        <button
          onClick={onClose}
          className="p-1 hover:bg-gray-100 rounded"
        >
          <X size={20} />
        </button>
      </div>

      <div className="p-4 space-y-4">
        {/* Label */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Label
          </label>
          <input
            type="text"
            value={label}
            onChange={(e) => setLabel(e.target.value)}
            className="w-full px-3 py-2 border rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          />
        </div>

        {/* Config selon le type */}
        {node.data.nodeType === 'input' && (
          <InputConfig
            config={config as InputNodeConfig}
            onChange={setConfig}
            fieldMapping={fieldMapping}
          />
        )}

        {node.data.nodeType === 'lookup' && (
          <LookupConfig
            config={config as LookupNodeConfig}
            onChange={setConfig}
          />
        )}

        {node.data.nodeType === 'output' && (
          <OutputConfig
            config={config as OutputNodeConfig}
            onChange={setConfig}
          />
        )}

        {/* Conditions (sauf pour output) */}
        {node.data.nodeType !== 'output' && (
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="block text-sm font-medium text-gray-700">
                Conditions de sortie
              </label>
              <button
                onClick={addCondition}
                className="text-blue-500 hover:text-blue-700 text-sm flex items-center gap-1"
              >
                <Plus size={16} />
                Ajouter
              </button>
            </div>

            <div className="space-y-3">
              {conditions.map((condition, index) => (
                <ConditionEditor
                  key={index}
                  condition={condition}
                  index={index}
                  total={conditions.length}
                  onChange={updateCondition}
                  onRemove={removeCondition}
                  onMove={moveCondition}
                />
              ))}

              {conditions.length === 0 && (
                <p className="text-xs text-gray-500 italic">
                  Aucune condition. Ajoutez des conditions pour créer des branches.
                </p>
              )}
            </div>
          </div>
        )}

        {/* Actions */}
        <div className="flex gap-2 pt-4 border-t">
          <button
            onClick={handleSave}
            className="flex-1 bg-blue-500 text-white py-2 rounded-md hover:bg-blue-600 font-medium"
          >
            Appliquer
          </button>
          <button
            onClick={handleDuplicate}
            className="p-2 text-gray-500 hover:bg-gray-100 rounded-md"
            title="Dupliquer le nœud"
          >
            <Copy size={20} />
          </button>
          <button
            onClick={handleDelete}
            className="p-2 text-red-500 hover:bg-red-50 rounded-md"
            title="Supprimer le nœud"
          >
            <Trash2 size={20} />
          </button>
        </div>
      </div>
      <ConfirmDialog {...confirmDialogProps} />
    </div>
  );
}
