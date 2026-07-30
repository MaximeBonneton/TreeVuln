import { DECISION_COLORS } from '../../constants/decisions';

interface DecisionBadgeProps {
  decision: string;
  size?: 'sm' | 'md';
}

// Track* (jaune #eab308) : texte foncé requis pour le contraste AA
const DARK_TEXT_DECISIONS = new Set(['Track*']);

const sizeClasses = {
  sm: 'px-2 py-0.5 text-xs',
  md: 'px-2.5 py-0.5 text-sm',
};

export function DecisionBadge({ decision, size = 'md' }: DecisionBadgeProps) {
  const color = DECISION_COLORS[decision];
  const base = `inline-flex items-center rounded-full font-semibold ${sizeClasses[size]}`;

  // Les arbres custom peuvent produire des décisions hors SSVC (Block, Remediate…)
  if (!color) {
    return <span className={`${base} bg-slate-200 text-slate-700`}>{decision}</span>;
  }

  const textClass = DARK_TEXT_DECISIONS.has(decision) ? 'text-slate-900' : 'text-white';
  return (
    <span className={`${base} ${textClass}`} style={{ backgroundColor: color }}>
      {decision}
    </span>
  );
}
