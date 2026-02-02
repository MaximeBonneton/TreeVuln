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
};
