import { DECISION_COLORS } from '@/constants/decisions';
import type { EvaluationResponse } from '@/types/evaluation';

function Tile({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-card border border-slate-200 bg-white p-4">
      <p className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</p>
      <p className="mt-1 text-2xl font-semibold tracking-tight text-slate-900">{value}</p>
    </div>
  );
}

/** Résumé de campagne : tuiles (total, succès, erreurs, taux) + distribution en barres (spec §3). */
export function BatchSummary({ response }: { response: EvaluationResponse }) {
  const rate = response.total > 0 ? Math.round((response.success_count / response.total) * 100) : 0;
  const max = Math.max(...Object.values(response.decision_summary), 1);

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Tile label="Total" value={String(response.total)} />
        <Tile label="Succès" value={String(response.success_count)} />
        <Tile label="Erreurs" value={String(response.error_count)} />
        <Tile label="Taux de succès" value={`${rate}%`} />
      </div>
      <ul aria-label="Distribution des décisions" className="space-y-1.5">
        {Object.entries(response.decision_summary).map(([decision, count]) => (
          <li key={decision} className="flex items-center gap-2 text-sm">
            <span className="w-28 shrink-0 truncate text-slate-700">{decision}</span>
            <span className="h-4 flex-1 overflow-hidden rounded bg-slate-100">
              <span
                className="block h-full rounded"
                style={{ width: `${(count / max) * 100}%`, backgroundColor: DECISION_COLORS[decision] ?? '#64748b' }}
              />
            </span>
            <span className="w-10 shrink-0 text-right tabular-nums text-slate-500">{count}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
