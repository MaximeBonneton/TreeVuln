import { api } from './client';
import type {
  SingleEvaluationRequest,
  EvaluationRequest,
  EvaluationResult,
  EvaluationResponse,
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
      body: JSON.stringify(data),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Export failed' }));
      throw new Error(error.detail);
    }

    return response.blob();
  },
};
