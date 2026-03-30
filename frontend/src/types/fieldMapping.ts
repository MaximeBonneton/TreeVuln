/**
 * Types for field mapping.
 */

/** Supported data types for fields */
export type FieldType = 'string' | 'number' | 'boolean' | 'date' | 'array' | 'unknown';

/** Labels for field types */
export const FIELD_TYPE_LABELS: Record<FieldType, string> = {
  string: 'Text',
  number: 'Number',
  boolean: 'Boolean',
  date: 'Date',
  array: 'Array',
  unknown: 'Unknown',
};

/** Definition of an available field */
export interface FieldDefinition {
  /** Technical field name (e.g., cvss_score) */
  name: string;
  /** Displayed label (e.g., CVSS Score) */
  label?: string;
  /** Data type */
  type: FieldType;
  /** Field description */
  description?: string;
  /** Example values (max 5) */
  examples: (string | number | boolean)[];
  /** Required field in vulnerabilities */
  required: boolean;
}

/** Complete field mapping for a tree */
export interface FieldMapping {
  /** List of available fields */
  fields: FieldDefinition[];
  /** Mapping origin: 'manual', 'import', 'scan:file.csv' */
  source?: string;
  /** Mapping version */
  version: number;
}

/** Schema for mapping update */
export interface FieldMappingUpdate {
  fields: FieldDefinition[];
  source?: string;
}

/** File scan result */
export interface ScanResult {
  /** Detected fields */
  fields: FieldDefinition[];
  /** Number of rows analyzed */
  rows_scanned: number;
  /** File type: 'csv' or 'json' */
  source_type: string;
  /** Possible warnings */
  warnings: string[];
}
