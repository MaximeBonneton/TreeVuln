import { Trash2 } from 'lucide-react';
import type { SimpleConditionCriteria, ConditionOperator } from '@/types';
import { OPERATORS, ValueEditor } from './ValueEditor';

export function CriterionEditor({
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
