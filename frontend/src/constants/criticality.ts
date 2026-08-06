// Ordre métier de la criticité d'un asset : Critical > High > Medium > Low.
// Un tri alphabétique placerait Critical après High et Low avant Medium.
const RANKS: Record<string, number> = { critical: 4, high: 3, medium: 2, low: 1 };

/** Rang numérique d'une criticité (0 si valeur inconnue), pour le tri. */
export function criticalityRank(value: string): number {
  return RANKS[value.trim().toLowerCase()] ?? 0;
}

/** Variante de Badge associée à une criticité. */
export function criticalityVariant(
  value: string
): 'error' | 'warning' | 'indigo' | 'neutral' {
  switch (value.trim().toLowerCase()) {
    case 'critical':
      return 'error';
    case 'high':
      return 'warning';
    case 'medium':
      return 'indigo';
    default:
      return 'neutral';
  }
}
