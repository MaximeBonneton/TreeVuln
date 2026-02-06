import type { Node, Edge } from '@xyflow/react';

// Types de nœuds disponibles
export type NodeType = 'input' | 'lookup' | 'output';

// Opérateurs de condition
export type ConditionOperator =
  | 'eq'
  | 'neq'
  | 'gt'
  | 'gte'
  | 'lt'
  | 'lte'
  | 'contains'
  | 'not_contains'
  | 'regex'
  | 'in'
  | 'not_in'
  | 'is_null'
  | 'is_not_null';

export const OPERATOR_LABELS: Record<ConditionOperator, string> = {
  eq: '=',
  neq: '≠',
  gt: '>',
  gte: '≥',
  lt: '<',
  lte: '≤',
  contains: 'contient',
  not_contains: 'ne contient pas',
  regex: 'regex',
  in: 'dans',
  not_in: 'pas dans',
  is_null: 'est vide',
  is_not_null: 'n\'est pas vide',
};

// Critère simple pour condition composée
export interface SimpleConditionCriteria {
  /** Champ à évaluer. Si undefined, utilise le champ principal du nœud */
  field?: string;
  operator: ConditionOperator;
  value: unknown;
}

// Condition d'une branche (supporte mode simple et composé)
export interface NodeCondition {
  label: string;
  // Mode simple (rétrocompatible) - utilisé si logic est undefined
  operator?: ConditionOperator;
  value?: unknown;
  // Mode composé - utilisé si logic est défini
  logic?: 'AND' | 'OR';
  criteria?: SimpleConditionCriteria[];
}

// Configuration des nœuds selon le type
export interface InputNodeConfig {
  field: string;
  default_branch?: number;
  /** Nombre d'entrées (> 1 pour mode multi-input) */
  input_count?: number;
}

export interface LookupNodeConfig {
  lookup_table: string;
  lookup_key: string;
  lookup_field: string;
  default_branch?: number;
  /** Nombre d'entrées (> 1 pour mode multi-input) */
  input_count?: number;
}

export interface OutputNodeConfig {
  decision: string;
  color: string;
}

export type TreeNodeConfig = InputNodeConfig | LookupNodeConfig | OutputNodeConfig;

// Données d'un nœud custom
export interface TreeNodeData extends Record<string, unknown> {
  label: string;
  nodeType: NodeType;
  config: TreeNodeConfig;
  conditions: NodeCondition[];
}

// Types React Flow étendus
export type TreeNode = Node<TreeNodeData>;
export type TreeEdge = Edge;

// Structure complète de l'arbre (format API)
export interface TreeStructure {
  nodes: ApiNode[];
  edges: ApiEdge[];
  metadata: Record<string, unknown>;
}

// Format API des nœuds
export interface ApiNode {
  id: string;
  type: NodeType;
  label: string;
  position: { x: number; y: number };
  config: TreeNodeConfig;
  conditions: NodeCondition[];
}

// Format API des edges
export interface ApiEdge {
  id: string;
  source: string;
  target: string;
  source_handle?: string | null;
  /** Handle d'entrée pour les nœuds multi-input. Format: 'input-{index}' */
  target_handle?: string | null;
  label?: string | null;
}

// Réponse API pour un arbre
export interface TreeResponse {
  id: number;
  name: string;
  description: string | null;
  structure: TreeStructure;
  is_default: boolean;
  api_enabled: boolean;
  api_slug: string | null;
  created_at: string;
  updated_at: string;
}

// Résumé d'un arbre pour la liste (sidebar)
export interface TreeListItem {
  id: number;
  name: string;
  description: string | null;
  is_default: boolean;
  api_enabled: boolean;
  api_slug: string | null;
  node_count: number;
  created_at: string;
  updated_at: string;
}

// Configuration API d'un arbre
export interface TreeApiConfig {
  api_enabled: boolean;
  api_slug: string | null;
}

// Requête de duplication d'arbre
export interface TreeDuplicateRequest {
  new_name: string;
  include_assets: boolean;
}

// Création/mise à jour d'un arbre
export interface TreeCreate {
  name: string;
  description?: string;
  structure: TreeStructure;
}

export interface TreeUpdate {
  name?: string;
  description?: string;
  structure?: TreeStructure;
  version_comment?: string;
}

// Version d'arbre
export interface TreeVersionResponse {
  id: number;
  tree_id: number;
  version_number: number;
  structure_snapshot: TreeStructure;
  comment: string | null;
  created_at: string;
}
