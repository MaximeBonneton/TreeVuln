import { api } from './client';

export interface UserResponse {
  id: string;
  username: string;
  email: string | null;
  role: 'admin' | 'operator';
  is_active: boolean;
  must_change_pwd: boolean;
  created_at: string;
  updated_at: string;
}

export const usersApi = {
  list: () => api.get<UserResponse[]>('/users'),
  create: (data: { username: string; password: string; role: string; email?: string }) =>
    api.post<UserResponse>('/users', data),
  update: (id: string, data: { role?: string; is_active?: boolean; email?: string }) =>
    api.put<UserResponse>(`/users/${id}`, data),
  delete: (id: string) => api.delete(`/users/${id}`),
  resetPassword: (id: string, newPassword: string) =>
    api.post(`/users/${id}/reset-password`, { new_password: newPassword }),
};
