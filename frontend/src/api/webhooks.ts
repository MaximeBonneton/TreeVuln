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

  update: (webhookId: number, data: WebhookUpdate) =>
    api.put<Webhook>(`/webhooks/${webhookId}`, data),

  delete: (webhookId: number) =>
    api.delete(`/webhooks/${webhookId}`),

  test: (webhookId: number) =>
    api.post<WebhookTestResult>(`/webhooks/${webhookId}/test`),

  getLogs: (webhookId: number, limit = 50) =>
    api.get<WebhookLog[]>(`/webhooks/${webhookId}/logs?limit=${limit}`),
};
