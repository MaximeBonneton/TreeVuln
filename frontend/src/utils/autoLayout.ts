/**
 * Auto-layout of nodes with Dagre (hierarchical left-to-right algorithm).
 */

import Dagre from '@dagrejs/dagre';
import type { TreeNode, TreeEdge } from '@/types';

/** Estimated node dimensions (px) */
const NODE_WIDTH = 220;
const NODE_HEIGHT = 120;

/** Spacing between nodes */
const RANK_SEP = 120; // horizontal (between columns)
const NODE_SEP = 40;  // vertical (between nodes in the same column)

/**
 * Compute optimal node positions via Dagre.
 * Returns new nodes with updated positions.
 */
export function getLayoutedNodes(
  nodes: TreeNode[],
  edges: TreeEdge[],
): TreeNode[] {
  const g = new Dagre.graphlib.Graph().setDefaultEdgeLabel(() => ({}));

  g.setGraph({
    rankdir: 'LR',   // left-to-right (horizontal layout)
    ranksep: RANK_SEP,
    nodesep: NODE_SEP,
    marginx: 50,
    marginy: 50,
  });

  // Add nodes
  for (const node of nodes) {
    g.setNode(node.id, { width: NODE_WIDTH, height: NODE_HEIGHT });
  }

  // Add edges
  for (const edge of edges) {
    g.setEdge(edge.source, edge.target);
  }

  // Compute layout
  Dagre.layout(g);

  // Apply new positions (center on top-left corner)
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
