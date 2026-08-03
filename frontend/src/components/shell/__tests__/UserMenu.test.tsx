import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { useTreeStore } from '@/stores/treeStore';
import { UserMenu } from '../UserMenu';
import { authApi } from '@/api/auth';

vi.mock('@/api/auth', () => ({
  authApi: { logout: vi.fn().mockResolvedValue(undefined) },
}));

// ChangePasswordDialog fait des appels API : on le remplace par un marqueur
vi.mock('@/components/ChangePasswordDialog', () => ({
  default: () => <div>change-password-dialog</div>,
}));

describe('UserMenu', () => {
  beforeEach(() => {
    useTreeStore.setState({
      currentUser: { id: '1', username: 'alice', role: 'admin' },
    });
  });

  it('affiche le nom et le rôle de l\'utilisateur dans le menu', async () => {
    render(<UserMenu />);
    await userEvent.click(screen.getByRole('button', { name: /Menu utilisateur/ }));
    expect(screen.getByText('alice')).toBeInTheDocument();
    expect(screen.getByText('admin')).toBeInTheDocument();
  });

  it('ouvre le dialog de changement de mot de passe', async () => {
    render(<UserMenu />);
    await userEvent.click(screen.getByRole('button', { name: /Menu utilisateur/ }));
    await userEvent.click(screen.getByRole('button', { name: /Changer le mot de passe/ }));
    expect(screen.getByText('change-password-dialog')).toBeInTheDocument();
  });

  it('appelle authApi.logout à la déconnexion', async () => {
    render(<UserMenu />);
    await userEvent.click(screen.getByRole('button', { name: /Menu utilisateur/ }));
    await userEvent.click(screen.getByRole('button', { name: /Déconnexion/ }));
    expect(authApi.logout).toHaveBeenCalledOnce();
  });
});
