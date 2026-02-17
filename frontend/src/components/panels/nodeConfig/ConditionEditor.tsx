import { Plus, Trash2, ChevronUp, ChevronDown } from 'lucide-react';
import type { NodeCondition, SimpleConditionCriteria, ConditionOperator } from '@/types';
import { OPERATORS, NUMERIC_OPERATORS, ValueEditor } from './ValueEditor';
import { CriterionEditor } from './CriterionEditor';

function isCompoundCondition(condition: NodeCondition): boolean {
  return condition.logic !== undefined && condition.criteria !== undefined;
}

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

function toSimpleCondition(condition: NodeCondition): NodeCondition {
  const firstCriterion = condition.criteria?.[0];
  return {
    label: condition.label,
    operator: firstCriterion?.operator || 'eq',
    value: firstCriterion?.value ?? '',
  };
}

export function ConditionEditor({
  condition,
  index,
  total,
  onChange,
  onRemove,
  onMove,
  numericOnly,
}: {
  condition: NodeCondition;
  index: number;
  total: number;
  onChange: (index: number, field: keyof NodeCondition, value: unknown) => void;
  onRemove: (index: number) => void;
  onMove: (index: number, direction: 'up' | 'down') => void;
  numericOnly?: boolean;
}) {
  const isCompound = isCompoundCondition(condition);

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

  const updateCriterion = (
    criterionIndex: number,
    field: keyof SimpleConditionCriteria,
    value: unknown
  ) => {
    const newCriteria = [...(condition.criteria || [])];
    newCriteria[criterionIndex] = { ...newCriteria[criterionIndex], [field]: value };
    onChange(index, 'criteria', newCriteria);
  };

  const addCriterion = () => {
    const newCriteria = [...(condition.criteria || []), {
      field: undefined,
      operator: 'eq' as ConditionOperator,
      value: '',
    }];
    onChange(index, 'criteria', newCriteria);
  };

  const removeCriterion = (criterionIndex: number) => {
    const newCriteria = (condition.criteria || []).filter((_, i) => i !== criterionIndex);
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
            {(numericOnly ? NUMERIC_OPERATORS : OPERATORS).map((op) => (
              <option key={op.value} value={op.value}>
                {op.label}
              </option>
            ))}
          </select>

          {!['is_null', 'is_not_null'].includes(condition.operator || '') && (
            <ValueEditor
              value={condition.value}
              onChange={(val) => onChange(index, 'value', val)}
              numericOnly={numericOnly}
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
                numericOnly={numericOnly}
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
