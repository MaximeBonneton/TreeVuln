import ColoredEdgeComponent from './ColoredEdge';

export const edgeTypes = {
  colored: ColoredEdgeComponent,
};

export { getEdgeColor, getHandleColor, getEdgeColorFromSource } from './ColoredEdge';
export type { ColoredEdge, ColoredEdgeData } from './ColoredEdge';
