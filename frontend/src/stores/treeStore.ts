import { create } from 'zustand';
import {
  applyNodeChanges,
  applyEdgeChanges,
  addEdge,
  type NodeChange,
  type EdgeChange,
  type Connection,
} from '@xyflow/react';
import type {
  TreeNode,
  TreeEdge,
  TreeNodeData,
  TreeStructure,
  ApiNode,
  ApiEdge,
  NodeType,
  TreeNodeConfig,
  FieldMapping,
  FieldDefinition,
  TreeListItem,
  TreeApiConfig,
  TreeDuplicateRequest,
} from '@/types';
import { treeApi, fieldMappingApi } from '@/api';
import { getLayoutedNodes } from '@/utils/autoLayout';

// AbortController to cancel in-flight loadTree requests (M-6)
let _loadTreeController: AbortController | null = null;

interface TreeState {
  // Current user
  currentUser: { id: string; username: string; role: 'admin' | 'operator' } | null;

  // Multi-trees
  trees: TreeListItem[];
  isDefault: boolean;
  apiEnabled: boolean;
  apiSlug: string | null;

  // Current tree data
  treeId: number | null;
  treeName: string;
  treeDescription: string;

  // React Flow nodes and edges
  nodes: TreeNode[];
  edges: TreeEdge[];

  // Field mapping
  fieldMapping: FieldMapping | null;

  // UI state
  selectedNodeId: string | null;
  hoveredNodeId: string | null;
  hoveredInputIndex: number | null; // For multi-input nodes
  isLoading: boolean;
  isSaving: boolean;
  hasUnsavedChanges: boolean;
  error: string | null;
  sidebarOpen: boolean;

  // User actions
  setCurrentUser: (user: { id: string; username: string; role: 'admin' | 'operator' } | null) => void;
  isAdmin: () => boolean;

  // Actions
  setNodes: (nodes: TreeNode[]) => void;
  setEdges: (edges: TreeEdge[]) => void;
  onNodesChange: (changes: NodeChange[]) => void;
  onEdgesChange: (changes: EdgeChange[]) => void;
  onConnect: (connection: Connection) => void;

  addNode: (type: NodeType, position: { x: number; y: number }) => void;
  duplicateNode: (nodeId: string) => void;
  updateNodeData: (nodeId: string, data: Partial<TreeNodeData>) => void;
  deleteNode: (nodeId: string) => void;
  deleteEdge: (edgeId: string) => void;
  selectNode: (nodeId: string | null) => void;
  setHoveredNode: (nodeId: string | null, inputIndex?: number | null) => void;

  // Field mapping actions
  setFieldMapping: (mapping: FieldMapping | null) => void;
  loadFieldMapping: () => Promise<void>;
  saveFieldMapping: (fields: FieldDefinition[], source?: string) => Promise<void>;
  deleteFieldMapping: () => Promise<void>;

  // Persistence
  loadTree: (treeId?: number) => Promise<void>;
  saveTree: (comment?: string) => Promise<void>;
  createNewTree: (name: string, description?: string) => Promise<void>;

  // Multi-tree actions
  loadTrees: () => Promise<void>;
  selectTree: (treeId: number) => Promise<void>;
  duplicateTree: (treeId: number, options: TreeDuplicateRequest) => Promise<void>;
  updateApiConfig: (config: TreeApiConfig) => Promise<void>;
  setAsDefault: () => Promise<void>;
  deleteCurrentTree: () => Promise<void>;
  setSidebarOpen: (open: boolean) => void;
  autoLayout: () => void;

  // Conversion
  toApiStructure: () => TreeStructure;
  fromApiStructure: (structure: TreeStructure) => void;
}

// Generate a unique ID for nodes
const generateNodeId = (type: NodeType) =>
  `${type}-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;

// Generate a unique ID for edges
const generateEdgeId = () =>
  `edge-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;

// Default configuration based on node type
const getDefaultConfig = (type: NodeType): TreeNodeConfig => {
  switch (type) {
    case 'input':
      return { field: '' };
    case 'lookup':
      return { lookup_table: 'assets', lookup_key: 'asset_id', lookup_field: 'criticality' };
    case 'equation':
      return { formula: '', variables: [], output_label: 'Score' };
    case 'output':
      return { decision: 'Track', color: '#22c55e' };
  }
};

// Default label based on type
const getDefaultLabel = (type: NodeType): string => {
  switch (type) {
    case 'input':
      return 'Input';
    case 'lookup':
      return 'Lookup';
    case 'equation':
      return 'Equation';
    case 'output':
      return 'Output';
  }
};

export const useTreeStore = create<TreeState>((set, get) => ({
  // Current user
  currentUser: null,
  setCurrentUser: (user) => set({ currentUser: user }),
  isAdmin: () => get().currentUser?.role === 'admin',

  // Initial state
  trees: [],
  isDefault: false,
  apiEnabled: false,
  apiSlug: null,
  treeId: null,
  treeName: 'New tree',
  treeDescription: '',
  nodes: [],
  edges: [],
  fieldMapping: null,
  selectedNodeId: null,
  hoveredNodeId: null,
  hoveredInputIndex: null,
  isLoading: false,
  isSaving: false,
  hasUnsavedChanges: false,
  error: null,
  sidebarOpen: false,

  // Basic setters
  setNodes: (nodes) => set({ nodes, hasUnsavedChanges: true }),
  setEdges: (edges) => set({ edges, hasUnsavedChanges: true }),

  // React Flow handlers
  onNodesChange: (changes) => {
    // Filter significant changes (actual moves or modifications)
    // - position with dragging=true = currently dragging
    // - remove/add = deletion/addition
    // Ignored: select, dimensions, position with dragging=false (init)
    const significantChanges = changes.filter((c) => {
      if (c.type === 'remove' || c.type === 'add') return true;
      if (c.type === 'position' && 'dragging' in c && c.dragging === true) return true;
      return false;
    });
    set({
      nodes: applyNodeChanges(changes, get().nodes) as TreeNode[],
      hasUnsavedChanges: significantChanges.length > 0 ? true : get().hasUnsavedChanges,
    });
  },

  onEdgesChange: (changes) => {
    const significantChanges = changes.filter(
      (c) => c.type === 'remove' || c.type === 'add'
    );
    set({
      edges: applyEdgeChanges(changes, get().edges),
      hasUnsavedChanges: significantChanges.length > 0 ? true : get().hasUnsavedChanges,
    });
  },

  onConnect: (connection) => {
    const { edges } = get();

    const newEdge: TreeEdge = {
      ...connection,
      id: generateEdgeId(),
      label: undefined,
      type: 'colored',
      animated: false,
    } as TreeEdge;

    set({
      edges: addEdge(newEdge, edges),
      hasUnsavedChanges: true,
    });
  },

  // Add a new node
  addNode: (type, position) => {
    const newNode: TreeNode = {
      id: generateNodeId(type),
      type: 'treeNode',
      position,
      data: {
        label: getDefaultLabel(type),
        nodeType: type,
        config: getDefaultConfig(type),
        conditions: type !== 'output' ? [] : [],
      },
    };

    set((state) => ({
      nodes: [...state.nodes, newNode],
      hasUnsavedChanges: true,
    }));
  },

  // Duplicate an existing node
  duplicateNode: (nodeId) => {
    const { nodes } = get();
    const nodeToCopy = nodes.find((n) => n.id === nodeId);
    if (!nodeToCopy) return;

    const newNode: TreeNode = {
      id: generateNodeId(nodeToCopy.data.nodeType),
      type: 'treeNode',
      position: {
        x: nodeToCopy.position.x + 50,
        y: nodeToCopy.position.y + 50,
      },
      data: {
        ...nodeToCopy.data,
        label: nodeToCopy.data.label,
        config: { ...nodeToCopy.data.config },
        conditions: nodeToCopy.data.conditions.map((c) => ({ ...c })),
      },
    };

    set((state) => ({
      nodes: [...state.nodes, newNode],
      hasUnsavedChanges: true,
    }));
  },

  // Update node data
  updateNodeData: (nodeId, data) => {
    set((state) => ({
      nodes: state.nodes.map((node) =>
        node.id === nodeId
          ? { ...node, data: { ...node.data, ...data } }
          : node
      ),
      hasUnsavedChanges: true,
    }));
  },

  // Delete a node and its associated edges
  deleteNode: (nodeId) => {
    set((state) => ({
      nodes: state.nodes.filter((n) => n.id !== nodeId),
      edges: state.edges.filter(
        (e) => e.source !== nodeId && e.target !== nodeId
      ),
      selectedNodeId:
        state.selectedNodeId === nodeId ? null : state.selectedNodeId,
      hasUnsavedChanges: true,
    }));
  },

  // Delete an edge
  deleteEdge: (edgeId) => {
    set((state) => ({
      edges: state.edges.filter((e) => e.id !== edgeId),
      hasUnsavedChanges: true,
    }));
  },

  // Select a node
  selectNode: (nodeId) => set({ selectedNodeId: nodeId }),

  // Hover a node (for edge highlighting)
  setHoveredNode: (nodeId, inputIndex = null) => set({
    hoveredNodeId: nodeId,
    hoveredInputIndex: inputIndex ?? null,
  }),

  // --- Field Mapping ---

  setFieldMapping: (mapping) => set({ fieldMapping: mapping }),

  loadFieldMapping: async () => {
    const { treeId } = get();
    if (!treeId) return;

    try {
      const mapping = await fieldMappingApi.getMapping(treeId);
      set({ fieldMapping: mapping });
    } catch (err) {
      console.error('Error loading mapping:', err);
    }
  },

  saveFieldMapping: async (fields, source = 'manual') => {
    const { treeId } = get();
    if (!treeId) return;

    try {
      const mapping = await fieldMappingApi.updateMapping(treeId, { fields, source });
      set({ fieldMapping: mapping });
    } catch (err) {
      console.error('Error saving mapping:', err);
      throw err;
    }
  },

  deleteFieldMapping: async () => {
    const { treeId } = get();
    if (!treeId) return;

    try {
      await fieldMappingApi.deleteMapping(treeId);
      set({ fieldMapping: null });
    } catch (err) {
      console.error('Error deleting mapping:', err);
      throw err;
    }
  },

  // Load the tree from the API (cancels the previous request if in flight)
  loadTree: async (treeId?: number) => {
    // Cancel the previous request if still in flight
    if (_loadTreeController) {
      _loadTreeController.abort();
    }
    _loadTreeController = new AbortController();
    const { signal } = _loadTreeController;

    set({ isLoading: true, error: null });
    try {
      const tree = await treeApi.getTree(treeId);
      // Check that the request was not cancelled during the wait
      if (signal.aborted) return;
      if (tree) {
        get().fromApiStructure(tree.structure);
        set({
          treeId: tree.id,
          treeName: tree.name,
          treeDescription: tree.description || '',
          isDefault: tree.is_default,
          apiEnabled: tree.api_enabled,
          apiSlug: tree.api_slug,
          hasUnsavedChanges: false,
        });
        // Load the field mapping
        if (!signal.aborted) {
          await get().loadFieldMapping();
        }
      }
    } catch (err) {
      // Ignore cancellation errors
      if (signal.aborted) return;
      set({ error: err instanceof Error ? err.message : 'Loading error' });
    } finally {
      if (!signal.aborted) {
        set({ isLoading: false });
      }
    }
  },

  // Save the tree
  saveTree: async (comment) => {
    const { treeId, treeName, treeDescription } = get();
    set({ isSaving: true, error: null });

    try {
      const structure = get().toApiStructure();

      if (treeId) {
        await treeApi.updateTree(treeId, {
          name: treeName,
          description: treeDescription,
          structure,
          version_comment: comment,
        });
      } else {
        const newTree = await treeApi.createTree({
          name: treeName,
          description: treeDescription,
          structure,
        });
        set({ treeId: newTree.id });
      }

      set({ hasUnsavedChanges: false });
    } catch (err) {
      set({ error: err instanceof Error ? err.message : 'Save error' });
      throw err;
    } finally {
      set({ isSaving: false });
    }
  },

  // Create a new empty tree
  createNewTree: async (name, description) => {
    set({
      treeId: null,
      treeName: name,
      treeDescription: description || '',
      isDefault: false,
      apiEnabled: false,
      apiSlug: null,
      nodes: [],
      edges: [],
      fieldMapping: null,
      selectedNodeId: null,
      hasUnsavedChanges: true,
      error: null,
    });
  },

  // --- Multi-tree ---

  // Load the tree list
  loadTrees: async () => {
    try {
      const trees = await treeApi.listTrees();
      set({ trees });
    } catch (err) {
      console.error('Error loading tree list:', err);
    }
  },

  // Select and load a tree
  selectTree: async (treeId: number) => {
    await get().loadTree(treeId);
    // Reload the list to reflect changes
    await get().loadTrees();
  },

  // Duplicate a tree
  duplicateTree: async (treeId: number, options: TreeDuplicateRequest) => {
    set({ isLoading: true, error: null });
    try {
      const newTree = await treeApi.duplicateTree(treeId, options);
      // Reload the list and select the new tree
      await get().loadTrees();
      await get().loadTree(newTree.id);
    } catch (err) {
      set({ error: err instanceof Error ? err.message : 'Duplication error' });
      throw err;
    } finally {
      set({ isLoading: false });
    }
  },

  // Update API configuration
  updateApiConfig: async (config: TreeApiConfig) => {
    const { treeId } = get();
    if (!treeId) return;

    try {
      const tree = await treeApi.updateApiConfig(treeId, config);
      set({
        apiEnabled: tree.api_enabled,
        apiSlug: tree.api_slug,
      });
      // Reload the list to reflect changes
      await get().loadTrees();
    } catch (err) {
      set({ error: err instanceof Error ? err.message : 'API configuration error' });
      throw err;
    }
  },

  // Set the current tree as default
  setAsDefault: async () => {
    const { treeId } = get();
    if (!treeId) return;

    try {
      await treeApi.setDefaultTree(treeId);
      set({ isDefault: true });
      // Reload the list to reflect changes
      await get().loadTrees();
    } catch (err) {
      set({ error: err instanceof Error ? err.message : 'Error setting default' });
      throw err;
    }
  },

  // Delete the current tree
  deleteCurrentTree: async () => {
    const { treeId, isDefault } = get();
    if (!treeId) return;
    if (isDefault) {
      set({ error: 'Cannot delete the default tree' });
      return;
    }

    try {
      await treeApi.deleteTree(treeId);
      // Reload the list and select the default tree
      await get().loadTrees();
      await get().loadTree();
    } catch (err) {
      set({ error: err instanceof Error ? err.message : 'Deletion error' });
      throw err;
    }
  },

  // Toggle sidebar
  setSidebarOpen: (open: boolean) => set({ sidebarOpen: open }),

  autoLayout: () => {
    const { nodes, edges } = get();
    if (nodes.length === 0) return;
    const layouted = getLayoutedNodes(nodes, edges);
    set({ nodes: layouted, hasUnsavedChanges: true });
  },

  // Convert to API format
  toApiStructure: (): TreeStructure => {
    const { nodes, edges } = get();

    const apiNodes: ApiNode[] = nodes.map((node) => ({
      id: node.id,
      type: node.data.nodeType,
      label: node.data.label,
      position: node.position,
      config: node.data.config,
      conditions: node.data.conditions,
    }));

    const apiEdges: ApiEdge[] = edges.map((edge) => ({
      id: edge.id,
      source: edge.source,
      target: edge.target,
      source_handle: edge.sourceHandle,
      target_handle: edge.targetHandle,
      label: typeof edge.label === 'string' ? edge.label : undefined,
    }));

    return {
      nodes: apiNodes,
      edges: apiEdges,
      metadata: {},
    };
  },

  // Load from API format
  fromApiStructure: (structure: TreeStructure) => {
    const nodes: TreeNode[] = structure.nodes.map((apiNode) => ({
      id: apiNode.id,
      type: 'treeNode',
      position: apiNode.position,
      data: {
        label: apiNode.label,
        nodeType: apiNode.type,
        config: apiNode.config,
        conditions: apiNode.conditions,
      },
    }));

    const edges: TreeEdge[] = structure.edges.map((apiEdge) => ({
      id: apiEdge.id,
      source: apiEdge.source,
      target: apiEdge.target,
      sourceHandle: apiEdge.source_handle || undefined,
      targetHandle: apiEdge.target_handle || undefined,
      label: apiEdge.label || undefined,
      type: 'colored',
    }));

    set({ nodes, edges });
  },
}));
