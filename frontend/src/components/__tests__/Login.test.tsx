import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Login } from '../Login';

const login = vi.fn();
vi.mock('@/api/auth', () => ({
  authApi: { login: (...args: unknown[]) => login(...args) },
}));

describe('Login (réhabillé aux tokens)', () => {
  it('rend la card claire avec le logo et le bouton indigo du kit', () => {
    const { container } = render(<Login onLogin={() => {}} />);
    expect(screen.getByText('TreeVuln')).toBeInTheDocument();
    // Plus aucune classe du thème sombre ni de blue-* hors tokens
    expect(container.innerHTML).not.toMatch(/bg-gray-|text-gray-|bg-blue-/);
    expect(screen.getByRole('button', { name: /Sign in/ })).toBeInTheDocument();
  });

  it('soumet les identifiants et appelle onLogin', async () => {
    login.mockResolvedValue({ status: 'authenticated' });
    const onLogin = vi.fn();
    render(<Login onLogin={onLogin} />);
    await userEvent.type(screen.getByLabelText('Username'), 'alice');
    await userEvent.type(screen.getByLabelText('Password'), 'secret');
    await userEvent.click(screen.getByRole('button', { name: /Sign in/ }));
    expect(login).toHaveBeenCalledWith('alice', 'secret');
    expect(onLogin).toHaveBeenCalledOnce();
  });
});
