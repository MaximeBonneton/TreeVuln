/**
 * API client for field mapping.
 */

import { api } from './client';
import type { FieldDefinition, FieldMapping, FieldMappingUpdate, ScanResult } from '@/types';

const API_BASE = '/api/v1';

export const fieldMappingApi = {
  /**
   * Get virtual CVSS field definitions.
   */
  getCvssFields: (): Promise<FieldDefinition[]> =>
    api.get<FieldDefinition[]>('/mapping/cvss-fields'),

  /**
   * Get field mapping for a tree.
   */
  getMapping: (treeId: number): Promise<FieldMapping | null> =>
    api.get<FieldMapping | null>(`/tree/${treeId}/mapping`),

  /**
   * Update field mapping for a tree.
   */
  updateMapping: (treeId: number, data: FieldMappingUpdate): Promise<FieldMapping> =>
    api.put<FieldMapping>(`/tree/${treeId}/mapping`, data),

  /**
   * Import a mapping from a JSON file.
   */
  importMapping: async (treeId: number, file: File): Promise<FieldMapping> => {
    const formData = new FormData();
    formData.append('file', file);

    const response = await fetch(`${API_BASE}/tree/${treeId}/mapping/import`, {
      method: 'POST',
      credentials: 'same-origin',
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
      throw new Error(error.detail || 'Import failed');
    }

    return response.json();
  },

  /**
   * Delete field mapping for a tree.
   */
  deleteMapping: (treeId: number): Promise<void> =>
    api.delete<void>(`/tree/${treeId}/mapping`),

  /**
   * Scan a CSV or JSON file to detect fields.
   */
  scanFile: async (file: File): Promise<ScanResult> => {
    const formData = new FormData();
    formData.append('file', file);

    const response = await fetch(`${API_BASE}/mapping/scan`, {
      method: 'POST',
      credentials: 'same-origin',
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
      throw new Error(error.detail || 'Scan failed');
    }

    return response.json();
  },
};
