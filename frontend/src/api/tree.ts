import { api, ApiError } from './client';
import type {
  TreeResponse,
  TreeCreate,
  TreeUpdate,
  TreeVersionResponse,
  TreeListItem,
  TreeApiConfig,
  TreeDuplicateRequest,
  TreeExportFile,
} from '@/types';

export const treeApi = {
  // --- Multi-tree ---

  // List all trees (summary)
  listTrees: () => api.get<TreeListItem[]>('/trees'),

  // Get a tree by ID or the default tree
  getTree: (treeId?: number) =>
    api.get<TreeResponse | null>(`/tree${treeId ? `?tree_id=${treeId}` : ''}`),

  // Create a new tree
  createTree: (data: TreeCreate) =>
    api.post<TreeResponse>('/tree', data),

  // Update a tree
  updateTree: (treeId: number, data: TreeUpdate, createVersion = true) =>
    api.put<TreeResponse>(`/tree/${treeId}?create_version=${createVersion}`, data),

  // Delete a tree
  deleteTree: (treeId: number) =>
    api.delete<void>(`/tree/${treeId}`),

  // Duplicate a tree
  duplicateTree: (treeId: number, data: TreeDuplicateRequest) =>
    api.post<TreeResponse>(`/tree/${treeId}/duplicate`, data),

  // Configure a tree's API
  updateApiConfig: (treeId: number, config: TreeApiConfig) =>
    api.put<TreeResponse>(`/tree/${treeId}/api-config`, config),

  // Set a tree as default
  setDefaultTree: (treeId: number) =>
    api.put<TreeResponse>(`/tree/${treeId}/set-default`),

  // --- Versioning ---

  // List tree versions
  getVersions: (treeId: number) =>
    api.get<TreeVersionResponse[]>(`/tree/${treeId}/versions`),

  // Get a specific version
  getVersion: (versionId: number) =>
    api.get<TreeVersionResponse>(`/tree/versions/${versionId}`),

  // Restore a version
  restoreVersion: (treeId: number, versionId: number) =>
    api.post<TreeResponse>(`/tree/${treeId}/restore/${versionId}`),

  // --- Decision-as-Code (export/import) ---

  // Export a tree (JSON file download)
  exportTree: async (treeId: number): Promise<void> => {
    const response = await fetch(`/api/v1/tree/${treeId}/export`, {
      credentials: 'same-origin',
    });
    if (!response.ok) throw new ApiError(response.status, 'Export failed');
    const blob = await response.blob();
    const disposition = response.headers.get('Content-Disposition');
    const filename = disposition?.match(/filename="(.+)"/)?.[1] ?? 'tree.json';
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  },

  // Import a tree from a Decision-as-Code file
  importTree: (data: TreeExportFile) =>
    api.post<TreeResponse>('/tree/import', data),
};
