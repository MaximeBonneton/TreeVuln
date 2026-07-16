import { describe, it, expect, beforeEach } from 'vitest';
import { useTreeStore } from '../treeStore';
import type { TreeStructure } from '@/types';

// Reset the store before each test
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
  it('adds an input node with default config', () => {
    const store = useTreeStore.getState();
    store.addNode('input', { x: 100, y: 200 });

    const { nodes } = useTreeStore.getState();
    expect(nodes).toHaveLength(1);
    expect(nodes[0].data.nodeType).toBe('input');
    expect(nodes[0].data.label).toBe('Input');
    expect(nodes[0].data.config).toEqual({ field: '' });
    expect(nodes[0].position).toEqual({ x: 100, y: 200 });
  });

  it('adds an output node with default config', () => {
    const store = useTreeStore.getState();
    store.addNode('output', { x: 0, y: 0 });

    const { nodes } = useTreeStore.getState();
    expect(nodes).toHaveLength(1);
    expect(nodes[0].data.nodeType).toBe('output');
    expect(nodes[0].data.config).toEqual({ decision: 'Track', color: '#22c55e' });
  });

  it('adds a lookup node with default config', () => {
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

  it('marks hasUnsavedChanges as true', () => {
    const store = useTreeStore.getState();
    store.addNode('input', { x: 0, y: 0 });
    expect(useTreeStore.getState().hasUnsavedChanges).toBe(true);
  });
});

describe('updateNodeData', () => {
  it('updates a node label', () => {
    const store = useTreeStore.getState();
    store.addNode('input', { x: 0, y: 0 });
    const nodeId = useTreeStore.getState().nodes[0].id;

    store.updateNodeData(nodeId, { label: 'Mon Input' });

    const node = useTreeStore.getState().nodes[0];
    expect(node.data.label).toBe('Mon Input');
  });

  it('updates a node config', () => {
    const store = useTreeStore.getState();
    store.addNode('input', { x: 0, y: 0 });
    const nodeId = useTreeStore.getState().nodes[0].id;

    store.updateNodeData(nodeId, { config: { field: 'cvss_score' } });

    const node = useTreeStore.getState().nodes[0];
    expect(node.data.config).toEqual({ field: 'cvss_score' });
  });
});

describe('deleteNode', () => {
  it('deletes a node and its edges', () => {
    const store = useTreeStore.getState();
    store.addNode('input', { x: 0, y: 0 });
    store.addNode('output', { x: 200, y: 0 });

    const nodes = useTreeStore.getState().nodes;
    const inputId = nodes[0].id;
    const outputId = nodes[1].id;

    // Add an edge manually
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

  it('deselects the deleted node', () => {
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
  it('deletes an edge by ID', () => {
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
  it('duplicates a node with an offset', () => {
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
  it('selects a node', () => {
    const store = useTreeStore.getState();
    store.selectNode('node-1');
    expect(useTreeStore.getState().selectedNodeId).toBe('node-1');
  });

  it('deselects with null', () => {
    const store = useTreeStore.getState();
    store.selectNode('node-1');
    store.selectNode(null);
    expect(useTreeStore.getState().selectedNodeId).toBeNull();
  });
});

describe('applyNodeConditions', () => {
  it('remaps edge sourceHandle when conditions are permuted (reorder)', () => {
    const store = useTreeStore.getState();
    store.addNode('input', { x: 0, y: 0 });
    store.addNode('output', { x: 200, y: 0 });
    store.addNode('output', { x: 200, y: 100 });

    const nodes = useTreeStore.getState().nodes;
    const nodeId = nodes[0].id;
    const outputA = nodes[1].id;
    const outputB = nodes[2].id;

    const originalConditions = [
      { operator: 'gte' as const, value: 9, label: '>= 9' },
      { operator: 'lt' as const, value: 9, label: '< 9' },
    ];
    store.updateNodeData(nodeId, { conditions: originalConditions });

    store.setEdges([
      { id: 'e-a', source: nodeId, target: outputA, sourceHandle: 'handle-0', type: 'colored' },
      { id: 'e-b', source: nodeId, target: outputB, sourceHandle: 'handle-1', type: 'colored' },
    ]);

    // Permute: old index 0 -> new index 1, old index 1 -> new index 0
    const permuted = [originalConditions[1], originalConditions[0]];
    store.applyNodeConditions(nodeId, permuted, new Map([[0, 1], [1, 0]]));

    const state = useTreeStore.getState();
    const node = state.nodes.find((n) => n.id === nodeId)!;
    expect(node.data.conditions).toEqual(permuted);

    const edgeA = state.edges.find((e) => e.id === 'e-a')!;
    const edgeB = state.edges.find((e) => e.id === 'e-b')!;
    expect(edgeA.sourceHandle).toBe('handle-1');
    expect(edgeB.sourceHandle).toBe('handle-0');
  });

  it('removes edges whose condition index maps to null (deletion)', () => {
    const store = useTreeStore.getState();
    store.addNode('input', { x: 0, y: 0 });
    store.addNode('output', { x: 200, y: 0 });
    store.addNode('output', { x: 200, y: 100 });

    const nodes = useTreeStore.getState().nodes;
    const nodeId = nodes[0].id;
    const outputA = nodes[1].id;
    const outputB = nodes[2].id;

    const originalConditions = [
      { operator: 'eq' as const, value: 'a', label: 'A' },
      { operator: 'eq' as const, value: 'b', label: 'B' },
    ];
    store.updateNodeData(nodeId, { conditions: originalConditions });

    store.setEdges([
      { id: 'e-keep', source: nodeId, target: outputA, sourceHandle: 'handle-0', type: 'colored' },
      { id: 'e-removed', source: nodeId, target: outputB, sourceHandle: 'handle-1', type: 'colored' },
    ]);

    // Condition at old index 1 is removed
    const remaining = [originalConditions[0]];
    store.applyNodeConditions(nodeId, remaining, new Map([[0, 0], [1, null]]));

    const state = useTreeStore.getState();
    const node = state.nodes.find((n) => n.id === nodeId)!;
    expect(node.data.conditions).toEqual(remaining);

    expect(state.edges.find((e) => e.id === 'e-removed')).toBeUndefined();
    const keptEdge = state.edges.find((e) => e.id === 'e-keep')!;
    expect(keptEdge.sourceHandle).toBe('handle-0');
  });

  it('preserves the input index for multi-input nodes', () => {
    const store = useTreeStore.getState();
    store.addNode('input', { x: 0, y: 0 });
    store.addNode('output', { x: 200, y: 0 });

    const nodes = useTreeStore.getState().nodes;
    const nodeId = nodes[0].id;
    const outputId = nodes[1].id;

    const originalConditions = [
      { operator: 'eq' as const, value: 'x', label: 'X' },
      { operator: 'eq' as const, value: 'y', label: 'Y' },
    ];
    store.updateNodeData(nodeId, { conditions: originalConditions });

    store.setEdges([
      { id: 'e-multi', source: nodeId, target: outputId, sourceHandle: 'handle-2-1', type: 'colored' },
    ]);

    store.applyNodeConditions(nodeId, [originalConditions[1]], new Map([[1, 0]]));

    const state = useTreeStore.getState();
    const edge = state.edges.find((e) => e.id === 'e-multi')!;
    expect(edge.sourceHandle).toBe('handle-2-0');
  });

  it('pushes an undo state so the change can be reverted', () => {
    const store = useTreeStore.getState();
    store.addNode('input', { x: 0, y: 0 });
    const nodeId = useTreeStore.getState().nodes[0].id;

    const conditionsBefore = [{ operator: 'eq' as const, value: 'a', label: 'A' }];
    store.updateNodeData(nodeId, { conditions: conditionsBefore });

    const undoLengthBefore = useTreeStore.getState().undoStack.length;
    store.applyNodeConditions(nodeId, [], new Map([[0, null]]));
    expect(useTreeStore.getState().undoStack.length).toBe(undoLengthBefore + 1);

    store.undo();
    const restoredNode = useTreeStore.getState().nodes.find((n) => n.id === nodeId)!;
    expect(restoredNode.data.conditions).toEqual(conditionsBefore);
  });

  it('shifts trailing condition indices down when a middle condition is deleted', () => {
    const store = useTreeStore.getState();
    store.addNode('input', { x: 0, y: 0 });
    store.addNode('output', { x: 200, y: 0 });
    store.addNode('output', { x: 200, y: 100 });
    store.addNode('output', { x: 200, y: 200 });

    const nodes = useTreeStore.getState().nodes;
    const nodeId = nodes[0].id;
    const outputA = nodes[1].id;
    const outputB = nodes[2].id;
    const outputC = nodes[3].id;

    const originalConditions = [
      { operator: 'eq' as const, value: 'a', label: 'A' },
      { operator: 'eq' as const, value: 'b', label: 'B' },
      { operator: 'eq' as const, value: 'c', label: 'C' },
    ];
    store.updateNodeData(nodeId, { conditions: originalConditions });

    store.setEdges([
      { id: 'e-a', source: nodeId, target: outputA, sourceHandle: 'handle-0', type: 'colored' },
      { id: 'e-b', source: nodeId, target: outputB, sourceHandle: 'handle-1', type: 'colored' },
      { id: 'e-c', source: nodeId, target: outputC, sourceHandle: 'handle-2', type: 'colored' },
    ]);

    // Condition at old index 1 (middle) is removed: 0 unchanged, 1 removed, 2 shifts to 1
    const remaining = [originalConditions[0], originalConditions[2]];
    store.applyNodeConditions(
      nodeId,
      remaining,
      new Map([
        [0, 0],
        [1, null],
        [2, 1],
      ])
    );

    const state = useTreeStore.getState();
    const node = state.nodes.find((n) => n.id === nodeId)!;
    expect(node.data.conditions).toEqual(remaining);

    expect(state.edges.find((e) => e.id === 'e-b')).toBeUndefined();
    const edgeA = state.edges.find((e) => e.id === 'e-a')!;
    const edgeC = state.edges.find((e) => e.id === 'e-c')!;
    expect(edgeA.sourceHandle).toBe('handle-0');
    expect(edgeC.sourceHandle).toBe('handle-1');
  });
});

describe('toApiStructure / fromApiStructure', () => {
  it('converts nodes and edges to API format', () => {
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

    // Verify API format for nodes
    const apiNode = structure.nodes[0];
    expect(apiNode.type).toBe('input');
    expect(apiNode.label).toBe('Input');
    expect(apiNode.config).toEqual({ field: '' });

    // Verify API format for edges
    const apiEdge = structure.edges[0];
    expect(apiEdge.source_handle).toBe('handle-0');
    expect(apiEdge.label).toBe('Yes');
  });

  it('loads from API format', () => {
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

    // Verify React Flow format
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
