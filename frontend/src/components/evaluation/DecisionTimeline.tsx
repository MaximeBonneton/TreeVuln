import type { DecisionPath } from '@/types/evaluation';

// Couleur de pastille par type de nœud (mêmes familles que le canvas Builder)
const DOT_COLORS: Record<string, string> = {
  input: 'bg-indigo-500',
  lookup: 'bg-violet-500',
  equation: 'bg-cyan-500',
  output: 'bg-emerald-500',
};

/** Chemin de décision en timeline verticale : une étape par nœud traversé (spec §3 Évaluation). */
export function DecisionTimeline({ path }: { path: DecisionPath[] }) {
  return (
    <ol className="relative ml-2 border-l border-slate-200 pl-5">
      {path.map((step, i) => (
        <li key={`${step.node_id}-${i}`} className="relative pb-4 last:pb-0">
          <span
            aria-hidden="true"
            className={`absolute -left-[26px] top-1 h-2.5 w-2.5 rounded-full ring-4 ring-white ${DOT_COLORS[step.node_type] ?? 'bg-slate-400'}`}
          />
          <p className="text-sm font-medium text-slate-900">{step.node_label}</p>
          {step.field_evaluated != null && (
            <p className="text-xs text-slate-500">
              <code className="font-mono">{step.field_evaluated}</code>
              {' = '}
              <code className="font-mono">{JSON.stringify(step.value_found)}</code>
              {step.condition_matched != null && <> → {step.condition_matched}</>}
            </p>
          )}
        </li>
      ))}
    </ol>
  );
}
