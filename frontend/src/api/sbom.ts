import { api } from './client';

export interface SbomComponent {
  purl: string | null;
  name: string;
  version: string | null;
  component_type: string | null;
}

export interface SbomMeta {
  format: string;
  spec_version: string;
  filename: string | null;
  component_count: number;
  imported_at: string;
  warnings: string[];
}

export interface SbomDetail extends SbomMeta {
  components: SbomComponent[];
  total_components: number;
}

export interface SbomSummaryItem {
  asset_id: string;
  format: string;
  component_count: number;
  imported_at: string;
}

export const sbomApi = {
  getSummary: (treeId: number) =>
    api.get<SbomSummaryItem[]>(`/assets/sbom/summary?tree_id=${treeId}`),

  getSbom: (assetId: string, treeId: number, limit = 1000) =>
    api.get<SbomDetail>(
      `/assets/${encodeURIComponent(assetId)}/sbom?tree_id=${treeId}&limit=${limit}`
    ),

  uploadSbom: async (
    assetId: string,
    treeId: number,
    file: File
  ): Promise<SbomMeta> => {
    const formData = new FormData();
    formData.append('file', file);
    const response = await fetch(
      `/api/v1/assets/${encodeURIComponent(assetId)}/sbom?tree_id=${treeId}`,
      { method: 'POST', credentials: 'same-origin', body: formData }
    );
    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Upload failed' }));
      throw new Error(
        typeof error.detail === 'string' ? error.detail : 'Upload failed'
      );
    }
    return response.json();
  },

  deleteSbom: (assetId: string, treeId: number) =>
    api.delete<void>(`/assets/${encodeURIComponent(assetId)}/sbom?tree_id=${treeId}`),
};
