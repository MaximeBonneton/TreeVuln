/**
 * Auto-layout des nœuds avec Dagre (algorithme hiérarchique gauche→droite).
 */

import Dagre from '@dagrejs/dagre';
import type { TreeNode, TreeEdge } from '@/types';

/** Dimensions estimées des nœuds (px) */
const NODE_WIDTH = 220;
const NODE_HEIGHT = 120;

/** Espacement entre les nœuds */
const RANK_SEP = 120; // horizontal (entre colonnes)
const NODE_SEP = 40;  // vertical (entre nœuds d'une même colonne)

/**
 * Calcule les positions optimales des nœuds via Dagre.
 * Retourne de nouveaux nœuds avec les positions mises à jour.
 */
export function getLayoutedNodes(
  nodes: TreeNode[],
  edges: TreeEdge[],
): TreeNode[] {
  const g = new Dagre.graphlib.Graph().setDefaultEdgeLabel(() => ({}));

  g.setGraph({
    rankdir: 'LR',   // gauche→droite (layout horizontal)
    ranksep: RANK_SEP,
    nodesep: NODE_SEP,
    marginx: 50,
    marginy: 50,
  });

  // Ajouter les nœuds
  for (const node of nodes) {
    g.setNode(node.id, { width: NODE_WIDTH, height: NODE_HEIGHT });
  }

  // Ajouter les edges
  for (const edge of edges) {
    g.setEdge(edge.source, edge.target);
  }

  // Calculer le layout
  Dagre.layout(g);

  // Appliquer les nouvelles positions (centrer sur le coin supérieur gauche)
  return nodes.map((node) => {
    const pos = g.node(node.id);
    return {
      ...node,
      position: {
        x: pos.x - NODE_WIDTH / 2,
        y: pos.y - NODE_HEIGHT / 2,
      },
    };
  });
}
