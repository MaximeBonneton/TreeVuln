import { memo } from 'react';
import {
  type Edge,
  type EdgeProps,
  Position,
} from '@xyflow/react';

// Palette de 24 couleurs légèrement saturées et équilibrées
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

// Génère un hash simple à partir d'une chaîne
const hashString = (str: string): number => {
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    const char = str.charCodeAt(i);
    hash = ((hash << 5) - hash) + char;
    hash = hash & hash;
  }
  return Math.abs(hash);
};

// Retourne une couleur unique basée sur l'ID de l'edge
export const getEdgeColor = (edgeId: string): string => {
  const hash = hashString(edgeId);
  return EDGE_COLORS[hash % EDGE_COLORS.length];
};

// Retourne une couleur basée sur le nœud source et l'index du handle
export const getHandleColor = (nodeId: string, handleIndex: number): string => {
  const hash = hashString(`${nodeId}-handle-${handleIndex}`);
  return EDGE_COLORS[hash % EDGE_COLORS.length];
};

// Retourne une couleur pour un edge basée sur sa source (pour correspondre aux handles)
export const getEdgeColorFromSource = (sourceNodeId: string, sourceHandle: string | null | undefined): string => {
  if (!sourceHandle) return getHandleColor(sourceNodeId, 0);

  // Format multi-input: handle-{inputIdx}-{condIdx} → hash basé sur l'ID complet
  // Format single-input: handle-{index}
  const parts = sourceHandle.replace('handle-', '').split('-');
  if (parts.length === 2) {
    // Multi-input: utiliser inputIdx * 100 + condIdx pour un index unique
    const inputIdx = parseInt(parts[0], 10) || 0;
    const condIdx = parseInt(parts[1], 10) || 0;
    return getHandleColor(sourceNodeId, inputIdx * 100 + condIdx);
  }
  // Single-input
  const handleIndex = parseInt(parts[0], 10) || 0;
  return getHandleColor(sourceNodeId, handleIndex);
};

// Calcule un offset pour les points de contrôle (pas les extrémités)
const getControlPointOffset = (edgeId: string): number => {
  // Utilise uniquement le hash de l'edge pour un offset léger et unique
  const hash = hashString(edgeId);
  // Offset entre -25 et +25 pixels pour éviter la superposition des courbes
  return ((hash % 50) - 25);
};

// Génère un path Bézier personnalisé avec offset sur les points de contrôle uniquement
const getCustomBezierPath = (
  sourceX: number,
  sourceY: number,
  targetX: number,
  targetY: number,
  sourcePosition: Position,
  targetPosition: Position,
  controlOffset: number
): string => {
  // Distance horizontale pour les points de contrôle
  const deltaX = Math.abs(targetX - sourceX);
  const controlDistance = Math.max(deltaX * 0.4, 50);

  // Points de contrôle avec offset vertical
  let cp1x: number, cp1y: number, cp2x: number, cp2y: number;

  if (sourcePosition === Position.Right && targetPosition === Position.Left) {
    // Connexion gauche-droite (cas standard)
    cp1x = sourceX + controlDistance;
    cp1y = sourceY + controlOffset;
    cp2x = targetX - controlDistance;
    cp2y = targetY + controlOffset * 0.5;
  } else if (sourcePosition === Position.Bottom && targetPosition === Position.Top) {
    // Connexion haut-bas
    cp1x = sourceX + controlOffset;
    cp1y = sourceY + controlDistance;
    cp2x = targetX + controlOffset * 0.5;
    cp2y = targetY - controlDistance;
  } else {
    // Fallback pour autres cas
    cp1x = sourceX + controlDistance;
    cp1y = sourceY + controlOffset;
    cp2x = targetX - controlDistance;
    cp2y = targetY + controlOffset * 0.5;
  }

  return `M ${sourceX} ${sourceY} C ${cp1x} ${cp1y}, ${cp2x} ${cp2y}, ${targetX} ${targetY}`;
};

// Type pour les données custom de l'edge
export interface ColoredEdgeData extends Record<string, unknown> {
  highlighted?: boolean;
  dimmed?: boolean;
}

// Type de l'edge custom
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
  // Calcule l'offset pour les points de contrôle (pas les extrémités)
  const controlOffset = getControlPointOffset(id);

  // Génère le path avec les extrémités alignées aux handles
  const edgePath = getCustomBezierPath(
    sourceX,
    sourceY,
    targetX,
    targetY,
    sourcePosition,
    targetPosition,
    controlOffset
  );

  // Couleur basée sur le nœud source + handle pour correspondre aux handles
  const color = getEdgeColorFromSource(source, sourceHandleId);
  const highlighted = data?.highlighted ?? false;
  const dimmed = data?.dimmed ?? false;

  // Calcule l'opacité et l'épaisseur selon l'état
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
