import { api } from './client';
import type {
  IngestEndpoint,
  IngestEndpointCreate,
  IngestEndpointUpdate,
  IngestEndpointWithKey,
  IngestLog,
} from '@/types';

export const ingestApi = {
  list: (treeId: number) =>
    api.get<IngestEndpoint[]>(`/tree/${treeId}/ingest-endpoints`),

  create: (treeId: number, data: IngestEndpointCreate) =>
    api.post<IngestEndpointWithKey>(`/tree/${treeId}/ingest-endpoints`, data),

  update: (endpointId: number, data: IngestEndpointUpdate) =>
    api.put<IngestEndpoint>(`/ingest-endpoints/${endpointId}`, data),

  delete: (endpointId: number) =>
    api.delete(`/ingest-endpoints/${endpointId}`),

  regenerateKey: (endpointId: number) =>
    api.post<IngestEndpointWithKey>(`/ingest-endpoints/${endpointId}/regenerate-key`),

  getLogs: (endpointId: number, limit = 50) =>
    api.get<IngestLog[]>(`/ingest-endpoints/${endpointId}/logs?limit=${limit}`),
};
