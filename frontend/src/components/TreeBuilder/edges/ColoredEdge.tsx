import { memo } from 'react';
import {
  type Edge,
  type EdgeProps,
  Position,
} from '@xyflow/react';

// Palette of 24 slightly saturated and balanced colors
const EDGE_COLORS = [
  '#5b8fb9', // steel blue
  '#6a9e87', // sage green
  '#b08968', // warm tan
  '#8e7aa8', // purple
  '#5fa08e', // teal
  '#b8956c', // caramel
  '#6889a8', // slate blue
  '#8aab6e', // olive
  '#a07a94', // mauve
  '#5a9e9e', // cyan
  '#c9a66b', // gold
  '#7091ab', // blue gray
  '#7fa85e', // green
  '#a87088', // rose
  '#4fa89a', // sea green
  '#c4a05a', // mustard
  '#7a8fc0', // periwinkle
  '#6ba86b', // fern
  '#b88a98', // dusty pink
  '#5aaba3', // turquoise
  '#c9b06a', // wheat
  '#8095b8', // cornflower
  '#80b07a', // lime sage
  '#b8908a', // salmon
];

// Generate a simple hash from a string
const hashString = (str: string): number => {
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    const char = str.charCodeAt(i);
    hash = ((hash << 5) - hash) + char;
    hash = hash & hash;
  }
  return Math.abs(hash);
};

// Return a unique color based on the edge ID
export const getEdgeColor = (edgeId: string): string => {
  const hash = hashString(edgeId);
  return EDGE_COLORS[hash % EDGE_COLORS.length];
};

// Return a color based on the source node and handle index
export const getHandleColor = (nodeId: string, handleIndex: number): string => {
  const hash = hashString(`${nodeId}-handle-${handleIndex}`);
  return EDGE_COLORS[hash % EDGE_COLORS.length];
};

// Return a color for an edge based on its source (to match handles)
export const getEdgeColorFromSource = (sourceNodeId: string, sourceHandle: string | null | undefined): string => {
  if (!sourceHandle) return getHandleColor(sourceNodeId, 0);

  // Multi-input format: handle-{inputIdx}-{condIdx} -> hash based on full ID
  // Single-input format: handle-{index}
  const parts = sourceHandle.replace('handle-', '').split('-');
  if (parts.length === 2) {
    // Multi-input: use inputIdx * 100 + condIdx for a unique index
    const inputIdx = parseInt(parts[0], 10) || 0;
    const condIdx = parseInt(parts[1], 10) || 0;
    return getHandleColor(sourceNodeId, inputIdx * 100 + condIdx);
  }
  // Single-input
  const handleIndex = parseInt(parts[0], 10) || 0;
  return getHandleColor(sourceNodeId, handleIndex);
};

// Calculate an offset for control points (not endpoints)
const getControlPointOffset = (edgeId: string): number => {
  // Use only the edge hash for a light and unique offset
  const hash = hashString(edgeId);
  // Offset between -25 and +25 pixels to avoid overlapping curves
  return ((hash % 50) - 25);
};

// Generate a custom Bezier path with offset on control points only
const getCustomBezierPath = (
  sourceX: number,
  sourceY: number,
  targetX: number,
  targetY: number,
  sourcePosition: Position,
  targetPosition: Position,
  controlOffset: number
): string => {
  // Horizontal distance for control points
  const deltaX = Math.abs(targetX - sourceX);
  const controlDistance = Math.max(deltaX * 0.4, 50);

  // Control points with vertical offset
  let cp1x: number, cp1y: number, cp2x: number, cp2y: number;

  if (sourcePosition === Position.Right && targetPosition === Position.Left) {
    // Left-to-right connection (standard case)
    cp1x = sourceX + controlDistance;
    cp1y = sourceY + controlOffset;
    cp2x = targetX - controlDistance;
    cp2y = targetY + controlOffset * 0.5;
  } else if (sourcePosition === Position.Bottom && targetPosition === Position.Top) {
    // Top-to-bottom connection
    cp1x = sourceX + controlOffset;
    cp1y = sourceY + controlDistance;
    cp2x = targetX + controlOffset * 0.5;
    cp2y = targetY - controlDistance;
  } else {
    // Fallback for other cases
    cp1x = sourceX + controlDistance;
    cp1y = sourceY + controlOffset;
    cp2x = targetX - controlDistance;
    cp2y = targetY + controlOffset * 0.5;
  }

  return `M ${sourceX} ${sourceY} C ${cp1x} ${cp1y}, ${cp2x} ${cp2y}, ${targetX} ${targetY}`;
};

// Type for custom edge data
export interface ColoredEdgeData extends Record<string, unknown> {
  highlighted?: boolean;
  dimmed?: boolean;
}

// Custom edge type
export type ColoredEdge = Edge<ColoredEdgeData, 'colored'>;

function ColoredEdgeComponent({
  id,
  source,
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
  sourceHandleId,
  selected,
  data,
}: EdgeProps<ColoredEdge>) {
  // Calculate offset for control points (not endpoints)
  const controlOffset = getControlPointOffset(id);

  // Generate the path with endpoints aligned to handles
  const edgePath = getCustomBezierPath(
    sourceX,
    sourceY,
    targetX,
    targetY,
    sourcePosition,
    targetPosition,
    controlOffset
  );

  // Color based on source node + handle to match handles
  const color = getEdgeColorFromSource(source, sourceHandleId);
  const highlighted = data?.highlighted ?? false;
  const dimmed = data?.dimmed ?? false;

  // Calculate opacity and width based on state
  let strokeOpacity = 0.7;
  let strokeWidth = 1.5;

  if (highlighted) {
    strokeOpacity = 1;
    strokeWidth = 3.5;
  } else if (dimmed) {
    strokeOpacity = 0.08;
    strokeWidth = 1;
  }

  if (selected) {
    strokeWidth = 4;
    strokeOpacity = 1;
  }

  const strokeColor = selected ? '#3b82f6' : color;

  return (
    <>
      {/* Invisible wider path for better click target */}
      <path
        id={id}
        className="react-flow__edge-path"
        d={edgePath}
        fill="none"
        stroke="transparent"
        strokeWidth={20}
      />
      {/* Visible colored path */}
      <path
        d={edgePath}
        fill="none"
        stroke={strokeColor}
        strokeWidth={strokeWidth}
        strokeOpacity={strokeOpacity}
        style={{
          transition: 'stroke-opacity 0.2s ease, stroke-width 0.2s ease',
        }}
      />
    </>
  );
}

export default memo(ColoredEdgeComponent);
