import type { LookupNodeConfig } from '@/types';

export function LookupConfig({
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
