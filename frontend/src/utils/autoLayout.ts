/**
 * Auto-layout des nœuds : Dagre (rangées gauche-droite) puis réordonnancement
 * vertical de chaque colonne selon la position des handles.
 *
 * Dagre minimise les croisements en supposant que les liens partent du centre
 * des nœuds. Or ici chaque condition a son handle de sortie empilé
 * verticalement (handle-0 en haut, puis handle-1, ... ; pour les nœuds
 * multi-input : handle-{input}-{cond} groupés par bande, et des entrées
 * input-{i} elles aussi empilées). Sans en tenir compte, l'ordre vertical des
 * cibles est arbitraire et les liens se croisent dès la sortie du nœud.
 */

import Dagre from '@dagrejs/dagre';
import type { TreeNode, TreeEdge } from '@/types';

/** Fallback node dimensions (px) — utilisées si le nœud n'a pas encore été
 * mesuré par React Flow (premier rendu, tests). Les nœuds rendus portent
 * leurs dimensions réelles dans `measured` : un nœud Equation avec une longue
 * formule est bien plus large que 220px, l'estimation seule collait ses
 * cibles contre lui. */
const NODE_WIDTH = 220;
const NODE_HEIGHT = 120;

/** Spacing between nodes */
const RANK_SEP = 120; // horizontal (between columns)
const NODE_SEP = 40;  // vertical (between nodes in the same column)

/** Position relative (0..1) d'un handle de sortie dans la hauteur du nœud. */
function sourceHandleFraction(node: TreeNode | undefined, handle: string | null | undefined): number {
  if (!node || !handle) return 0.5;
  const conditions = Math.max(1, node.data.conditions?.length ?? 0);
  const config = node.data.config as { input_count?: number };
  const inputCount = Math.max(1, Number(config?.input_count ?? 1) || 1);

  const parts = handle.replace(/^handle-/, '').split('-').map(Number);
  let rank: number;
  let total: number;
  if (parts.length === 2 && inputCount > 1) {
    // Multi-input : handle-{input}-{cond} -> les bandes se suivent verticalement
    rank = parts[0] * conditions + parts[1];
    total = inputCount * conditions;
  } else {
    rank = parts[parts.length - 1] || 0;
    total = conditions;
  }
  return (rank + 1) / (total + 1);
}

/** Position relative (0..1) d'un handle d'entrée (input-{i}) dans le nœud cible. */
function targetHandleFraction(node: TreeNode | undefined, handle: string | null | undefined): number {
  if (!node || !handle) return 0.5;
  const config = node.data.config as { input_count?: number };
  const inputCount = Math.max(1, Number(config?.input_count ?? 1) || 1);
  if (inputCount <= 1) return 0.5;
  const idx = Number(handle.replace(/^input-/, '')) || 0;
  return (idx + 1) / (inputCount + 1);
}

/**
 * Compute optimal node positions via Dagre, puis réordonne chaque colonne
 * pour suivre l'ordre des handles. Returns new nodes with updated positions.
 */
export function getLayoutedNodes(
  nodes: TreeNode[],
  edges: TreeEdge[],
): TreeNode[] {
  const nodeById = new Map(nodes.map((n) => [n.id, n]));
  const widthOf = (id: string): number =>
    nodeById.get(id)?.measured?.width ?? NODE_WIDTH;
  const heightOf = (id: string): number =>
    nodeById.get(id)?.measured?.height ?? NODE_HEIGHT;

  const g = new Dagre.graphlib.Graph().setDefaultEdgeLabel(() => ({}));

  g.setGraph({
    rankdir: 'LR',   // left-to-right (horizontal layout)
    ranksep: RANK_SEP,
    nodesep: NODE_SEP,
    marginx: 50,
    marginy: 50,
  });

  for (const node of nodes) {
    g.setNode(node.id, { width: widthOf(node.id), height: heightOf(node.id) });
  }
  for (const edge of edges) {
    g.setEdge(edge.source, edge.target);
  }

  Dagre.layout(g);

  // Colonnes = groupes de nœuds partageant le même x Dagre (coordonnées centre)
  const columnsByX = new Map<number, string[]>();
  for (const node of nodes) {
    const x = Math.round(g.node(node.id).x);
    const column = columnsByX.get(x) ?? [];
    column.push(node.id);
    columnsByX.set(x, column);
  }
  const columns = [...columnsByX.entries()]
    .sort((a, b) => a[0] - b[0])
    .map(([, ids]) => ids);

  // y courant (centre) de chaque nœud ; initialisé depuis Dagre
  const centerY = new Map<string, number>(
    nodes.map((n) => [n.id, g.node(n.id).y])
  );

  const incoming = new Map<string, TreeEdge[]>();
  const outgoing = new Map<string, TreeEdge[]>();
  for (const edge of edges) {
    (incoming.get(edge.target) ?? incoming.set(edge.target, []).get(edge.target)!).push(edge);
    (outgoing.get(edge.source) ?? outgoing.set(edge.source, []).get(edge.source)!).push(edge);
  }

  /** Réordonne une colonne selon des clés, puis réassigne des y espacés. */
  const placeColumn = (ids: string[], keyOf: (id: string) => number) => {
    const keyed = ids.map((id) => ({ id, key: keyOf(id) }));
    // Tri stable : clé, puis y courant, puis id (déterminisme)
    keyed.sort(
      (a, b) =>
        a.key - b.key ||
        centerY.get(a.id)! - centerY.get(b.id)! ||
        a.id.localeCompare(b.id)
    );
    const totalHeight =
      keyed.reduce((s, k) => s + heightOf(k.id), 0) + (keyed.length - 1) * NODE_SEP;
    const meanKey = keyed.reduce((s, k) => s + k.key, 0) / keyed.length;
    let top = meanKey - totalHeight / 2;
    for (const { id } of keyed) {
      centerY.set(id, top + heightOf(id) / 2);
      top += heightOf(id) + NODE_SEP;
    }
  };

  /** Clé d'un nœud à partir de ses parents : y du parent + position du handle. */
  const keyFromParents = (id: string): number => {
    const parents = incoming.get(id) ?? [];
    if (parents.length === 0) return centerY.get(id)!;
    let sum = 0;
    for (const edge of parents) {
      const fraction = sourceHandleFraction(nodeById.get(edge.source), edge.sourceHandle);
      sum += centerY.get(edge.source)! + (fraction - 0.5) * heightOf(edge.source);
    }
    return sum / parents.length;
  };

  /** Clé d'un nœud à partir de ses enfants : y de l'enfant + handle d'entrée visé. */
  const keyFromChildren = (id: string): number => {
    const children = outgoing.get(id) ?? [];
    if (children.length === 0) return centerY.get(id)!;
    let sum = 0;
    for (const edge of children) {
      const fraction = targetHandleFraction(nodeById.get(edge.target), edge.targetHandle);
      sum += centerY.get(edge.target)! + (fraction - 0.5) * heightOf(edge.target);
    }
    return sum / children.length;
  };

  // 1. Balayage avant : chaque colonne suit l'ordre des handles de ses parents
  for (let c = 1; c < columns.length; c++) placeColumn(columns[c], keyFromParents);
  // 2. Les racines (aucun parent) s'alignent sur les entrées qu'elles alimentent
  if (columns.length > 0) placeColumn(columns[0], keyFromChildren);
  // 3. Second balayage avant avec l'ordre des racines stabilisé
  for (let c = 1; c < columns.length; c++) placeColumn(columns[c], keyFromParents);

  // Apply new positions (center on top-left corner)
  return nodes.map((node) => {
    const pos = g.node(node.id);
    return {
      ...node,
      position: {
        x: pos.x - widthOf(node.id) / 2,
        y: centerY.get(node.id)! - heightOf(node.id) / 2,
      },
    };
  });
}
