import { describe, it, expect } from 'vitest';
import { getLayoutedNodes } from '../autoLayout';
import type { TreeNode, TreeEdge } from '@/types';

function inputNode(id: string, conditionCount: number): TreeNode {
  return {
    id,
    type: 'custom',
    position: { x: 0, y: 0 },
    data: {
      label: id,
      nodeType: 'input',
      config: { field: 'f' },
      conditions: Array.from({ length: conditionCount }, (_, i) => ({
        label: `c${i}`,
        operator: 'eq',
        value: i,
      })),
    },
  } as unknown as TreeNode;
}

function outputNode(id: string): TreeNode {
  return {
    id,
    type: 'custom',
    position: { x: 0, y: 0 },
    data: {
      label: id,
      nodeType: 'output',
      config: { decision: id, color: '#000' },
      conditions: [],
    },
  } as unknown as TreeNode;
}

function multiInputNode(id: string, inputCount: number, conditionCount: number): TreeNode {
  const node = inputNode(id, conditionCount);
  (node.data.config as { input_count?: number }).input_count = inputCount;
  return node;
}

function edge(
  id: string,
  source: string,
  target: string,
  handle: string,
  targetHandle?: string
): TreeEdge {
  return { id, source, target, sourceHandle: handle, targetHandle } as TreeEdge;
}

const byId = (nodes: TreeNode[]) =>
  Object.fromEntries(nodes.map((n) => [n.id, n.position]));

describe('getLayoutedNodes — ordre vertical aligné sur les handles', () => {
  it('ordonne les cibles selon l’index de condition du parent, pas l’ordre des edges', () => {
    // Edges volontairement insérées dans l'ordre inverse des handles :
    // un layout naïf suit l'ordre d'insertion et croise les liens.
    const nodes = [inputNode('root', 3), outputNode('A'), outputNode('B'), outputNode('C')];
    const edges = [
      edge('e2', 'root', 'A', 'handle-2'),
      edge('e1', 'root', 'B', 'handle-1'),
      edge('e0', 'root', 'C', 'handle-0'),
    ];

    const pos = byId(getLayoutedNodes(nodes, edges));
    // handle-0 (haut) -> C au-dessus de B (handle-1), lui-même au-dessus de A (handle-2)
    expect(pos['C'].y).toBeLessThan(pos['B'].y);
    expect(pos['B'].y).toBeLessThan(pos['A'].y);
  });

  it('propage l’ordre sur plusieurs niveaux', () => {
    // root: handle-0 -> n1, handle-1 -> n2 ; puis chaque niveau 2 suit son parent
    const nodes = [
      inputNode('root', 2),
      inputNode('n1', 2),
      inputNode('n2', 2),
      outputNode('o1a'), outputNode('o1b'), outputNode('o2a'), outputNode('o2b'),
    ];
    const edges = [
      edge('r1', 'root', 'n2', 'handle-1'),
      edge('r0', 'root', 'n1', 'handle-0'),
      edge('a1', 'n1', 'o1b', 'handle-1'),
      edge('a0', 'n1', 'o1a', 'handle-0'),
      edge('b1', 'n2', 'o2b', 'handle-1'),
      edge('b0', 'n2', 'o2a', 'handle-0'),
    ];

    const pos = byId(getLayoutedNodes(nodes, edges));
    // Niveau 1 : n1 (handle-0) au-dessus de n2 (handle-1)
    expect(pos['n1'].y).toBeLessThan(pos['n2'].y);
    // Niveau 2 : les enfants de n1 tous au-dessus des enfants de n2,
    // et dans l'ordre des handles au sein de chaque fratrie
    expect(pos['o1a'].y).toBeLessThan(pos['o1b'].y);
    expect(pos['o2a'].y).toBeLessThan(pos['o2b'].y);
    expect(pos['o1b'].y).toBeLessThan(pos['o2a'].y);
  });

  it('supporte les handles multi-input (handle-{input}-{condition})', () => {
    const nodes = [inputNode('root', 2), outputNode('A'), outputNode('B')];
    const edges = [
      edge('e1', 'root', 'A', 'handle-0-1'),
      edge('e0', 'root', 'B', 'handle-0-0'),
    ];
    const pos = byId(getLayoutedNodes(nodes, edges));
    expect(pos['B'].y).toBeLessThan(pos['A'].y);
  });

  it('retourne des positions finies pour tous les nœuds, même isolés', () => {
    const nodes = [inputNode('root', 1), outputNode('A'), outputNode('orphan')];
    const edges = [edge('e0', 'root', 'A', 'handle-0')];
    const layouted = getLayoutedNodes(nodes, edges);
    expect(layouted).toHaveLength(3);
    for (const n of layouted) {
      expect(Number.isFinite(n.position.x)).toBe(true);
      expect(Number.isFinite(n.position.y)).toBe(true);
    }
  });

  it('ordonne les sorties d’un nœud multi-input par bande (handle-{input}-{cond})', () => {
    // Cas SSVC réduit : s1 -> input-0 de m, s2 -> input-1 ; chaque bande a
    // 2 sorties. Dagre seul rend un ordre arbitraire (A, C, B, D constaté).
    const nodes = [
      inputNode('s1', 1), inputNode('s2', 1),
      multiInputNode('m', 2, 2),
      outputNode('A'), outputNode('B'), outputNode('C'), outputNode('D'),
    ];
    const edges = [
      edge('i1', 's1', 'm', 'handle-0', 'input-0'),
      edge('i2', 's2', 'm', 'handle-0', 'input-1'),
      // sorties insérées dans le désordre
      edge('o3', 'm', 'D', 'handle-1-1'),
      edge('o1', 'm', 'B', 'handle-0-1'),
      edge('o2', 'm', 'C', 'handle-1-0'),
      edge('o0', 'm', 'A', 'handle-0-0'),
    ];

    const pos = byId(getLayoutedNodes(nodes, edges));
    // Sorties dans l'ordre des handles : bande 0 (A, B) puis bande 1 (C, D)
    expect(pos['A'].y).toBeLessThan(pos['B'].y);
    expect(pos['B'].y).toBeLessThan(pos['C'].y);
    expect(pos['C'].y).toBeLessThan(pos['D'].y);
    // Sources ordonnées selon l'entrée qu'elles alimentent : s1 (input-0) en haut
    expect(pos['s1'].y).toBeLessThan(pos['s2'].y);
  });

  it('sépare verticalement les nœuds d’une même colonne (pas de chevauchement)', () => {
    const nodes = [inputNode('root', 3), outputNode('A'), outputNode('B'), outputNode('C')];
    const edges = [
      edge('e0', 'root', 'A', 'handle-0'),
      edge('e1', 'root', 'B', 'handle-1'),
      edge('e2', 'root', 'C', 'handle-2'),
    ];
    const pos = byId(getLayoutedNodes(nodes, edges));
    const ys = [pos['A'].y, pos['B'].y, pos['C'].y].sort((a, b) => a - b);
    expect(ys[1] - ys[0]).toBeGreaterThanOrEqual(120); // NODE_HEIGHT
    expect(ys[2] - ys[1]).toBeGreaterThanOrEqual(120);
  });

  it('respecte la largeur mesurée : un nœud large (equation) ne colle pas ses cibles', () => {
    // Un nœud equation rendu à 420px de large : ses sorties doivent rester
    // à au moins ~RANK_SEP de son bord droit, pas de son centre théorique.
    const root = inputNode('eq', 2);
    (root as { measured?: { width: number; height: number } }).measured = {
      width: 420,
      height: 120,
    };
    const nodes = [root, outputNode('A'), outputNode('B')];
    const edges = [
      edge('e0', 'eq', 'A', 'handle-0'),
      edge('e1', 'eq', 'B', 'handle-1'),
    ];
    const pos = byId(getLayoutedNodes(nodes, edges));
    const rootRightEdge = pos['eq'].x + 420;
    expect(pos['A'].x - rootRightEdge).toBeGreaterThanOrEqual(100);
    expect(pos['B'].x - rootRightEdge).toBeGreaterThanOrEqual(100);
  });

  it('respecte la hauteur mesurée : pas de chevauchement avec un nœud haut', () => {
    const tall = outputNode('tall');
    (tall as { measured?: { width: number; height: number } }).measured = {
      width: 220,
      height: 320,
    };
    const nodes = [inputNode('root', 2), tall, outputNode('B')];
    const edges = [
      edge('e0', 'root', 'tall', 'handle-0'),
      edge('e1', 'root', 'B', 'handle-1'),
    ];
    const pos = byId(getLayoutedNodes(nodes, edges));
    // tall (handle-0) au-dessus : B doit commencer après tall.y + 320 + espacement
    expect(pos['tall'].y).toBeLessThan(pos['B'].y);
    expect(pos['B'].y - (pos['tall'].y + 320)).toBeGreaterThanOrEqual(40); // NODE_SEP
  });
});
