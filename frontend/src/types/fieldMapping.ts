/**
 * Types pour le mapping des champs.
 */

/** Types de données supportés pour les champs */
export type FieldType = 'string' | 'number' | 'boolean' | 'date' | 'array' | 'unknown';

/** Labels pour les types de champs */
export const FIELD_TYPE_LABELS: Record<FieldType, string> = {
  string: 'Texte',
  number: 'Nombre',
  boolean: 'Booléen',
  date: 'Date',
  array: 'Liste',
  unknown: 'Inconnu',
};

/** Définition d'un champ disponible */
export interface FieldDefinition {
  /** Nom technique du champ (ex: cvss_score) */
  name: string;
  /** Label affiché (ex: Score CVSS) */
  label?: string;
  /** Type de données */
  type: FieldType;
  /** Description du champ */
  description?: string;
  /** Exemples de valeurs (max 5) */
  examples: (string | number | boolean)[];
  /** Champ obligatoire dans les vulnérabilités */
  required: boolean;
}

/** Mapping complet des champs pour un arbre */
export interface FieldMapping {
  /** Liste des champs disponibles */
  fields: FieldDefinition[];
  /** Origine du mapping: 'manual', 'import', 'scan:fichier.csv' */
  source?: string;
  /** Version du mapping */
  version: number;
}

/** Schéma pour la mise à jour du mapping */
export interface FieldMappingUpdate {
  fields: FieldDefinition[];
  source?: string;
}

/** Résultat du scan d'un fichier */
export interface ScanResult {
  /** Champs détectés */
  fields: FieldDefinition[];
  /** Nombre de lignes analysées */
  rows_scanned: number;
  /** Type de fichier: 'csv' ou 'json' */
  source_type: string;
  /** Avertissements éventuels */
  warnings: string[];
}
