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
import { getInputCount, parseInputHandle, parseSourceHandle } from './handles';

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

/** Position relative (0..1) d'un handle de sortie dans la hauteur du nœud.
 * Aligné sur le rendu mono-input de TreeNode ((index + 0.5) / total) ; pour
 * le multi-input (géométrie en pixels dans TreeNode), la répartition
 * uniforme par rang de bande reste une approximation : elle préserve l'ordre
 * et un centrage approché, seuls besoins du layout. */
function sourceHandleFraction(node: TreeNode | undefined, handle: string | null | undefined): number {
  if (!node || !handle) return 0.5;
  const parsed = parseSourceHandle(handle);
  if (!parsed) return 0.5;
  const conditions = Math.max(1, node.data.conditions?.length ?? 0);
  const total = getInputCount(node.data) * conditions;
  const rank = Math.min(parsed.inputIndex * conditions + parsed.conditionIndex, total - 1);
  return (rank + 0.5) / total;
}

/** Position relative (0..1) d'un handle d'entrée (input-{i}) dans le nœud cible. */
function targetHandleFraction(node: TreeNode | undefined, handle: string | null | undefined): number {
  if (!node || !handle) return 0.5;
  const inputCount = getInputCount(node.data);
  if (inputCount <= 1) return 0.5;
  const idx = parseInputHandle(handle);
  if (idx === null) return 0.5;
  return (Math.min(idx, inputCount - 1) + 0.5) / inputCount;
}

/** Ajoute une edge à la liste d'un nœud dans la map (créée au besoin). */
function appendEdge(map: Map<string, TreeEdge[]>, key: string, edge: TreeEdge): void {
  const list = map.get(key);
  if (list) list.push(edge);
  else map.set(key, [edge]);
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
    const column = columnsByX.get(x);
    if (column) column.push(node.id);
    else columnsByX.set(x, [node.id]);
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
    appendEdge(incoming, edge.target, edge);
    appendEdge(outgoing, edge.source, edge);
  }

  /** Réordonne une colonne selon des clés, puis réassigne des y espacés. */
  const placeColumn = (ids: string[], keyOf: (id: string) => number) => {
    const keyed = ids.map((id) => ({ id, key: keyOf(id), height: heightOf(id) }));
    // Tri stable : clé, puis y courant, puis id (déterminisme)
    keyed.sort(
      (a, b) =>
        a.key - b.key ||
        centerY.get(a.id)! - centerY.get(b.id)! ||
        a.id.localeCompare(b.id)
    );
    let totalHeight = -NODE_SEP;
    let keySum = 0;
    for (const k of keyed) {
      totalHeight += k.height + NODE_SEP;
      keySum += k.key;
    }
    let top = keySum / keyed.length - totalHeight / 2;
    for (const { id, height } of keyed) {
      centerY.set(id, top + height / 2);
      top += height + NODE_SEP;
    }
  };

  /** Point d'ancrage vertical du handle source d'une edge (côté parent). */
  const parentAnchor = (edge: TreeEdge): number => {
    const fraction = sourceHandleFraction(nodeById.get(edge.source), edge.sourceHandle);
    return centerY.get(edge.source)! + (fraction - 0.5) * heightOf(edge.source);
  };

  /** Point d'ancrage vertical du handle d'entrée visé par une edge (côté enfant). */
  const childAnchor = (edge: TreeEdge): number => {
    const fraction = targetHandleFraction(nodeById.get(edge.target), edge.targetHandle);
    return centerY.get(edge.target)! + (fraction - 0.5) * heightOf(edge.target);
  };

  /** Clé de tri d'un nœud : moyenne des ancrages de ses edges (ou y courant). */
  const keyFromEdges = (
    edgesOf: Map<string, TreeEdge[]>,
    anchorOf: (edge: TreeEdge) => number,
  ) => (id: string): number => {
    const connected = edgesOf.get(id);
    if (!connected || connected.length === 0) return centerY.get(id)!;
    return connected.reduce((sum, edge) => sum + anchorOf(edge), 0) / connected.length;
  };

  const keyFromParents = keyFromEdges(incoming, parentAnchor);
  const keyFromChildren = keyFromEdges(outgoing, childAnchor);

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
