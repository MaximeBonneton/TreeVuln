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
  // Evaluate a single vulnerability
  evaluateSingle: (data: SingleEvaluationRequest) =>
    api.post<EvaluationResult>('/evaluate/single', data),

  // Evaluate a batch of vulnerabilities
  evaluateBatch: (data: EvaluationRequest) =>
    api.post<EvaluationResponse>('/evaluate', data),

  // Evaluate a CSV file (upload)
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

  // Export an evaluated CSV file as CSV
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

  // Export a JSON batch as CSV or JSON
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

  // Preview: evaluate on an unsaved tree
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

  exportPreviewCsaf: async (
    file: File,
    structure: TreeStructure,
    treeId: number | null | undefined,
    signed: boolean,
  ): Promise<{ blob: Blob; filename: string }> => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('structure', JSON.stringify(structure));
    formData.append('format', 'csaf');
    formData.append('signed', String(signed));
    if (treeId) formData.append('tree_id', String(treeId));

    const response = await fetch('/api/v1/evaluate/preview/export/csv', {
      method: 'POST',
      credentials: 'same-origin',
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Export failed' }));
      throw new Error(
        typeof error.detail === 'string' ? error.detail : 'Export failed'
      );
    }

    // Nom de fichier {tracking_id}.zip fourni par le Content-Disposition
    const disposition = response.headers.get('Content-Disposition') ?? '';
    const match = disposition.match(/filename="([^"]+)"/);
    return {
      blob: await response.blob(),
      filename: match?.[1] ?? 'csaf_export.zip',
    };
  },

  // Diagnostic
  diagnoseTree: (structure: TreeStructure) =>
    api.post<DiagnosticResult>('/tree/diagnose', { structure }),
};
