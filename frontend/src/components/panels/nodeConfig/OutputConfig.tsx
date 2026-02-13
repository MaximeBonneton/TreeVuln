import { SSVC_DECISIONS } from '@/constants/decisions';
import type { OutputNodeConfig } from '@/types';

export function OutputConfig({
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
