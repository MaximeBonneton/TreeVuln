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

interface TreeState {
  // Multi-arbres
  trees: TreeListItem[];
  isDefault: boolean;
  apiEnabled: boolean;
  apiSlug: string | null;

  // Données de l'arbre courant
  treeId: number | null;
  treeName: string;
  treeDescription: string;

  // Nœuds et edges React Flow
  nodes: TreeNode[];
  edges: TreeEdge[];

  // Field mapping
  fieldMapping: FieldMapping | null;

  // État UI
  selectedNodeId: string | null;
  hoveredNodeId: string | null;
  hoveredInputIndex: number | null; // Pour les nœuds multi-input
  isLoading: boolean;
  isSaving: boolean;
  hasUnsavedChanges: boolean;
  error: string | null;
  sidebarOpen: boolean;

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

  // Multi-arbres actions
  loadTrees: () => Promise<void>;
  selectTree: (treeId: number) => Promise<void>;
  duplicateTree: (treeId: number, options: TreeDuplicateRequest) => Promise<void>;
  updateApiConfig: (config: TreeApiConfig) => Promise<void>;
  setAsDefault: () => Promise<void>;
  deleteCurrentTree: () => Promise<void>;
  setSidebarOpen: (open: boolean) => void;

  // Conversion
  toApiStructure: () => TreeStructure;
  fromApiStructure: (structure: TreeStructure) => void;
}

// Génère un ID unique pour les nœuds
const generateNodeId = (type: NodeType) =>
  `${type}-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;

// Génère un ID unique pour les edges
const generateEdgeId = () =>
  `edge-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;

// Configuration par défaut selon le type de nœud
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

// Label par défaut selon le type
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
  // État initial
  trees: [],
  isDefault: false,
  apiEnabled: false,
  apiSlug: null,
  treeId: null,
  treeName: 'Nouvel arbre',
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

  // Setters de base
  setNodes: (nodes) => set({ nodes, hasUnsavedChanges: true }),
  setEdges: (edges) => set({ edges, hasUnsavedChanges: true }),

  // Handlers React Flow
  onNodesChange: (changes) => {
    // Filtre les changements significatifs (vrais déplacements ou modifications)
    // - position avec dragging=true = en train de déplacer
    // - remove/add = suppression/ajout
    // On ignore: select, dimensions, position avec dragging=false (init)
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

  // Ajoute un nouveau nœud
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

  // Duplique un nœud existant
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

  // Met à jour les données d'un nœud
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

  // Supprime un nœud et ses edges associées
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

  // Supprime une edge
  deleteEdge: (edgeId) => {
    set((state) => ({
      edges: state.edges.filter((e) => e.id !== edgeId),
      hasUnsavedChanges: true,
    }));
  },

  // Sélectionne un nœud
  selectNode: (nodeId) => set({ selectedNodeId: nodeId }),

  // Survole un nœud (pour le highlighting des edges)
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
      console.error('Erreur chargement mapping:', err);
    }
  },

  saveFieldMapping: async (fields, source = 'manual') => {
    const { treeId } = get();
    if (!treeId) return;

    try {
      const mapping = await fieldMappingApi.updateMapping(treeId, { fields, source });
      set({ fieldMapping: mapping });
    } catch (err) {
      console.error('Erreur sauvegarde mapping:', err);
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
      console.error('Erreur suppression mapping:', err);
      throw err;
    }
  },

  // Charge l'arbre depuis l'API
  loadTree: async (treeId?: number) => {
    set({ isLoading: true, error: null });
    try {
      const tree = await treeApi.getTree(treeId);
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
        // Charge le mapping des champs
        await get().loadFieldMapping();
      }
    } catch (err) {
      set({ error: err instanceof Error ? err.message : 'Erreur de chargement' });
    } finally {
      set({ isLoading: false });
    }
  },

  // Sauvegarde l'arbre
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
      set({ error: err instanceof Error ? err.message : 'Erreur de sauvegarde' });
      throw err;
    } finally {
      set({ isSaving: false });
    }
  },

  // Crée un nouvel arbre vide
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

  // --- Multi-arbres ---

  // Charge la liste des arbres
  loadTrees: async () => {
    try {
      const trees = await treeApi.listTrees();
      set({ trees });
    } catch (err) {
      console.error('Erreur chargement liste arbres:', err);
    }
  },

  // Sélectionne et charge un arbre
  selectTree: async (treeId: number) => {
    await get().loadTree(treeId);
    // Recharge la liste pour refléter les changements
    await get().loadTrees();
  },

  // Duplique un arbre
  duplicateTree: async (treeId: number, options: TreeDuplicateRequest) => {
    set({ isLoading: true, error: null });
    try {
      const newTree = await treeApi.duplicateTree(treeId, options);
      // Recharge la liste et sélectionne le nouvel arbre
      await get().loadTrees();
      await get().loadTree(newTree.id);
    } catch (err) {
      set({ error: err instanceof Error ? err.message : 'Erreur de duplication' });
      throw err;
    } finally {
      set({ isLoading: false });
    }
  },

  // Met à jour la configuration API
  updateApiConfig: async (config: TreeApiConfig) => {
    const { treeId } = get();
    if (!treeId) return;

    try {
      const tree = await treeApi.updateApiConfig(treeId, config);
      set({
        apiEnabled: tree.api_enabled,
        apiSlug: tree.api_slug,
      });
      // Recharge la liste pour refléter les changements
      await get().loadTrees();
    } catch (err) {
      set({ error: err instanceof Error ? err.message : 'Erreur de configuration API' });
      throw err;
    }
  },

  // Définit l'arbre courant comme défaut
  setAsDefault: async () => {
    const { treeId } = get();
    if (!treeId) return;

    try {
      await treeApi.setDefaultTree(treeId);
      set({ isDefault: true });
      // Recharge la liste pour refléter les changements
      await get().loadTrees();
    } catch (err) {
      set({ error: err instanceof Error ? err.message : 'Erreur définition défaut' });
      throw err;
    }
  },

  // Supprime l'arbre courant
  deleteCurrentTree: async () => {
    const { treeId, isDefault } = get();
    if (!treeId) return;
    if (isDefault) {
      set({ error: 'Impossible de supprimer l\'arbre par défaut' });
      return;
    }

    try {
      await treeApi.deleteTree(treeId);
      // Recharge la liste et sélectionne l'arbre par défaut
      await get().loadTrees();
      await get().loadTree();
    } catch (err) {
      set({ error: err instanceof Error ? err.message : 'Erreur de suppression' });
      throw err;
    }
  },

  // Toggle sidebar
  setSidebarOpen: (open: boolean) => set({ sidebarOpen: open }),

  // Convertit vers le format API
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

  // Charge depuis le format API
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
