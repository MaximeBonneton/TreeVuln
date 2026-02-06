import { useState, useEffect } from 'react';
import { X, Plus, Trash2, Copy, AlertCircle, ChevronUp, ChevronDown } from 'lucide-react';
import { useTreeStore } from '@/stores/treeStore';
import { fieldMappingApi } from '@/api/fieldMapping';
import type {
  TreeNode,
  NodeCondition,
  SimpleConditionCriteria,
  ConditionOperator,
  InputNodeConfig,
  LookupNodeConfig,
  OutputNodeConfig,
  FieldMapping,
  FieldDefinition,
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
  const [cvssFields, setCvssFields] = useState<FieldDefinition[]>([]);

  // Fetch CVSS fields on mount
  useEffect(() => {
    fieldMappingApi.getCvssFields()
      .then(setCvssFields)
      .catch(console.error);
  }, []);

  const hasMapping = fieldMapping && fieldMapping.fields.length > 0;
  const inputCount = config.input_count ?? 1;

  // Separate standard fields from CVSS fields in the mapping
  const standardFields = hasMapping
    ? fieldMapping.fields.filter(f => !f.name.startsWith('cvss_') || f.name === 'cvss_score' || f.name === 'cvss_vector')
    : [];

  // Find current field in both lists
  const currentFieldInMapping = hasMapping
    ? fieldMapping.fields.find((f) => f.name === config.field)
    : null;
  const currentFieldInCvss = cvssFields.find((f) => f.name === config.field);
  const currentField = currentFieldInMapping || currentFieldInCvss;

  const showWarning = hasMapping && config.field && !currentFieldInMapping && !currentFieldInCvss;

  return (
    <div className="space-y-4">
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
              <optgroup label="Champs standards">
                {standardFields.map((field) => (
                  <option key={field.name} value={field.name}>
                    {field.label || field.name}
                    {field.type !== 'unknown' && ` (${field.type})`}
                  </option>
                ))}
              </optgroup>
              {cvssFields.length > 0 && (
                <optgroup label="Métriques CVSS">
                  {cvssFields.map((field) => (
                    <option key={field.name} value={field.name}>
                      {field.label || field.name}
                    </option>
                  ))}
                </optgroup>
              )}
            </select>

            {currentField && (
              <div className="mt-2 text-xs text-gray-500">
                <p className="font-medium">{currentField.label || currentField.name}</p>
                {currentField.description && (
                  <p className="mt-0.5">{currentField.description}</p>
                )}
                {currentField.examples.length > 0 && (
                  <p className="mt-0.5">
                    Exemples: {currentField.examples.slice(0, 3).map(String).join(', ')}
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

      {/* Input count configuration */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Nombre d'entrées
        </label>
        <div className="flex items-center gap-2">
          <input
            type="number"
            min={1}
            max={20}
            value={inputCount}
            onChange={(e) => onChange({ ...config, input_count: Math.max(1, parseInt(e.target.value) || 1) })}
            className="w-20 px-3 py-2 border rounded-md focus:ring-2 focus:ring-blue-500"
          />
          {inputCount > 1 && (
            <span className="text-xs text-blue-600">
              Mode multi-entrées actif
            </span>
          )}
        </div>
        <p className="text-xs text-gray-500 mt-1">
          Plusieurs entrées permettent de réutiliser ce nœud depuis différents chemins avec des sorties distinctes.
        </p>
      </div>
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
  const inputCount = config.input_count ?? 1;

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

      {/* Input count configuration */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Nombre d'entrées
        </label>
        <div className="flex items-center gap-2">
          <input
            type="number"
            min={1}
            max={20}
            value={inputCount}
            onChange={(e) => onChange({ ...config, input_count: Math.max(1, parseInt(e.target.value) || 1) })}
            className="w-20 px-3 py-2 border rounded-md focus:ring-2 focus:ring-blue-500"
          />
          {inputCount > 1 && (
            <span className="text-xs text-purple-600">
              Mode multi-entrées actif
            </span>
          )}
        </div>
        <p className="text-xs text-gray-500 mt-1">
          Plusieurs entrées permettent de réutiliser ce nœud depuis différents chemins.
        </p>
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

// Détermine si la condition est en mode composé
function isCompoundCondition(condition: NodeCondition): boolean {
  return condition.logic !== undefined && condition.criteria !== undefined;
}

// Convertit une condition simple en condition composée
function toCompoundCondition(condition: NodeCondition): NodeCondition {
  return {
    label: condition.label,
    logic: 'AND',
    criteria: [{
      field: undefined,
      operator: condition.operator || 'eq',
      value: condition.value ?? '',
    }],
  };
}

// Convertit une condition composée en condition simple
function toSimpleCondition(condition: NodeCondition): NodeCondition {
  const firstCriterion = condition.criteria?.[0];
  return {
    label: condition.label,
    operator: firstCriterion?.operator || 'eq',
    value: firstCriterion?.value ?? '',
  };
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
  const isCompound = isCompoundCondition(condition);

  // Bascule entre mode simple et composé
  const toggleMode = () => {
    if (isCompound) {
      const simple = toSimpleCondition(condition);
      onChange(index, 'logic', undefined);
      onChange(index, 'criteria', undefined);
      onChange(index, 'operator', simple.operator);
      onChange(index, 'value', simple.value);
    } else {
      const compound = toCompoundCondition(condition);
      onChange(index, 'operator', undefined);
      onChange(index, 'value', undefined);
      onChange(index, 'logic', compound.logic);
      onChange(index, 'criteria', compound.criteria);
    }
  };

  // Met à jour un critère dans le mode composé
  const updateCriterion = (
    criterionIndex: number,
    field: keyof SimpleConditionCriteria,
    value: unknown
  ) => {
    const newCriteria = [...(condition.criteria || [])];
    newCriteria[criterionIndex] = { ...newCriteria[criterionIndex], [field]: value };
    onChange(index, 'criteria', newCriteria);
  };

  // Ajoute un nouveau critère
  const addCriterion = () => {
    const newCriteria = [...(condition.criteria || []), {
      field: undefined,
      operator: 'eq' as ConditionOperator,
      value: '',
    }];
    onChange(index, 'criteria', newCriteria);
  };

  // Supprime un critère
  const removeCriterion = (criterionIndex: number) => {
    const newCriteria = (condition.criteria || []).filter((_, i) => i !== criterionIndex);
    // S'il ne reste qu'un critère, on le garde (minimum 1)
    if (newCriteria.length === 0) return;
    onChange(index, 'criteria', newCriteria);
  };

  return (
    <div className="p-3 bg-gray-50 rounded-md space-y-2">
      {/* Header avec contrôles */}
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

      {/* Label */}
      <input
        type="text"
        value={condition.label}
        onChange={(e) => onChange(index, 'label', e.target.value)}
        placeholder="Label de la branche"
        className="w-full px-2 py-1 text-sm border rounded"
      />

      {/* Toggle mode simple/composé */}
      <div className="flex items-center gap-2 text-xs">
        <button
          onClick={toggleMode}
          className={`px-2 py-1 rounded ${!isCompound ? 'bg-blue-500 text-white' : 'bg-gray-200 text-gray-600 hover:bg-gray-300'}`}
        >
          Simple
        </button>
        <button
          onClick={toggleMode}
          className={`px-2 py-1 rounded ${isCompound ? 'bg-blue-500 text-white' : 'bg-gray-200 text-gray-600 hover:bg-gray-300'}`}
        >
          Composé
        </button>
      </div>

      {/* Mode simple */}
      {!isCompound && (
        <div className="flex gap-2">
          <select
            value={condition.operator || 'eq'}
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

          {!['is_null', 'is_not_null'].includes(condition.operator || '') && (
            <ValueEditor
              value={condition.value}
              onChange={(val) => onChange(index, 'value', val)}
            />
          )}
        </div>
      )}

      {/* Mode composé */}
      {isCompound && (
        <div className="space-y-2">
          {/* Sélecteur AND/OR */}
          <div className="flex items-center gap-2">
            <span className="text-xs text-gray-500">Logique :</span>
            <select
              value={condition.logic || 'AND'}
              onChange={(e) => onChange(index, 'logic', e.target.value as 'AND' | 'OR')}
              className="px-2 py-1 text-sm border rounded bg-white"
            >
              <option value="AND">AND (toutes vraies)</option>
              <option value="OR">OR (au moins une vraie)</option>
            </select>
          </div>

          {/* Liste des critères */}
          <div className="space-y-2">
            {(condition.criteria || []).map((criterion, criterionIndex) => (
              <CriterionEditor
                key={criterionIndex}
                criterion={criterion}
                index={criterionIndex}
                canRemove={(condition.criteria || []).length > 1}
                onChange={(field, value) => updateCriterion(criterionIndex, field, value)}
                onRemove={() => removeCriterion(criterionIndex)}
              />
            ))}
          </div>

          {/* Bouton ajouter critère */}
          <button
            onClick={addCriterion}
            className="flex items-center gap-1 text-xs text-blue-500 hover:text-blue-700"
          >
            <Plus size={14} />
            Ajouter critère
          </button>
        </div>
      )}
    </div>
  );
}

// Éditeur pour un critère individuel dans une condition composée
function CriterionEditor({
  criterion,
  index,
  canRemove,
  onChange,
  onRemove,
}: {
  criterion: SimpleConditionCriteria;
  index: number;
  canRemove: boolean;
  onChange: (field: keyof SimpleConditionCriteria, value: unknown) => void;
  onRemove: () => void;
}) {
  return (
    <div className="p-2 bg-white border rounded space-y-2">
      <div className="flex items-center justify-between">
        <span className="text-xs text-gray-400">Critère {index + 1}</span>
        {canRemove && (
          <button
            onClick={onRemove}
            className="text-red-400 hover:text-red-600"
          >
            <Trash2 size={12} />
          </button>
        )}
      </div>

      {/* Champ optionnel */}
      <div>
        <input
          type="text"
          value={criterion.field || ''}
          onChange={(e) => onChange('field', e.target.value || undefined)}
          placeholder="Champ (vide = champ du nœud)"
          className="w-full px-2 py-1 text-xs border rounded"
        />
      </div>

      {/* Opérateur + valeur */}
      <div className="flex gap-2">
        <select
          value={criterion.operator}
          onChange={(e) => onChange('operator', e.target.value as ConditionOperator)}
          className="flex-1 px-2 py-1 text-xs border rounded"
        >
          {OPERATORS.map((op) => (
            <option key={op.value} value={op.value}>
              {op.label}
            </option>
          ))}
        </select>

        {!['is_null', 'is_not_null'].includes(criterion.operator) && (
          <ValueEditor
            value={criterion.value}
            onChange={(val) => onChange('value', val)}
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
