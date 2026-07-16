import { SSVC_DECISIONS } from '@/constants/decisions';
import { VEX_JUSTIFICATIONS, VEX_STATUSES } from '@/constants/vex';
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
          SSVC Decision
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
          Or custom decision
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
          Color
        </label>
        <input
          type="color"
          value={config.color}
          onChange={(e) => onChange({ ...config, color: e.target.value })}
          className="w-full h-10 rounded-md cursor-pointer"
        />
      </div>

      {/* VEX / CSAF : mapping du nœud vers un statut normalisé */}
      <div className="pt-3 border-t space-y-3">
        <p className="text-sm font-semibold text-gray-700">VEX / CSAF</p>
        <div>
          <label
            htmlFor="vex-status"
            className="block text-sm font-medium text-gray-700 mb-1"
          >
            VEX status
          </label>
          <select
            id="vex-status"
            value={config.vex_status ?? ''}
            onChange={(e) => {
              const status = e.target.value;
              const next = { ...config };
              delete next.vex_status;
              delete next.vex_justification;
              if (status) next.vex_status = status;
              onChange(next);
            }}
            className="w-full px-3 py-2 border rounded-md bg-white"
          >
            <option value="">— Not mapped —</option>
            {VEX_STATUSES.map((s) => (
              <option key={s.value} value={s.value}>
                {s.label}
              </option>
            ))}
          </select>
        </div>

        {config.vex_status === 'not_affected' && (
          <div>
            <label
              htmlFor="vex-justification"
              className="block text-sm font-medium text-gray-700 mb-1"
            >
              VEX justification
              <span className="ml-1 text-red-500 text-xs">(required)</span>
            </label>
            <select
              id="vex-justification"
              value={config.vex_justification ?? ''}
              onChange={(e) =>
                onChange({
                  ...config,
                  vex_justification: e.target.value || undefined,
                })
              }
              className="w-full px-3 py-2 border rounded-md bg-white"
            >
              <option value="">— Select a justification —</option>
              {VEX_JUSTIFICATIONS.map((j) => (
                <option key={j.value} value={j.value}>
                  {j.label}
                </option>
              ))}
            </select>
          </div>
        )}
      </div>
    </div>
  );
}
