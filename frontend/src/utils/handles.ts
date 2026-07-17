/**
 * Convention des handles React Flow — source de vérité unique du format :
 * - sortie : `handle-{cond}` (mono-input) ou `handle-{input}-{cond}` (multi-input)
 * - entrée : `input-{index}` (nœuds multi-input)
 *
 * Historiquement ce format était re-parsé localement dans plusieurs fichiers
 * (treeStore, ColoredEdge, EdgeConfigPanel...). Tout nouveau code doit passer
 * par ces helpers ; les sites historiques convergeront ici au fil de l'eau.
 */

import type { InputNodeConfig, LookupNodeConfig, TreeNodeData } from '@/types';

export interface SourceHandleRef {
  inputIndex: number;
  conditionIndex: number;
}

/** Nombre d'entrées d'un nœud (toujours 1 pour output/equation). */
export function getInputCount(data: TreeNodeData): number {
  if (data.nodeType === 'output' || data.nodeType === 'equation') return 1;
  const config = data.config as InputNodeConfig | LookupNodeConfig;
  return config.input_count ?? 1;
}

/** Parse `handle-{cond}` ou `handle-{input}-{cond}`. Null si format inconnu. */
export function parseSourceHandle(handle: string): SourceHandleRef | null {
  const match = /^handle-(?:(\d+)-)?(\d+)$/.exec(handle);
  if (!match) return null;
  return {
    inputIndex: match[1] !== undefined ? Number(match[1]) : 0,
    conditionIndex: Number(match[2]),
  };
}

/** Parse `input-{index}`. Null si format inconnu. */
export function parseInputHandle(handle: string): number | null {
  const match = /^input-(\d+)$/.exec(handle);
  return match ? Number(match[1]) : null;
}
