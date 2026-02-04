/**
 * Client API pour le mapping des champs.
 */

import { api } from './client';
import type { FieldDefinition, FieldMapping, FieldMappingUpdate, ScanResult } from '@/types';

const API_BASE = '/api/v1';

export const fieldMappingApi = {
  /**
   * Récupère les définitions des champs CVSS virtuels.
   */
  getCvssFields: (): Promise<FieldDefinition[]> =>
    api.get<FieldDefinition[]>('/mapping/cvss-fields'),

  /**
   * Récupère le mapping des champs pour un arbre.
   */
  getMapping: (treeId: number): Promise<FieldMapping | null> =>
    api.get<FieldMapping | null>(`/tree/${treeId}/mapping`),

  /**
   * Met à jour le mapping des champs pour un arbre.
   */
  updateMapping: (treeId: number, data: FieldMappingUpdate): Promise<FieldMapping> =>
    api.put<FieldMapping>(`/tree/${treeId}/mapping`, data),

  /**
   * Importe un mapping depuis un fichier JSON.
   */
  importMapping: async (treeId: number, file: File): Promise<FieldMapping> => {
    const formData = new FormData();
    formData.append('file', file);

    const response = await fetch(`${API_BASE}/tree/${treeId}/mapping/import`, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Erreur inconnue' }));
      throw new Error(error.detail || 'Échec de l\'import');
    }

    return response.json();
  },

  /**
   * Supprime le mapping des champs pour un arbre.
   */
  deleteMapping: (treeId: number): Promise<void> =>
    api.delete<void>(`/tree/${treeId}/mapping`),

  /**
   * Scanne un fichier CSV ou JSON pour détecter les champs.
   */
  scanFile: async (file: File): Promise<ScanResult> => {
    const formData = new FormData();
    formData.append('file', file);

    const response = await fetch(`${API_BASE}/mapping/scan`, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Erreur inconnue' }));
      throw new Error(error.detail || 'Échec du scan');
    }

    return response.json();
  },
};
