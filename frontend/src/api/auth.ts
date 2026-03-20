import { api } from './client';

export interface AuthUser {
  id: string;
  username: string;
  role: 'admin' | 'operator';
}

export interface AuthStatus {
  status: 'setup_required' | 'unauthenticated' | 'authenticated' | 'must_change_password';
  user?: AuthUser;
}

export const authApi = {
  check: () => api.get<AuthStatus>('/auth/check'),
  setup: (username: string, password: string) =>
    api.post<AuthStatus>('/auth/setup', { username, password }),
  login: (username: string, password: string) =>
    api.post<AuthStatus>('/auth/login', { username, password }),
  logout: () => api.post('/auth/logout'),
  changePassword: (currentPassword: string, newPassword: string) =>
    api.post('/auth/change-password', { current_password: currentPassword, new_password: newPassword }),
};
