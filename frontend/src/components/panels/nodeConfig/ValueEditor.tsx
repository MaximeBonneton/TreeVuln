import type { ConditionOperator } from '@/types';

export const OPERATORS: { value: ConditionOperator; label: string }[] = [
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

function getValueType(value: unknown): 'boolean' | 'number' | 'string' {
  if (typeof value === 'boolean') return 'boolean';
  if (typeof value === 'number') return 'number';
  return 'string';
}

export function ValueEditor({
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
