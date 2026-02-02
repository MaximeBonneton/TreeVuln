import { useCallback, useRef } from 'react';
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

  return (
    <div ref={reactFlowWrapper} className="flex-1 h-full">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        onInit={onInit}
        onDrop={onDrop}
        onDragOver={onDragOver}
        onNodeClick={handleNodeClick}
        onEdgeClick={handleEdgeClick}
        nodeTypes={nodeTypes}
        fitView
        snapToGrid
        snapGrid={[15, 15]}
        defaultEdgeOptions={{
          type: 'smoothstep',
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
