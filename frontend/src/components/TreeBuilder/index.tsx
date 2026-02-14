import { useState, useCallback, useEffect } from 'react';
import { ReactFlowProvider } from '@xyflow/react';

import { Canvas } from './Canvas';
import { Toolbar } from './Toolbar';
import { NodePalette } from '../panels/NodePalette';
import { NodeConfigPanel } from '../panels/NodeConfigPanel';
import { EdgeConfigPanel } from '../panels/EdgeConfigPanel';
import { TestPanel } from './TestPanel';
import { FieldMappingPanel } from '../panels/FieldMappingPanel';
import { TreeSidebar } from '../TreeSidebar';
import { ApiConfigDialog } from '../dialogs/ApiConfigDialog';
import { CreateTreeDialog } from '../dialogs/CreateTreeDialog';
import { AssetImportDialog } from '../dialogs/AssetImportDialog';
import { WebhookConfigDialog } from '../dialogs/WebhookConfigDialog';
import { IngestConfigDialog } from '../dialogs/IngestConfigDialog';
import { useTreeStore } from '@/stores/treeStore';
import type { NodeType, TreeNode, TreeEdge } from '@/types';

export function TreeBuilder() {
  const [selectedNode, setSelectedNode] = useState<TreeNode | null>(null);
  const [selectedEdge, setSelectedEdge] = useState<TreeEdge | null>(null);
  const [showTestPanel, setShowTestPanel] = useState(false);
  const [showMappingPanel, setShowMappingPanel] = useState(false);
  const [showApiConfig, setShowApiConfig] = useState(false);
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [showAssetImport, setShowAssetImport] = useState(false);
  const [showWebhookConfig, setShowWebhookConfig] = useState(false);
  const [showIngestConfig, setShowIngestConfig] = useState(false);

  const { nodes, edges, loadTree, loadTrees, selectNode, sidebarOpen, treeId, treeName } = useTreeStore();

  const saveTree = useTreeStore((state) => state.saveTree);
  const deleteNode = useTreeStore((state) => state.deleteNode);
  const deleteEdge = useTreeStore((state) => state.deleteEdge);
  const selectedNodeId = useTreeStore((state) => state.selectedNodeId);

  // Charge l'arbre et la liste au montage
  useEffect(() => {
    loadTree();
    loadTrees();
  }, [loadTree, loadTrees]);

  // Raccourcis clavier
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement;
      const isInput = target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.tagName === 'SELECT';

      // Ctrl/Cmd+S : Sauvegarder
      if ((e.ctrlKey || e.metaKey) && e.key === 's') {
        e.preventDefault();
        saveTree();
        return;
      }

      // Ne pas traiter Delete/Escape si focus dans un champ de saisie
      if (isInput) return;

      // Delete/Backspace : Supprimer nœud ou edge sélectionné
      if (e.key === 'Delete' || e.key === 'Backspace') {
        if (selectedNodeId) {
          deleteNode(selectedNodeId);
          selectNode(null);
          setSelectedNode(null);
        } else if (selectedEdge) {
          deleteEdge(selectedEdge.id);
          setSelectedEdge(null);
        }
        return;
      }

      // Escape : Désélectionner
      if (e.key === 'Escape') {
        selectNode(null);
        setSelectedNode(null);
        setSelectedEdge(null);
        return;
      }
    };

    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [selectedNodeId, selectedEdge, saveTree, deleteNode, deleteEdge, selectNode]);

  // Synchronise le nœud sélectionné avec le store
  useEffect(() => {
    if (selectedNodeId) {
      const node = nodes.find((n) => n.id === selectedNodeId);
      setSelectedNode(node || null);
      setSelectedEdge(null); // Deselectionne l'edge si on selectionne un noeud
    } else {
      setSelectedNode(null);
    }
  }, [selectedNodeId, nodes]);

  // Met a jour l'edge selectionne si les edges changent
  useEffect(() => {
    if (selectedEdge) {
      const edge = edges.find((e) => e.id === selectedEdge.id);
      if (!edge) {
        setSelectedEdge(null);
      }
    }
  }, [edges, selectedEdge]);

  const handleDragStart = useCallback(
    (event: React.DragEvent, nodeType: NodeType) => {
      event.dataTransfer.setData('application/reactflow', nodeType);
      event.dataTransfer.effectAllowed = 'move';
    },
    []
  );

  const handleNodeClick = useCallback((node: TreeNode) => {
    selectNode(node.id);
    setSelectedNode(node);
    setSelectedEdge(null); // Deselectionne l'edge
  }, [selectNode]);

  const handleEdgeClick = useCallback((edge: TreeEdge) => {
    setSelectedEdge(edge);
    setSelectedNode(null);
    selectNode(null); // Deselectionne le noeud
  }, [selectNode]);

  const handleCloseConfig = useCallback(() => {
    selectNode(null);
    setSelectedNode(null);
  }, [selectNode]);

  const handleCloseEdgeConfig = useCallback(() => {
    setSelectedEdge(null);
  }, []);

  return (
    <ReactFlowProvider>
      <div className="h-screen flex flex-col bg-gray-50">
        <Toolbar
          onTest={() => setShowTestPanel(true)}
          onOpenMapping={() => setShowMappingPanel(true)}
        />

        <div className="flex-1 flex overflow-hidden">
          {/* Sidebar des arbres */}
          <TreeSidebar
            onOpenCreateDialog={() => setShowCreateDialog(true)}
            onOpenApiConfig={() => setShowApiConfig(true)}
            onOpenAssetImport={() => setShowAssetImport(true)}
            onOpenWebhookConfig={() => setShowWebhookConfig(true)}
            onOpenIngestConfig={() => setShowIngestConfig(true)}
          />

          {/* Palette gauche */}
          <div className={`p-4 ${sidebarOpen ? '' : 'ml-8'}`}>
            <NodePalette onDragStart={handleDragStart} />
          </div>

          {/* Canvas central */}
          <Canvas onNodeClick={handleNodeClick} onEdgeClick={handleEdgeClick} />

          {/* Panel de configuration noeud (droit) */}
          {selectedNode && (
            <div className="p-4">
              <NodeConfigPanel
                key={selectedNode.id}
                node={selectedNode}
                onClose={handleCloseConfig}
              />
            </div>
          )}

          {/* Panel de configuration edge (droit) */}
          {selectedEdge && !selectedNode && (
            <div className="p-4">
              <EdgeConfigPanel
                key={selectedEdge.id}
                edge={selectedEdge}
                onClose={handleCloseEdgeConfig}
              />
            </div>
          )}

          {/* Panel de test (droit) */}
          {showTestPanel && (
            <TestPanel onClose={() => setShowTestPanel(false)} />
          )}
        </div>

        {/* Modal de mapping des champs */}
        {showMappingPanel && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
            <FieldMappingPanel onClose={() => setShowMappingPanel(false)} />
          </div>
        )}

        {/* Dialog de configuration API */}
        {showApiConfig && (
          <ApiConfigDialog onClose={() => setShowApiConfig(false)} />
        )}

        {/* Dialog de création d'arbre */}
        {showCreateDialog && (
          <CreateTreeDialog onClose={() => setShowCreateDialog(false)} />
        )}

        {/* Dialog d'import d'assets */}
        {showAssetImport && treeId && (
          <AssetImportDialog
            treeId={treeId}
            treeName={treeName}
            onClose={() => setShowAssetImport(false)}
            onImported={() => {}}
          />
        )}

        {/* Dialog de configuration webhooks sortants */}
        {showWebhookConfig && treeId && (
          <WebhookConfigDialog
            treeId={treeId}
            treeName={treeName}
            onClose={() => setShowWebhookConfig(false)}
          />
        )}

        {/* Dialog de configuration webhooks entrants */}
        {showIngestConfig && treeId && (
          <IngestConfigDialog
            treeId={treeId}
            treeName={treeName}
            onClose={() => setShowIngestConfig(false)}
          />
        )}
      </div>
    </ReactFlowProvider>
  );
}

export default TreeBuilder;
