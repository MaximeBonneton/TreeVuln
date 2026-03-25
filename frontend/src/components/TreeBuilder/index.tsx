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
  const isAdminUser = useTreeStore((state) => state.isAdmin);

  // Load tree and list on mount
  useEffect(() => {
    loadTree();
    loadTrees();
  }, [loadTree, loadTrees]);

  // Keyboard shortcuts
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement;
      const isInput = target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.tagName === 'SELECT';

      // Ctrl/Cmd+S: Save (admin only)
      if ((e.ctrlKey || e.metaKey) && e.key === 's') {
        e.preventDefault();
        if (isAdminUser()) {
          saveTree();
        }
        return;
      }

      // Do not handle Delete/Escape if focus is in an input field
      if (isInput) return;

      // Delete/Backspace: Delete selected node or edge (admin only)
      if (e.key === 'Delete' || e.key === 'Backspace') {
        if (!isAdminUser()) return;
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

      // Escape: Deselect
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

  // Sync selected node with the store
  useEffect(() => {
    if (selectedNodeId) {
      const node = nodes.find((n) => n.id === selectedNodeId);
      setSelectedNode(node || null);
      setSelectedEdge(null); // Deselect edge when selecting a node
    } else {
      setSelectedNode(null);
    }
  }, [selectedNodeId, nodes]);

  // Update selected edge if edges change
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
    setSelectedEdge(null); // Deselect edge
  }, [selectNode]);

  const handleEdgeClick = useCallback((edge: TreeEdge) => {
    setSelectedEdge(edge);
    setSelectedNode(null);
    selectNode(null); // Deselect node
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
          {/* Tree sidebar */}
          <TreeSidebar
            onOpenCreateDialog={() => setShowCreateDialog(true)}
            onOpenApiConfig={() => setShowApiConfig(true)}
            onOpenAssetImport={() => setShowAssetImport(true)}
            onOpenWebhookConfig={() => setShowWebhookConfig(true)}
            onOpenIngestConfig={() => setShowIngestConfig(true)}
          />

          {/* Left palette */}
          <div className={`p-4 ${sidebarOpen ? '' : 'ml-8'}`}>
            <NodePalette onDragStart={handleDragStart} />
          </div>

          {/* Central canvas */}
          <Canvas onNodeClick={handleNodeClick} onEdgeClick={handleEdgeClick} />

          {/* Node config panel (right) */}
          {selectedNode && (
            <div className="p-4">
              <NodeConfigPanel
                key={selectedNode.id}
                node={selectedNode}
                onClose={handleCloseConfig}
              />
            </div>
          )}

          {/* Edge config panel (right) */}
          {selectedEdge && !selectedNode && (
            <div className="p-4">
              <EdgeConfigPanel
                key={selectedEdge.id}
                edge={selectedEdge}
                onClose={handleCloseEdgeConfig}
              />
            </div>
          )}

          {/* Test panel (right) */}
          {showTestPanel && (
            <TestPanel onClose={() => setShowTestPanel(false)} />
          )}
        </div>

        {/* Field mapping modal */}
        {showMappingPanel && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
            <FieldMappingPanel onClose={() => setShowMappingPanel(false)} />
          </div>
        )}

        {/* API configuration dialog */}
        {showApiConfig && (
          <ApiConfigDialog onClose={() => setShowApiConfig(false)} />
        )}

        {/* Tree creation dialog */}
        {showCreateDialog && (
          <CreateTreeDialog onClose={() => setShowCreateDialog(false)} />
        )}

        {/* Asset import dialog */}
        {showAssetImport && treeId && (
          <AssetImportDialog
            treeId={treeId}
            treeName={treeName}
            onClose={() => setShowAssetImport(false)}
            onImported={() => {}}
          />
        )}

        {/* Outgoing webhooks configuration dialog */}
        {showWebhookConfig && treeId && (
          <WebhookConfigDialog
            treeId={treeId}
            treeName={treeName}
            onClose={() => setShowWebhookConfig(false)}
          />
        )}

        {/* Incoming webhooks configuration dialog */}
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
