export const SSVC_DECISIONS = [
  { value: 'Act', color: '#dc2626' },
  { value: 'Attend', color: '#f97316' },
  { value: 'Track*', color: '#eab308' },
  { value: 'Track', color: '#22c55e' },
] as const;

export const DECISION_COLORS: Record<string, string> = Object.fromEntries(
  SSVC_DECISIONS.map((d) => [d.value, d.color])
);
