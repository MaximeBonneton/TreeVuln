import type { AssetImportResult, AssetImportPreview } from '@/types';

export const assetsApi = {
  previewImport: async (file: File): Promise<AssetImportPreview> => {
    const formData = new FormData();
    formData.append('file', file);

    const response = await fetch('/api/v1/assets/import/preview', {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Preview failed' }));
      throw new Error(error.detail);
    }

    return response.json();
  },

  importAssets: async (
    treeId: number,
    file: File,
    mapping: { asset_id: string; name?: string; criticality?: string },
  ): Promise<AssetImportResult> => {
    const formData = new FormData();
    formData.append('file', file);

    const params = new URLSearchParams();
    params.set('tree_id', String(treeId));
    params.set('col_asset_id', mapping.asset_id);
    if (mapping.name) params.set('col_name', mapping.name);
    if (mapping.criticality) params.set('col_criticality', mapping.criticality);

    const response = await fetch(`/api/v1/assets/import?${params.toString()}`, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Import failed' }));
      throw new Error(error.detail);
    }

    return response.json();
  },
};
