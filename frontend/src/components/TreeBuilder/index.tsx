import { useState, useCallback, useEffect } from 'react';
import { ReactFlowProvider } from '@xyflow/react';

import { Canvas } from './Canvas';
import { Toolbar } from './Toolbar';
import { NodePalette } from '../panels/NodePalette';
import { NodeConfigPanel } from '../panels/NodeConfigPanel';
import { EdgeConfigPanel } from '../panels/EdgeConfigPanel';
import { TestPanel } from './TestPanel';
import { FieldMappingPanel } from '../panels/FieldMappingPanel';
import { useTreeStore } from '@/stores/treeStore';
import type { NodeType, TreeNode, TreeEdge } from '@/types';

export function TreeBuilder() {
  const [selectedNode, setSelectedNode] = useState<TreeNode | null>(null);
  const [selectedEdge, setSelectedEdge] = useState<TreeEdge | null>(null);
  const [showTestPanel, setShowTestPanel] = useState(false);
  const [showMappingPanel, setShowMappingPanel] = useState(false);

  const { nodes, edges, selectNode, error: storeError } = useTreeStore();
  const treeWarnings = useTreeStore((state) => state.treeWarnings);

  const saveTree = useTreeStore((state) => state.saveTree);
  const deleteNode = useTreeStore((state) => state.deleteNode);
  const deleteEdge = useTreeStore((state) => state.deleteEdge);
  const selectedNodeId = useTreeStore((state) => state.selectedNodeId);
  const isAdminUser = useTreeStore((state) => state.isAdmin);
  const undo = useTreeStore((state) => state.undo);
  const redo = useTreeStore((state) => state.redo);

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

      // Ctrl/Cmd+Z: Undo
      if ((e.ctrlKey || e.metaKey) && !e.shiftKey && e.key === 'z') {
        e.preventDefault();
        undo();
        return;
      }

      // Ctrl/Cmd+Shift+Z or Ctrl/Cmd+Y: Redo
      if ((e.ctrlKey || e.metaKey) && (
        (e.shiftKey && e.key === 'z') ||
        (e.shiftKey && e.key === 'Z') ||
        (!e.shiftKey && e.key === 'y')
      )) {
        e.preventDefault();
        redo();
        return;
      }

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
  }, [selectedNodeId, selectedEdge, saveTree, deleteNode, deleteEdge, selectNode, undo, redo]);

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
      <div className="h-full flex flex-col bg-slate-50">
        <Toolbar
          onTest={() => setShowTestPanel(true)}
          onOpenMapping={() => setShowMappingPanel(true)}
        />

        {/* Error banner */}
        {storeError && (
          <div className="bg-red-50 border-b border-red-200 px-4 py-2 text-sm text-red-700 flex items-center justify-between">
            <span>{storeError}</span>
            <button
              onClick={() => useTreeStore.setState({ error: null })}
              className="text-red-500 hover:text-red-700 font-medium ml-4"
            >
              Dismiss
            </button>
          </div>
        )}

        {/* Validation warnings banner (F-8, non-blocking) */}
        {treeWarnings.length > 0 && (
          <div className="bg-amber-50 border-b border-amber-200 px-4 py-2 text-sm text-amber-800 flex items-start justify-between">
            <div>
              <span className="font-medium">Tree saved with warnings:</span>
              <ul className="list-disc list-inside mt-1">
                {treeWarnings.map((w, i) => (
                  <li key={i}>{w}</li>
                ))}
              </ul>
            </div>
            <button
              onClick={() => useTreeStore.setState({ treeWarnings: [] })}
              className="text-amber-600 hover:text-amber-800 font-medium ml-4 shrink-0"
            >
              Dismiss
            </button>
          </div>
        )}

        <div className="flex-1 flex overflow-hidden">
          {/* Left palette */}
          <div className="p-4">
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
      </div>
    </ReactFlowProvider>
  );
}

export default TreeBuilder;
