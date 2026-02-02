import { useState } from 'react';
import { X, Plus, Trash2, Copy, AlertCircle, ChevronUp, ChevronDown } from 'lucide-react';
import { useTreeStore } from '@/stores/treeStore';
import type {
  TreeNode,
  NodeCondition,
  ConditionOperator,
  InputNodeConfig,
  LookupNodeConfig,
  OutputNodeConfig,
  FieldMapping,
} from '@/types';

const OPERATORS: { value: ConditionOperator; label: string }[] = [
  { value: 'eq', label: '=' },
  { value: 'neq', label: '≠' },
  { value: 'gt', label: '>' },
  { value: 'gte', label: '≥' },
  { value: 'lt', label: '<' },
  { value: 'lte', label: '≤' },
  { value: 'contains', label: 'contient' },
  { value: 'not_contains', label: 'ne contient pas' },
  { value: 'regex', label: 'regex' },
  { value: 'in', label: 'dans liste' },
  { value: 'not_in', label: 'pas dans liste' },
  { value: 'is_null', label: 'est vide' },
  { value: 'is_not_null', label: "n'est pas vide" },
];

const SSVC_DECISIONS = [
  { value: 'Act', color: '#dc2626' },
  { value: 'Attend', color: '#f97316' },
  { value: 'Track*', color: '#eab308' },
  { value: 'Track', color: '#22c55e' },
];

interface NodeConfigPanelProps {
  node: TreeNode;
  onClose: () => void;
}

export function NodeConfigPanel({ node, onClose }: NodeConfigPanelProps) {
  const updateNodeData = useTreeStore((state) => state.updateNodeData);
  const deleteNode = useTreeStore((state) => state.deleteNode);
  const duplicateNode = useTreeStore((state) => state.duplicateNode);
  const fieldMapping = useTreeStore((state) => state.fieldMapping);

  const [label, setLabel] = useState(node.data.label);
  const [config, setConfig] = useState(node.data.config);
  const [conditions, setConditions] = useState<NodeCondition[]>(
    node.data.conditions
  );

  const handleSave = () => {
    updateNodeData(node.id, { label, config, conditions });
  };

  const handleDelete = () => {
    if (confirm('Supprimer ce nœud ?')) {
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
    </div>
  );
}

// Sous-composants pour la configuration

function InputConfig({
  config,
  onChange,
  fieldMapping,
}: {
  config: InputNodeConfig;
  onChange: (c: InputNodeConfig) => void;
  fieldMapping: FieldMapping | null;
}) {
  const hasMapping = fieldMapping && fieldMapping.fields.length > 0;

  // Vérifie si le champ actuel existe dans le mapping
  const currentFieldInMapping = hasMapping
    ? fieldMapping.fields.find((f) => f.name === config.field)
    : null;
  const showWarning = hasMapping && config.field && !currentFieldInMapping;

  return (
    <div>
      <label className="block text-sm font-medium text-gray-700 mb-1">
        Champ à lire
      </label>

      {hasMapping ? (
        <>
          <select
            value={config.field}
            onChange={(e) => onChange({ ...config, field: e.target.value })}
            className="w-full px-3 py-2 border rounded-md focus:ring-2 focus:ring-blue-500 bg-white"
          >
            <option value="">-- Sélectionner un champ --</option>
            {fieldMapping.fields.map((field) => (
              <option key={field.name} value={field.name}>
                {field.label || field.name}
                {field.type !== 'unknown' && ` (${field.type})`}
              </option>
            ))}
          </select>

          {currentFieldInMapping && (
            <div className="mt-2 text-xs text-gray-500">
              <p className="font-medium">{currentFieldInMapping.label || currentFieldInMapping.name}</p>
              {currentFieldInMapping.description && (
                <p className="mt-0.5">{currentFieldInMapping.description}</p>
              )}
              {currentFieldInMapping.examples.length > 0 && (
                <p className="mt-0.5">
                  Exemples: {currentFieldInMapping.examples.slice(0, 3).map(String).join(', ')}
                </p>
              )}
            </div>
          )}

          {showWarning && (
            <div className="mt-2 flex items-start gap-1 text-xs text-amber-600">
              <AlertCircle size={14} className="mt-0.5 flex-shrink-0" />
              <span>
                Le champ "{config.field}" n'existe pas dans le mapping actuel.
              </span>
            </div>
          )}
        </>
      ) : (
        <>
          <input
            type="text"
            value={config.field}
            onChange={(e) => onChange({ ...config, field: e.target.value })}
            placeholder="ex: cvss_score, epss_score, kev"
            className="w-full px-3 py-2 border rounded-md focus:ring-2 focus:ring-blue-500"
          />
          <p className="text-xs text-gray-500 mt-1">
            Champs standards: cvss_score, epss_score, kev, asset_id, cve_id
          </p>
        </>
      )}
    </div>
  );
}

function LookupConfig({
  config,
  onChange,
}: {
  config: LookupNodeConfig;
  onChange: (c: LookupNodeConfig) => void;
}) {
  return (
    <div className="space-y-3">
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Table de lookup
        </label>
        <input
          type="text"
          value={config.lookup_table || ''}
          onChange={(e) =>
            onChange({ ...config, lookup_table: e.target.value })
          }
          placeholder="ex: assets"
          className="w-full px-3 py-2 border rounded-md"
        />
      </div>
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Clé de recherche
        </label>
        <input
          type="text"
          value={config.lookup_key || ''}
          onChange={(e) =>
            onChange({ ...config, lookup_key: e.target.value })
          }
          placeholder="ex: asset_id"
          className="w-full px-3 py-2 border rounded-md"
        />
      </div>
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Champ à retourner
        </label>
        <input
          type="text"
          value={config.lookup_field || ''}
          onChange={(e) =>
            onChange({ ...config, lookup_field: e.target.value })
          }
          placeholder="ex: criticality"
          className="w-full px-3 py-2 border rounded-md"
        />
      </div>
    </div>
  );
}

function OutputConfig({
  config,
  onChange,
}: {
  config: OutputNodeConfig;
  onChange: (c: OutputNodeConfig) => void;
}) {
  return (
    <div className="space-y-3">
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Décision SSVC
        </label>
        <div className="grid grid-cols-2 gap-2">
          {SSVC_DECISIONS.map((decision) => (
            <button
              key={decision.value}
              onClick={() =>
                onChange({ decision: decision.value, color: decision.color })
              }
              className={`
                p-2 rounded-md border-2 text-sm font-medium transition-all
                ${
                  config.decision === decision.value
                    ? 'border-gray-800 shadow-md'
                    : 'border-transparent'
                }
              `}
              style={{ backgroundColor: decision.color, color: 'white' }}
            >
              {decision.value}
            </button>
          ))}
        </div>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Ou décision personnalisée
        </label>
        <input
          type="text"
          value={config.decision}
          onChange={(e) => onChange({ ...config, decision: e.target.value })}
          className="w-full px-3 py-2 border rounded-md"
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Couleur
        </label>
        <input
          type="color"
          value={config.color}
          onChange={(e) => onChange({ ...config, color: e.target.value })}
          className="w-full h-10 rounded-md cursor-pointer"
        />
      </div>
    </div>
  );
}

function ConditionEditor({
  condition,
  index,
  total,
  onChange,
  onRemove,
  onMove,
}: {
  condition: NodeCondition;
  index: number;
  total: number;
  onChange: (index: number, field: keyof NodeCondition, value: unknown) => void;
  onRemove: (index: number) => void;
  onMove: (index: number, direction: 'up' | 'down') => void;
}) {
  return (
    <div className="p-3 bg-gray-50 rounded-md space-y-2">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-1">
          <span className="text-xs font-medium text-gray-500">
            Branche {index + 1}
          </span>
          <div className="flex flex-col ml-2">
            <button
              onClick={() => onMove(index, 'up')}
              disabled={index === 0}
              className={`p-0.5 rounded ${index === 0 ? 'text-gray-300' : 'text-gray-400 hover:text-gray-600 hover:bg-gray-200'}`}
              title="Monter"
            >
              <ChevronUp size={14} />
            </button>
            <button
              onClick={() => onMove(index, 'down')}
              disabled={index === total - 1}
              className={`p-0.5 rounded ${index === total - 1 ? 'text-gray-300' : 'text-gray-400 hover:text-gray-600 hover:bg-gray-200'}`}
              title="Descendre"
            >
              <ChevronDown size={14} />
            </button>
          </div>
        </div>
        <button
          onClick={() => onRemove(index)}
          className="text-red-400 hover:text-red-600"
        >
          <Trash2 size={14} />
        </button>
      </div>

      <input
        type="text"
        value={condition.label}
        onChange={(e) => onChange(index, 'label', e.target.value)}
        placeholder="Label de la branche"
        className="w-full px-2 py-1 text-sm border rounded"
      />

      <div className="flex gap-2">
        <select
          value={condition.operator}
          onChange={(e) =>
            onChange(index, 'operator', e.target.value as ConditionOperator)
          }
          className="flex-1 px-2 py-1 text-sm border rounded"
        >
          {OPERATORS.map((op) => (
            <option key={op.value} value={op.value}>
              {op.label}
            </option>
          ))}
        </select>

        {!['is_null', 'is_not_null'].includes(condition.operator) && (
          <ValueEditor
            value={condition.value}
            onChange={(val) => onChange(index, 'value', val)}
          />
        )}
      </div>
    </div>
  );
}

// Détermine le type d'une valeur
function getValueType(value: unknown): 'boolean' | 'number' | 'string' {
  if (typeof value === 'boolean') return 'boolean';
  if (typeof value === 'number') return 'number';
  return 'string';
}

function ValueEditor({
  value,
  onChange,
}: {
  value: unknown;
  onChange: (val: unknown) => void;
}) {
  const currentType = getValueType(value);

  const handleTypeChange = (newType: string) => {
    switch (newType) {
      case 'boolean':
        onChange(true);
        break;
      case 'number':
        onChange(0);
        break;
      default:
        onChange('');
    }
  };

  return (
    <div className="flex-1 flex gap-1">
      <select
        value={currentType}
        onChange={(e) => handleTypeChange(e.target.value)}
        className="w-16 px-1 py-1 text-xs border rounded bg-gray-100"
        title="Type de valeur"
      >
        <option value="string">Txt</option>
        <option value="number">Num</option>
        <option value="boolean">Bool</option>
      </select>

      {currentType === 'boolean' && (
        <select
          value={String(value)}
          onChange={(e) => onChange(e.target.value === 'true')}
          className="flex-1 px-2 py-1 text-sm border rounded"
        >
          <option value="true">true</option>
          <option value="false">false</option>
        </select>
      )}

      {currentType === 'number' && (
        <input
          type="number"
          step="any"
          value={String(value)}
          onChange={(e) => onChange(parseFloat(e.target.value) || 0)}
          placeholder="Valeur"
          className="flex-1 px-2 py-1 text-sm border rounded"
        />
      )}

      {currentType === 'string' && (
        <input
          type="text"
          value={String(value)}
          onChange={(e) => onChange(e.target.value)}
          placeholder="Valeur"
          className="flex-1 px-2 py-1 text-sm border rounded"
        />
      )}
    </div>
  );
}
