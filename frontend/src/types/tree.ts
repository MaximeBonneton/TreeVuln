import type { Node, Edge } from '@xyflow/react';
import type { FieldMapping } from './fieldMapping';

// Available node types
export type NodeType = 'input' | 'lookup' | 'output' | 'equation';

// Condition operators
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
  contains: 'contains',
  not_contains: 'does not contain',
  regex: 'regex',
  in: 'in',
  not_in: 'not in',
  is_null: 'is null',
  is_not_null: 'is not null',
};

// Simple criterion for compound condition
export interface SimpleConditionCriteria {
  /** Field to evaluate. If undefined, uses the node's main field */
  field?: string;
  operator: ConditionOperator;
  value: unknown;
}

// Branch condition (supports simple and compound mode)
export interface NodeCondition {
  label: string;
  // Simple mode (backward-compatible) - used if logic is undefined
  operator?: ConditionOperator;
  value?: unknown;
  // Compound mode - used if logic is defined
  logic?: 'AND' | 'OR';
  criteria?: SimpleConditionCriteria[];
}

// Node configuration based on type
export interface InputNodeConfig {
  field: string;
  default_branch?: number;
  /** Number of inputs (> 1 for multi-input mode) */
  input_count?: number;
}

export interface LookupNodeConfig {
  lookup_table: string;
  lookup_key: string;
  lookup_field: string;
  default_branch?: number;
  /** Number of inputs (> 1 for multi-input mode) */
  input_count?: number;
}

export interface OutputNodeConfig {
  decision: string;
  color: string;
}

export interface ValueMapEntry {
  text: string;
  value: number;
}

export interface ValueMap {
  entries: ValueMapEntry[];
  default_value: number;
}

export interface EquationNodeConfig {
  formula: string;
  variables: string[];
  output_label: string;
  default_branch?: number;
  value_maps?: Record<string, ValueMap>;
}

export type TreeNodeConfig = InputNodeConfig | LookupNodeConfig | OutputNodeConfig | EquationNodeConfig;

// Custom node data
export interface TreeNodeData extends Record<string, unknown> {
  label: string;
  nodeType: NodeType;
  config: TreeNodeConfig;
  conditions: NodeCondition[];
}

// Extended React Flow types
export type TreeNode = Node<TreeNodeData>;
export type TreeEdge = Edge;

// Complete tree structure (API format)
export interface TreeStructure {
  nodes: ApiNode[];
  edges: ApiEdge[];
  metadata: Record<string, unknown>;
}

// API format for nodes
export interface ApiNode {
  id: string;
  type: NodeType;
  label: string;
  position: { x: number; y: number };
  config: TreeNodeConfig;
  conditions: NodeCondition[];
}

// API format for edges
export interface ApiEdge {
  id: string;
  source: string;
  target: string;
  source_handle?: string | null;
  /** Input handle for multi-input nodes. Format: 'input-{index}' */
  target_handle?: string | null;
  label?: string | null;
}

// API response for a tree
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

// Tree summary for the list (sidebar)
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

// API configuration for a tree
export interface TreeApiConfig {
  api_enabled: boolean;
  api_slug: string | null;
}

// Tree duplication request
export interface TreeDuplicateRequest {
  new_name: string;
  include_assets: boolean;
}

// Tree creation/update
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

// Tree version
export interface TreeVersionResponse {
  id: number;
  tree_id: number;
  version_number: number;
  structure_snapshot: TreeStructure;
  comment: string | null;
  created_at: string;
}

// --- Decision-as-Code (export/import) ---

export interface TreeExportFile {
  format: 'treevuln-decision-tree';
  version: number;
  exported_at: string;
  tree: {
    name: string;
    description: string | null;
    structure: TreeStructure;
    field_mapping: FieldMapping | null;
  };
}
