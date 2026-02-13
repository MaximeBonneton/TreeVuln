import { describe, it, expect, beforeEach } from 'vitest';
import { useTreeStore } from '../treeStore';
import type { TreeStructure } from '@/types';

// Réinitialise le store avant chaque test
beforeEach(() => {
  const store = useTreeStore.getState();
  store.setNodes([]);
  store.setEdges([]);
  useTreeStore.setState({
    selectedNodeId: null,
    hasUnsavedChanges: false,
    hoveredNodeId: null,
    hoveredInputIndex: null,
  });
});

describe('addNode', () => {
  it('ajoute un nœud input avec la config par défaut', () => {
    const store = useTreeStore.getState();
    store.addNode('input', { x: 100, y: 200 });

    const { nodes } = useTreeStore.getState();
    expect(nodes).toHaveLength(1);
    expect(nodes[0].data.nodeType).toBe('input');
    expect(nodes[0].data.label).toBe('Input');
    expect(nodes[0].data.config).toEqual({ field: '' });
    expect(nodes[0].position).toEqual({ x: 100, y: 200 });
  });

  it('ajoute un nœud output avec la config par défaut', () => {
    const store = useTreeStore.getState();
    store.addNode('output', { x: 0, y: 0 });

    const { nodes } = useTreeStore.getState();
    expect(nodes).toHaveLength(1);
    expect(nodes[0].data.nodeType).toBe('output');
    expect(nodes[0].data.config).toEqual({ decision: 'Track', color: '#22c55e' });
  });

  it('ajoute un nœud lookup avec la config par défaut', () => {
    const store = useTreeStore.getState();
    store.addNode('lookup', { x: 50, y: 50 });

    const { nodes } = useTreeStore.getState();
    expect(nodes).toHaveLength(1);
    expect(nodes[0].data.nodeType).toBe('lookup');
    expect(nodes[0].data.config).toEqual({
      lookup_table: 'assets',
      lookup_key: 'asset_id',
      lookup_field: 'criticality',
    });
  });

  it('marque hasUnsavedChanges à true', () => {
    const store = useTreeStore.getState();
    store.addNode('input', { x: 0, y: 0 });
    expect(useTreeStore.getState().hasUnsavedChanges).toBe(true);
  });
});

describe('updateNodeData', () => {
  it('met à jour le label d\'un nœud', () => {
    const store = useTreeStore.getState();
    store.addNode('input', { x: 0, y: 0 });
    const nodeId = useTreeStore.getState().nodes[0].id;

    store.updateNodeData(nodeId, { label: 'Mon Input' });

    const node = useTreeStore.getState().nodes[0];
    expect(node.data.label).toBe('Mon Input');
  });

  it('met à jour la config d\'un nœud', () => {
    const store = useTreeStore.getState();
    store.addNode('input', { x: 0, y: 0 });
    const nodeId = useTreeStore.getState().nodes[0].id;

    store.updateNodeData(nodeId, { config: { field: 'cvss_score' } });

    const node = useTreeStore.getState().nodes[0];
    expect(node.data.config).toEqual({ field: 'cvss_score' });
  });
});

describe('deleteNode', () => {
  it('supprime un nœud et ses edges', () => {
    const store = useTreeStore.getState();
    store.addNode('input', { x: 0, y: 0 });
    store.addNode('output', { x: 200, y: 0 });

    const nodes = useTreeStore.getState().nodes;
    const inputId = nodes[0].id;
    const outputId = nodes[1].id;

    // Ajoute une edge manuellement
    store.setEdges([
      {
        id: 'edge-1',
        source: inputId,
        target: outputId,
        sourceHandle: 'handle-0',
        type: 'colored',
      },
    ]);

    store.deleteNode(inputId);

    const state = useTreeStore.getState();
    expect(state.nodes).toHaveLength(1);
    expect(state.nodes[0].id).toBe(outputId);
    expect(state.edges).toHaveLength(0);
  });

  it('désélectionne le nœud supprimé', () => {
    const store = useTreeStore.getState();
    store.addNode('input', { x: 0, y: 0 });
    const nodeId = useTreeStore.getState().nodes[0].id;

    store.selectNode(nodeId);
    expect(useTreeStore.getState().selectedNodeId).toBe(nodeId);

    store.deleteNode(nodeId);
    expect(useTreeStore.getState().selectedNodeId).toBeNull();
  });
});

describe('deleteEdge', () => {
  it('supprime une edge par ID', () => {
    const store = useTreeStore.getState();
    store.setEdges([
      { id: 'e1', source: 'a', target: 'b', type: 'colored' },
      { id: 'e2', source: 'b', target: 'c', type: 'colored' },
    ]);

    store.deleteEdge('e1');

    const { edges } = useTreeStore.getState();
    expect(edges).toHaveLength(1);
    expect(edges[0].id).toBe('e2');
  });
});

describe('duplicateNode', () => {
  it('duplique un nœud avec un offset', () => {
    const store = useTreeStore.getState();
    store.addNode('input', { x: 100, y: 200 });
    const nodeId = useTreeStore.getState().nodes[0].id;

    store.updateNodeData(nodeId, {
      label: 'CVSS',
      config: { field: 'cvss_score' },
      conditions: [{ operator: 'gte', value: 9, label: '>= 9' }],
    });

    store.duplicateNode(nodeId);

    const { nodes } = useTreeStore.getState();
    expect(nodes).toHaveLength(2);

    const copy = nodes[1];
    expect(copy.id).not.toBe(nodeId);
    expect(copy.data.label).toBe('CVSS');
    expect(copy.data.config).toEqual({ field: 'cvss_score' });
    expect(copy.position.x).toBe(150);
    expect(copy.position.y).toBe(250);
  });
});

describe('selectNode', () => {
  it('sélectionne un nœud', () => {
    const store = useTreeStore.getState();
    store.selectNode('node-1');
    expect(useTreeStore.getState().selectedNodeId).toBe('node-1');
  });

  it('désélectionne avec null', () => {
    const store = useTreeStore.getState();
    store.selectNode('node-1');
    store.selectNode(null);
    expect(useTreeStore.getState().selectedNodeId).toBeNull();
  });
});

describe('toApiStructure / fromApiStructure', () => {
  it('convertit les nœuds et edges vers le format API', () => {
    const store = useTreeStore.getState();
    store.addNode('input', { x: 0, y: 0 });
    store.addNode('output', { x: 300, y: 0 });

    const nodes = useTreeStore.getState().nodes;
    store.setEdges([
      {
        id: 'e1',
        source: nodes[0].id,
        target: nodes[1].id,
        sourceHandle: 'handle-0',
        targetHandle: undefined,
        label: 'Yes',
        type: 'colored',
      },
    ]);

    const structure = useTreeStore.getState().toApiStructure();

    expect(structure.nodes).toHaveLength(2);
    expect(structure.edges).toHaveLength(1);

    // Vérifie le format API des nœuds
    const apiNode = structure.nodes[0];
    expect(apiNode.type).toBe('input');
    expect(apiNode.label).toBe('Input');
    expect(apiNode.config).toEqual({ field: '' });

    // Vérifie le format API des edges
    const apiEdge = structure.edges[0];
    expect(apiEdge.source_handle).toBe('handle-0');
    expect(apiEdge.label).toBe('Yes');
  });

  it('charge depuis le format API', () => {
    const structure: TreeStructure = {
      nodes: [
        {
          id: 'input-1',
          type: 'input',
          label: 'KEV',
          position: { x: 0, y: 0 },
          config: { field: 'kev' },
          conditions: [
            { operator: 'eq', value: true, label: 'Active' },
          ],
        },
        {
          id: 'output-1',
          type: 'output',
          label: 'Act',
          position: { x: 300, y: 0 },
          config: { decision: 'Act', color: '#ef4444' },
          conditions: [],
        },
      ],
      edges: [
        {
          id: 'e1',
          source: 'input-1',
          target: 'output-1',
          source_handle: 'handle-0',
          label: 'Active',
        },
      ],
      metadata: {},
    };

    const store = useTreeStore.getState();
    store.fromApiStructure(structure);

    const state = useTreeStore.getState();
    expect(state.nodes).toHaveLength(2);
    expect(state.edges).toHaveLength(1);

    // Vérifie le format React Flow
    const node = state.nodes[0];
    expect(node.type).toBe('treeNode');
    expect(node.data.nodeType).toBe('input');
    expect(node.data.label).toBe('KEV');
    expect(node.data.config).toEqual({ field: 'kev' });

    const edge = state.edges[0];
    expect(edge.sourceHandle).toBe('handle-0');
    expect(edge.type).toBe('colored');
    expect(edge.label).toBe('Active');
  });
});
