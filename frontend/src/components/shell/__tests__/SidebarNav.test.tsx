import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { useTreeStore } from '@/stores/treeStore';
import { SidebarNav } from '../SidebarNav';

vi.mock('@/api/enisa', () => ({
  getEnisaSummary: vi.fn().mockResolvedValue({
    candidates: 2,
    confirmed: 1,
    overdue_milestones: 1,
  }),
}));

const admin = { id: '1', username: 'alice', role: 'admin' as const };
const operator = { id: '2', username: 'bob', role: 'operator' as const };

function renderNav() {
  return render(
    <MemoryRouter initialEntries={['/builder']}>
      <SidebarNav />
    </MemoryRouter>
  );
}

describe('SidebarNav', () => {
  beforeEach(() => {
    useTreeStore.setState({ currentUser: admin, treeId: null });
  });

  it('affiche toutes les entrées de navigation', () => {
    renderNav();
    for (const label of ['Builder', 'Évaluation', 'CSAF', 'ENISA', 'Assets & SBOM', 'Intégrations']) {
      expect(screen.getByRole('link', { name: new RegExp(label) })).toBeInTheDocument();
    }
  });

  it('affiche la section Administration pour un admin', () => {
    renderNav();
    expect(screen.getByRole('link', { name: /Utilisateurs/ })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /Paramètres/ })).toBeInTheDocument();
  });

  it('masque la section Administration pour un operator', () => {
    useTreeStore.setState({ currentUser: operator });
    renderNav();
    expect(screen.queryByRole('link', { name: /Utilisateurs/ })).not.toBeInTheDocument();
    expect(screen.queryByText('Administration')).not.toBeInTheDocument();
  });

  it('affiche le badge ENISA (candidats + jalons en retard) quand un arbre est chargé', async () => {
    useTreeStore.setState({ treeId: 1 });
    renderNav();
    await waitFor(() => expect(screen.getByText('3')).toBeInTheDocument());
  });

  it('se replie en mode icônes (les libellés disparaissent)', async () => {
    renderNav();
    await userEvent.click(screen.getByRole('button', { name: /Replier la navigation/ }));
    expect(screen.queryByText('Évaluation')).not.toBeInTheDocument();
    // Les liens restent accessibles via aria-label
    expect(screen.getByRole('link', { name: /Évaluation/ })).toBeInTheDocument();
  });
});
