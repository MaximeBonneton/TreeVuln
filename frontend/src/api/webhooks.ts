import { api } from './client';
import type {
  Webhook,
  WebhookCreate,
  WebhookUpdate,
  WebhookLog,
  WebhookTestResult,
} from '@/types';

export const webhooksApi = {
  list: (treeId: number) =>
    api.get<Webhook[]>(`/tree/${treeId}/webhooks`),

  create: (treeId: number, data: WebhookCreate) =>
    api.post<Webhook>(`/tree/${treeId}/webhooks`, data),

  update: (treeId: number, webhookId: number, data: WebhookUpdate) =>
    api.put<Webhook>(`/tree/${treeId}/webhooks/${webhookId}`, data),

  delete: (treeId: number, webhookId: number) =>
    api.delete(`/tree/${treeId}/webhooks/${webhookId}`),

  test: (treeId: number, webhookId: number) =>
    api.post<WebhookTestResult>(`/tree/${treeId}/webhooks/${webhookId}/test`),

  getLogs: (treeId: number, webhookId: number, limit = 50) =>
    api.get<WebhookLog[]>(`/tree/${treeId}/webhooks/${webhookId}/logs?limit=${limit}`),
};
