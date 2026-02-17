import { useState, useEffect, useRef, useCallback } from 'react';
import { ChevronDown, ChevronRight, Plus, Trash2 } from 'lucide-react';
import { fieldMappingApi } from '@/api/fieldMapping';
import type { EquationNodeConfig, FieldMapping, FieldDefinition, ValueMap } from '@/types';

const FUNCTION_NAMES = new Set(['min', 'max', 'abs', 'round']);
const KEYWORDS = new Set(['if', 'else', 'and', 'or', 'not', 'True', 'False']);

function extractVariables(formula: string): string[] {
  const tokens = formula.match(/[a-zA-Z_][a-zA-Z0-9_]*/g) || [];
  const seen = new Set<string>();
  return tokens.filter((t) => {
    if (FUNCTION_NAMES.has(t) || KEYWORDS.has(t) || seen.has(t)) return false;
    seen.add(t);
    return true;
  });
}

/** Champs connus comme textuels */
const KNOWN_STRING_FIELDS = new Set([
  'asset_criticality',
  'severity',
  'vendor',
  'product',
  'status',
]);

function isLikelyStringField(
  varName: string,
  fieldMapping: FieldMapping | null,
  cvssFields: FieldDefinition[]
): boolean {
  // Cherche dans le fieldMapping
  if (fieldMapping) {
    const field = fieldMapping.fields.find((f) => f.name === varName);
    if (field) return field.type === 'string';
  }
  // Cherche dans les champs CVSS (tous sont numériques/enum)
  if (cvssFields.some((f) => f.name === varName)) return false;
  // Fallback sur les champs connus
  return KNOWN_STRING_FIELDS.has(varName);
}

function FieldChip({
  field,
  color,
  onClick,
}: {
  field: FieldDefinition;
  color: 'blue' | 'violet';
  onClick: () => void;
}) {
  const colorClasses =
    color === 'blue'
      ? 'bg-blue-100 text-blue-800 hover:bg-blue-200'
      : 'bg-purple-100 text-purple-800 hover:bg-purple-200';

  const tooltipLines = [
    field.label && field.label !== field.name ? field.label : null,
    field.type !== 'unknown' ? `Type: ${field.type}` : null,
    field.description || null,
    field.examples.length > 0
      ? `Ex: ${field.examples.slice(0, 3).map(String).join(', ')}`
      : null,
  ].filter(Boolean);

  return (
    <button
      type="button"
      onClick={onClick}
      className={`px-2 py-0.5 rounded text-xs font-mono cursor-pointer transition-colors ${colorClasses}`}
      title={tooltipLines.join('\n')}
    >
      {field.name}
    </button>
  );
}

function ValueMapEditor({
  varName,
  valueMap,
  onChange,
  isStringField,
}: {
  varName: string;
  valueMap: ValueMap | undefined;
  onChange: (vm: ValueMap | undefined) => void;
  isStringField: boolean;
}) {
  const [expanded, setExpanded] = useState(false);

  const entries = valueMap?.entries ?? [];
  const hasEntries = entries.length > 0;

  const addEntry = () => {
    const newEntries = [...entries, { text: '', value: 0 }];
    onChange({
      entries: newEntries,
      default_value: valueMap?.default_value ?? 0,
    });
    if (!expanded) setExpanded(true);
  };

  const updateEntry = (idx: number, field: 'text' | 'value', val: string | number) => {
    const newEntries = entries.map((e, i) =>
      i === idx ? { ...e, [field]: val } : e
    );
    onChange({ entries: newEntries, default_value: valueMap?.default_value ?? 0 });
  };

  const removeEntry = (idx: number) => {
    const newEntries = entries.filter((_, i) => i !== idx);
    if (newEntries.length === 0) {
      onChange(undefined);
    } else {
      onChange({ entries: newEntries, default_value: valueMap?.default_value ?? 0 });
    }
  };

  const updateDefault = (val: number) => {
    onChange({ entries, default_value: val });
  };

  return (
    <div className="border rounded-md overflow-hidden">
      <button
        type="button"
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center gap-2 px-3 py-1.5 text-xs hover:bg-gray-50 text-left"
      >
        <code className="font-mono text-gray-800">{varName}</code>
        {isStringField && !hasEntries && (
          <span className="px-1.5 py-0.5 bg-orange-100 text-orange-700 rounded text-[10px]">
            texte
          </span>
        )}
        {hasEntries && (
          <span className="px-1.5 py-0.5 bg-green-100 text-green-700 rounded text-[10px]">
            {entries.length} mapping{entries.length > 1 ? 's' : ''}
          </span>
        )}
      </button>

      {expanded && (
        <div className="px-3 pb-3 space-y-2 border-t bg-gray-50/50">
          {entries.length > 0 && (
            <div className="mt-2 space-y-1">
              <div className="grid grid-cols-[1fr_80px_28px] gap-1 text-[10px] text-gray-500 font-medium px-0.5">
                <span>Texte</span>
                <span>Valeur</span>
                <span></span>
              </div>
              {entries.map((entry, idx) => (
                <div key={idx} className="grid grid-cols-[1fr_80px_28px] gap-1 items-center">
                  <input
                    type="text"
                    value={entry.text}
                    onChange={(e) => updateEntry(idx, 'text', e.target.value)}
                    placeholder="ex: High"
                    className="px-2 py-1 border rounded text-xs font-mono"
                  />
                  <input
                    type="number"
                    value={entry.value}
                    onChange={(e) => updateEntry(idx, 'value', parseFloat(e.target.value) || 0)}
                    className="px-2 py-1 border rounded text-xs font-mono text-right"
                  />
                  <button
                    type="button"
                    onClick={() => removeEntry(idx)}
                    className="p-1 text-gray-400 hover:text-red-500 transition-colors"
                    title="Supprimer"
                  >
                    <Trash2 size={12} />
                  </button>
                </div>
              ))}
            </div>
          )}

          {hasEntries && (
            <div className="flex items-center gap-2 mt-1">
              <label className="text-[10px] text-gray-500 whitespace-nowrap">
                Defaut (si non trouve) :
              </label>
              <input
                type="number"
                value={valueMap?.default_value ?? 0}
                onChange={(e) => updateDefault(parseFloat(e.target.value) || 0)}
                className="w-20 px-2 py-1 border rounded text-xs font-mono text-right"
              />
            </div>
          )}

          <button
            type="button"
            onClick={addEntry}
            className="flex items-center gap-1 text-xs text-blue-600 hover:text-blue-800 mt-1"
          >
            <Plus size={12} />
            Ajouter une correspondance
          </button>
        </div>
      )}
    </div>
  );
}

export function EquationConfig({
  config,
  onChange,
  fieldMapping,
}: {
  config: EquationNodeConfig;
  onChange: (c: EquationNodeConfig) => void;
  fieldMapping: FieldMapping | null;
}) {
  const [showHelp, setShowHelp] = useState(false);
  const [cvssFields, setCvssFields] = useState<FieldDefinition[]>([]);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const cursorPosRef = useRef<number>(0);

  useEffect(() => {
    fieldMappingApi.getCvssFields()
      .then(setCvssFields)
      .catch(console.error);
  }, []);

  const handleFormulaChange = useCallback((formula: string) => {
    const variables = extractVariables(formula);
    // Nettoie les value_maps des variables supprimees de la formule
    const varSet = new Set(variables);
    let cleanedMaps = config.value_maps;
    if (cleanedMaps) {
      const filtered: Record<string, ValueMap> = {};
      let changed = false;
      for (const [k, v] of Object.entries(cleanedMaps)) {
        if (varSet.has(k)) {
          filtered[k] = v;
        } else {
          changed = true;
        }
      }
      if (changed) {
        cleanedMaps = Object.keys(filtered).length > 0 ? filtered : undefined;
      }
    }
    onChange({ ...config, formula, variables, value_maps: cleanedMaps });
  }, [config, onChange]);

  const handleTextareaSelect = () => {
    if (textareaRef.current) {
      cursorPosRef.current = textareaRef.current.selectionStart;
    }
  };

  const insertFieldAtCursor = (fieldName: string) => {
    const textarea = textareaRef.current;
    if (!textarea) return;

    const pos = cursorPosRef.current;
    const before = config.formula.slice(0, pos);
    const after = config.formula.slice(pos);

    // Ajouter un espace avant/apres si necessaire
    const needSpaceBefore = before.length > 0 && !/\s$/.test(before) && !/[(\[,+\-*/%=<>!&|?:]$/.test(before);
    const needSpaceAfter = after.length > 0 && !/^\s/.test(after) && !/^[)\],+\-*/%=<>!&|?:]/.test(after);

    const inserted = (needSpaceBefore ? ' ' : '') + fieldName + (needSpaceAfter ? ' ' : '');
    const newFormula = before + inserted + after;
    const newCursorPos = pos + inserted.length;

    handleFormulaChange(newFormula);

    // Restaurer le focus et la position du curseur apres le re-render
    requestAnimationFrame(() => {
      if (textareaRef.current) {
        textareaRef.current.focus();
        textareaRef.current.setSelectionRange(newCursorPos, newCursorPos);
        cursorPosRef.current = newCursorPos;
      }
    });
  };

  const handleValueMapChange = (varName: string, vm: ValueMap | undefined) => {
    const newMaps = { ...(config.value_maps || {}) };
    if (vm) {
      newMaps[varName] = vm;
    } else {
      delete newMaps[varName];
    }
    onChange({
      ...config,
      value_maps: Object.keys(newMaps).length > 0 ? newMaps : undefined,
    });
  };

  const hasMapping = fieldMapping && fieldMapping.fields.length > 0;

  const standardFields = hasMapping
    ? fieldMapping.fields.filter(
        (f) => !f.name.startsWith('cvss_') || f.name === 'cvss_score' || f.name === 'cvss_vector'
      )
    : [];

  const numericStandardFields = standardFields.filter(
    (f) => f.type === 'number' || f.type === 'boolean' || f.type === 'unknown'
  );

  const stringStandardFields = standardFields.filter(
    (f) => f.type === 'string'
  );

  const numericCvssFields = cvssFields.filter(
    (f) => f.type === 'number' || f.type === 'unknown'
  );

  const showFieldChips = numericStandardFields.length > 0 || numericCvssFields.length > 0 || stringStandardFields.length > 0;

  return (
    <div className="space-y-4">
      {/* Formule */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Formule
        </label>
        <textarea
          ref={textareaRef}
          value={config.formula}
          onChange={(e) => handleFormulaChange(e.target.value)}
          onSelect={handleTextareaSelect}
          onClick={handleTextareaSelect}
          onKeyUp={handleTextareaSelect}
          placeholder="ex: cvss_score * 0.4 + epss_score * 100 * 0.3 + (kev ? 30 : 0)"
          className="w-full px-3 py-2 border rounded-md focus:ring-2 focus:ring-blue-500 font-mono text-sm"
          rows={3}
          spellCheck={false}
        />
      </div>

      {/* Champs disponibles cliquables */}
      {showFieldChips && (
        <div>
          <label className="block text-xs font-medium text-gray-500 mb-1">
            Champs disponibles
          </label>
          <div className="space-y-2">
            {numericStandardFields.length > 0 && (
              <div>
                <span className="text-xs text-blue-600 font-medium">Standards</span>
                <div className="flex flex-wrap gap-1 mt-1">
                  {numericStandardFields.map((f) => (
                    <FieldChip
                      key={f.name}
                      field={f}
                      color="blue"
                      onClick={() => insertFieldAtCursor(f.name)}
                    />
                  ))}
                </div>
              </div>
            )}
            {numericCvssFields.length > 0 && (
              <div>
                <span className="text-xs text-purple-600 font-medium">CVSS</span>
                <div className="flex flex-wrap gap-1 mt-1">
                  {numericCvssFields.map((f) => (
                    <FieldChip
                      key={f.name}
                      field={f}
                      color="violet"
                      onClick={() => insertFieldAtCursor(f.name)}
                    />
                  ))}
                </div>
              </div>
            )}
            {stringStandardFields.length > 0 && (
              <div>
                <span className="text-xs text-orange-600 font-medium">Texte (via mapping)</span>
                <div className="flex flex-wrap gap-1 mt-1">
                  {stringStandardFields.map((f) => (
                    <button
                      key={f.name}
                      type="button"
                      onClick={() => insertFieldAtCursor(f.name)}
                      className="px-2 py-0.5 rounded text-xs font-mono cursor-pointer transition-colors bg-orange-100 text-orange-800 hover:bg-orange-200"
                      title={[
                        f.label && f.label !== f.name ? f.label : null,
                        'Type: texte (mapping requis)',
                        f.description || null,
                        f.examples.length > 0 ? `Ex: ${f.examples.slice(0, 3).map(String).join(', ')}` : null,
                      ].filter(Boolean).join('\n')}
                    >
                      {f.name}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Variables detectees */}
      {config.variables.length > 0 && (
        <div>
          <label className="block text-xs font-medium text-gray-500 mb-1">
            Variables détectées
          </label>
          <div className="flex flex-wrap gap-1">
            {config.variables.map((v) => (
              <span
                key={v}
                className="px-2 py-0.5 bg-amber-100 text-amber-800 rounded text-xs font-mono"
              >
                {v}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Mapping de valeurs */}
      {config.variables.length > 0 && (
        <div>
          <label className="block text-xs font-medium text-gray-500 mb-1">
            Mapping de valeurs
          </label>
          <p className="text-[10px] text-gray-400 mb-2">
            Convertir les valeurs textuelles en nombres pour le calcul.
          </p>
          <div className="space-y-1">
            {config.variables.map((v) => (
              <ValueMapEditor
                key={v}
                varName={v}
                valueMap={config.value_maps?.[v]}
                onChange={(vm) => handleValueMapChange(v, vm)}
                isStringField={isLikelyStringField(v, fieldMapping, cvssFields)}
              />
            ))}
          </div>
        </div>
      )}

      {/* Label de sortie */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Label de sortie
        </label>
        <input
          type="text"
          value={config.output_label}
          onChange={(e) => onChange({ ...config, output_label: e.target.value })}
          placeholder="ex: Risk Score"
          className="w-full px-3 py-2 border rounded-md focus:ring-2 focus:ring-blue-500"
        />
        <p className="text-xs text-gray-500 mt-1">
          Nom affiché pour le score calculé dans l'audit trail.
        </p>
      </div>

      {/* Aide syntaxe */}
      <div className="border rounded-md">
        <button
          type="button"
          onClick={() => setShowHelp(!showHelp)}
          className="w-full flex items-center gap-1 px-3 py-2 text-xs text-gray-600 hover:bg-gray-50"
        >
          {showHelp ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
          Aide syntaxe
        </button>
        {showHelp && (
          <div className="px-3 pb-3 text-xs text-gray-600 space-y-2">
            <div>
              <span className="font-medium">Opérateurs :</span>{' '}
              <code className="bg-gray-100 px-1 rounded">+ - * / ** %</code>
            </div>
            <div>
              <span className="font-medium">Fonctions :</span>{' '}
              <code className="bg-gray-100 px-1 rounded">min() max() abs() round()</code>
            </div>
            <div>
              <span className="font-medium">Ternaire :</span>{' '}
              <code className="bg-gray-100 px-1 rounded">{'condition ? val_true : val_false'}</code>
            </div>
            <div>
              <span className="font-medium">Comparaisons :</span>{' '}
              <code className="bg-gray-100 px-1 rounded">{'< > <= >= == !='}</code>
            </div>
            <div className="border-t pt-2 mt-2">
              <span className="font-medium">Exemples :</span>
              <div className="mt-1 space-y-1 font-mono bg-gray-50 p-2 rounded">
                <div>cvss_score * 0.4 + epss_score * 100 * 0.3</div>
                <div>max(cvss_score, epss_score * 10)</div>
                <div>kev ? 30 : 0</div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
