import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { useTreeStore } from '@/stores/treeStore';
import { RequireAdmin } from '../RequireAdmin';

const admin = { id: '1', username: 'alice', role: 'admin' as const };
const operator = { id: '2', username: 'bob', role: 'operator' as const };

describe('RequireAdmin', () => {
  beforeEach(() => {
    useTreeStore.setState({ currentUser: null });
  });

  it('rend les enfants pour un admin', () => {
    useTreeStore.setState({ currentUser: admin });
    render(<RequireAdmin><div>contenu admin</div></RequireAdmin>);
    expect(screen.getByText('contenu admin')).toBeInTheDocument();
  });

  it('affiche « Accès restreint » pour un operator', () => {
    useTreeStore.setState({ currentUser: operator });
    render(<RequireAdmin><div>contenu admin</div></RequireAdmin>);
    expect(screen.queryByText('contenu admin')).not.toBeInTheDocument();
    expect(screen.getByText('Accès restreint')).toBeInTheDocument();
  });

  it('affiche « Accès restreint » sans utilisateur', () => {
    render(<RequireAdmin><div>contenu admin</div></RequireAdmin>);
    expect(screen.getByText('Accès restreint')).toBeInTheDocument();
  });
});
