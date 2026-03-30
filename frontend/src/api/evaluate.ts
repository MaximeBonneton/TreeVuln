import { api } from './client';
import type {
  SingleEvaluationRequest,
  EvaluationRequest,
  EvaluationResult,
  EvaluationResponse,
  PreviewEvaluationRequest,
  DiagnosticResult,
  TreeStructure,
} from '@/types';

export const evaluateApi = {
  // Évalue une vulnérabilité unique
  evaluateSingle: (data: SingleEvaluationRequest) =>
    api.post<EvaluationResult>('/evaluate/single', data),

  // Évalue un batch de vulnérabilités
  evaluateBatch: (data: EvaluationRequest) =>
    api.post<EvaluationResponse>('/evaluate', data),

  // Évalue un fichier CSV (upload)
  evaluateCsv: async (file: File, includePath = false): Promise<EvaluationResponse> => {
    const formData = new FormData();
    formData.append('file', file);

    const response = await fetch(
      `/api/v1/evaluate/csv?include_path=${includePath}`,
      {
        method: 'POST',
        credentials: 'same-origin',
        body: formData,
      }
    );

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Upload failed' }));
      throw new Error(error.detail);
    }

    return response.json();
  },

  // Exporte un fichier CSV évalué en CSV
  exportCsvFile: async (file: File, format: 'csv' | 'json' = 'csv'): Promise<Blob> => {
    const formData = new FormData();
    formData.append('file', file);

    const response = await fetch(
      `/api/v1/evaluate/export/csv?format=${format}`,
      {
        method: 'POST',
        credentials: 'same-origin',
        body: formData,
      }
    );

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Export failed' }));
      throw new Error(error.detail);
    }

    return response.blob();
  },

  // Exporte un batch JSON en CSV ou JSON
  exportBatch: async (
    data: EvaluationRequest & { format: 'csv' | 'json' },
  ): Promise<Blob> => {
    const response = await fetch('/api/v1/evaluate/export', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'same-origin',
      body: JSON.stringify(data),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Export failed' }));
      throw new Error(error.detail);
    }

    return response.blob();
  },

  // Preview : evalue sur un arbre non sauvegarde
  evaluatePreview: (data: PreviewEvaluationRequest) =>
    api.post<EvaluationResult>('/evaluate/preview', data),

  evaluatePreviewCsv: async (
    file: File,
    structure: TreeStructure,
    treeId?: number | null,
    includePath = true,
  ): Promise<EvaluationResponse> => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('structure', JSON.stringify(structure));
    if (treeId) formData.append('tree_id', String(treeId));
    if (!includePath) formData.append('include_path', 'false');

    const response = await fetch('/api/v1/evaluate/preview/csv', {
      method: 'POST',
      credentials: 'same-origin',
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Upload failed' }));
      throw new Error(error.detail);
    }

    return response.json();
  },

  exportPreviewCsv: async (
    file: File,
    structure: TreeStructure,
    format: 'csv' | 'json' = 'csv',
    treeId?: number | null,
  ): Promise<Blob> => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('structure', JSON.stringify(structure));
    formData.append('format', format);
    if (treeId) formData.append('tree_id', String(treeId));

    const response = await fetch('/api/v1/evaluate/preview/export/csv', {
      method: 'POST',
      credentials: 'same-origin',
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Export failed' }));
      throw new Error(error.detail);
    }

    return response.blob();
  },

  // Diagnostic
  diagnoseTree: (structure: TreeStructure) =>
    api.post<DiagnosticResult>('/tree/diagnose', { structure }),
};
