import { useCallback, useEffect, useRef, useMemo } from 'react';
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  type ReactFlowInstance,
  type Node,
  type Edge,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';

import { nodeTypes } from './nodes';
import { edgeTypes } from './edges';
import { useTreeStore } from '@/stores/treeStore';
import type { NodeType, TreeNode, TreeNodeData, TreeEdge } from '@/types';

interface CanvasProps {
  onNodeClick?: (node: TreeNode) => void;
  onEdgeClick?: (edge: TreeEdge) => void;
}

export function Canvas({ onNodeClick, onEdgeClick }: CanvasProps) {
  const reactFlowWrapper = useRef<HTMLDivElement>(null);
  const reactFlowInstance = useRef<ReactFlowInstance | null>(null);

  const {
    nodes,
    edges,
    onNodesChange,
    onEdgesChange,
    onConnect,
    addNode,
    hoveredNodeId,
    hoveredInputIndex,
    setHoveredNode,
  } = useTreeStore();

  const isAdminUser = useTreeStore((s) => s.isAdmin());
  const treeId = useTreeStore((s) => s.treeId);

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const onInit = useCallback((instance: any) => {
    reactFlowInstance.current = instance;
  }, []);

  // À l'arrivée sur un arbre (sélection dans la sidebar, import...), recentre
  // la vue sur l'ensemble des nœuds. Le prop fitView de ReactFlow ne joue
  // qu'au montage initial : sans cet effet, changer d'arbre conserve le
  // viewport de l'arbre précédent. rAF laisse ReactFlow mesurer les nouveaux
  // nœuds avant le cadrage.
  useEffect(() => {
    if (treeId === null) return;
    const frame = requestAnimationFrame(() => {
      reactFlowInstance.current?.fitView({ padding: 0.15, duration: 300 });
    });
    return () => cancelAnimationFrame(frame);
  }, [treeId]);

  const onDragOver = useCallback((event: React.DragEvent) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = 'move';
  }, []);

  const onDrop = useCallback(
    (event: React.DragEvent) => {
      event.preventDefault();

      const type = event.dataTransfer.getData('application/reactflow') as NodeType;
      if (!type || !reactFlowInstance.current || !reactFlowWrapper.current) {
        return;
      }

      const position = reactFlowInstance.current.screenToFlowPosition({
        x: event.clientX,
        y: event.clientY,
      });

      addNode(type, position);
    },
    [addNode]
  );

  const handleNodeClick = useCallback(
    (_: React.MouseEvent, node: Node<TreeNodeData>) => {
      onNodeClick?.(node as TreeNode);
    },
    [onNodeClick]
  );

  const handleEdgeClick = useCallback(
    (_: React.MouseEvent, edge: Edge) => {
      onEdgeClick?.(edge as TreeEdge);
    },
    [onEdgeClick]
  );

  // Handlers for node hover
  const handleNodeMouseEnter = useCallback(
    (_: React.MouseEvent, node: Node<TreeNodeData>) => {
      setHoveredNode(node.id);
    },
    [setHoveredNode]
  );

  const handleNodeMouseLeave = useCallback(() => {
    setHoveredNode(null);
  }, [setHoveredNode]);

  // Compute edges with colors and highlighting
  const styledEdges = useMemo(() => {
    return edges.map((edge) => {
      let isConnectedToHovered = false;

      if (hoveredNodeId !== null) {
        // Check if the edge is connected to the hovered node
        const isSourceMatch = edge.source === hoveredNodeId;
        const isTargetMatch = edge.target === hoveredNodeId;

        if (hoveredInputIndex !== null) {
          // Multi-input mode: filter by specific handle
          if (isSourceMatch) {
            // Outgoing edge: check if the sourceHandle matches the hovered input
            // Format: "handle-{inputIndex}-{conditionIndex}"
            const handlePrefix = `handle-${hoveredInputIndex}-`;
            isConnectedToHovered = edge.sourceHandle?.startsWith(handlePrefix) ?? false;
          }
          if (isTargetMatch) {
            // Incoming edge: check if the targetHandle matches the hovered input
            // Format: "input-{inputIndex}"
            const expectedHandle = `input-${hoveredInputIndex}`;
            isConnectedToHovered = isConnectedToHovered || edge.targetHandle === expectedHandle;
          }
        } else {
          // Standard mode: highlight all edges of the node
          isConnectedToHovered = isSourceMatch || isTargetMatch;
        }
      }

      return {
        ...edge,
        type: 'colored',
        data: {
          ...edge.data,
          highlighted: isConnectedToHovered,
          dimmed: hoveredNodeId !== null && !isConnectedToHovered,
        },
      };
    });
  }, [edges, hoveredNodeId, hoveredInputIndex]);

  return (
    <div ref={reactFlowWrapper} className="flex-1 h-full">
      <ReactFlow
        nodes={nodes}
        edges={styledEdges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        onInit={onInit}
        onDrop={onDrop}
        onDragOver={onDragOver}
        onNodeClick={handleNodeClick}
        onEdgeClick={handleEdgeClick}
        onNodeMouseEnter={handleNodeMouseEnter}
        onNodeMouseLeave={handleNodeMouseLeave}
        nodeTypes={nodeTypes}
        edgeTypes={edgeTypes}
        fitView
        snapToGrid
        snapGrid={[15, 15]}
        // F-2 : la suppression clavier native de React Flow contournait le
        // raccourci custom (undo state) et restait active pour les operators.
        // Delete/Backspace est géré exclusivement par useKeyboardShortcuts.
        deleteKeyCode={null}
        // F-2 : l'édition du canvas est réservée aux admins ; les operators
        // gardent la navigation (pan/zoom), le survol et les panneaux de test.
        nodesDraggable={isAdminUser}
        nodesConnectable={isAdminUser}
        elementsSelectable={isAdminUser}
        defaultEdgeOptions={{
          type: 'colored',
          animated: false,
        }}
      >
        <Background gap={15} size={1} />
        <Controls />
        <MiniMap
          nodeStrokeWidth={3}
          pannable
          zoomable
          className="!bg-gray-100"
        />
      </ReactFlow>
    </div>
  );
}
