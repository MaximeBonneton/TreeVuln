import { useCallback, useRef, useMemo } from 'react';
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

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const onInit = useCallback((instance: any) => {
    reactFlowInstance.current = instance;
  }, []);

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

      const bounds = reactFlowWrapper.current.getBoundingClientRect();
      const position = reactFlowInstance.current.screenToFlowPosition({
        x: event.clientX - bounds.left,
        y: event.clientY - bounds.top,
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

  // Handlers pour le survol des nœuds
  const handleNodeMouseEnter = useCallback(
    (_: React.MouseEvent, node: Node<TreeNodeData>) => {
      setHoveredNode(node.id);
    },
    [setHoveredNode]
  );

  const handleNodeMouseLeave = useCallback(() => {
    setHoveredNode(null);
  }, [setHoveredNode]);

  // Calcule les edges avec couleurs et highlighting
  const styledEdges = useMemo(() => {
    return edges.map((edge) => {
      let isConnectedToHovered = false;

      if (hoveredNodeId !== null) {
        // Vérifie si l'edge est connecté au nœud survolé
        const isSourceMatch = edge.source === hoveredNodeId;
        const isTargetMatch = edge.target === hoveredNodeId;

        if (hoveredInputIndex !== null) {
          // Mode multi-input : filtrer par handle spécifique
          if (isSourceMatch) {
            // Edge sortant : vérifier si le sourceHandle correspond à l'entrée survolée
            // Format: "handle-{inputIndex}-{conditionIndex}"
            const handlePrefix = `handle-${hoveredInputIndex}-`;
            isConnectedToHovered = edge.sourceHandle?.startsWith(handlePrefix) ?? false;
          }
          if (isTargetMatch) {
            // Edge entrant : vérifier si le targetHandle correspond à l'entrée survolée
            // Format: "input-{inputIndex}"
            const expectedHandle = `input-${hoveredInputIndex}`;
            isConnectedToHovered = isConnectedToHovered || edge.targetHandle === expectedHandle;
          }
        } else {
          // Mode standard : highlighter tous les edges du nœud
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
