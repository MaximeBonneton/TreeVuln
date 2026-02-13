import { useState, useEffect } from 'react';
import { AlertCircle } from 'lucide-react';
import { fieldMappingApi } from '@/api/fieldMapping';
import type { InputNodeConfig, FieldMapping, FieldDefinition } from '@/types';

export function InputConfig({
  config,
  onChange,
  fieldMapping,
}: {
  config: InputNodeConfig;
  onChange: (c: InputNodeConfig) => void;
  fieldMapping: FieldMapping | null;
}) {
  const [cvssFields, setCvssFields] = useState<FieldDefinition[]>([]);

  useEffect(() => {
    fieldMappingApi.getCvssFields()
      .then(setCvssFields)
      .catch(console.error);
  }, []);

  const hasMapping = fieldMapping && fieldMapping.fields.length > 0;
  const inputCount = config.input_count ?? 1;

  const standardFields = hasMapping
    ? fieldMapping.fields.filter(f => !f.name.startsWith('cvss_') || f.name === 'cvss_score' || f.name === 'cvss_vector')
    : [];

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
