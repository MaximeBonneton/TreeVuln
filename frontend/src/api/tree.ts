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
  // --- Multi-arbres ---

  // Liste tous les arbres (résumé)
  listTrees: () => api.get<TreeListItem[]>('/trees'),

  // Récupère un arbre par ID ou l'arbre par défaut
  getTree: (treeId?: number) =>
    api.get<TreeResponse | null>(`/tree${treeId ? `?tree_id=${treeId}` : ''}`),

  // Crée un nouvel arbre
  createTree: (data: TreeCreate) =>
    api.post<TreeResponse>('/tree', data),

  // Met à jour un arbre
  updateTree: (treeId: number, data: TreeUpdate, createVersion = true) =>
    api.put<TreeResponse>(`/tree/${treeId}?create_version=${createVersion}`, data),

  // Supprime un arbre
  deleteTree: (treeId: number) =>
    api.delete<void>(`/tree/${treeId}`),

  // Duplique un arbre
  duplicateTree: (treeId: number, data: TreeDuplicateRequest) =>
    api.post<TreeResponse>(`/tree/${treeId}/duplicate`, data),

  // Configure l'API d'un arbre
  updateApiConfig: (treeId: number, config: TreeApiConfig) =>
    api.put<TreeResponse>(`/tree/${treeId}/api-config`, config),

  // Définit un arbre comme défaut
  setDefaultTree: (treeId: number) =>
    api.put<TreeResponse>(`/tree/${treeId}/set-default`),

  // --- Versioning ---

  // Liste les versions d'un arbre
  getVersions: (treeId: number) =>
    api.get<TreeVersionResponse[]>(`/tree/${treeId}/versions`),

  // Récupère une version spécifique
  getVersion: (versionId: number) =>
    api.get<TreeVersionResponse>(`/tree/versions/${versionId}`),

  // Restaure une version
  restoreVersion: (treeId: number, versionId: number) =>
    api.post<TreeResponse>(`/tree/${treeId}/restore/${versionId}`),

  // --- Decision-as-Code (export/import) ---

  // Exporte un arbre (téléchargement fichier JSON)
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

  // Importe un arbre depuis un fichier Decision-as-Code
  importTree: (data: TreeExportFile) =>
    api.post<TreeResponse>('/tree/import', data),
};
