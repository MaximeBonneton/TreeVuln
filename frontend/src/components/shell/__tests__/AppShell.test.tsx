import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { useTreeStore } from '@/stores/treeStore';
import { AppShell } from '../AppShell';

vi.mock('@/api/enisa', () => ({
  getEnisaSummary: vi.fn().mockResolvedValue({ candidates: 0, confirmed: 0, overdue_milestones: 0 }),
}));

function renderShell(initialEntry: string) {
  return render(
    <MemoryRouter initialEntries={[initialEntry]}>
      <Routes>
        <Route element={<AppShell />}>
          <Route path="/builder" element={<div>page-builder</div>} />
        </Route>
      </Routes>
    </MemoryRouter>
  );
}

describe('AppShell', () => {
  const loadTree = vi.fn().mockResolvedValue(undefined);
  const loadTrees = vi.fn().mockResolvedValue(undefined);
  const selectTree = vi.fn().mockResolvedValue(undefined);

  beforeEach(() => {
    loadTree.mockClear();
    loadTrees.mockClear();
    selectTree.mockClear();
    useTreeStore.setState({
      currentUser: { id: '1', username: 'alice', role: 'admin' },
      trees: [],
      treeId: null,
      treeName: '',
      loadTree,
      loadTrees,
      selectTree,
    });
  });

  it('rend la topbar, la navigation et le contenu de la route', () => {
    renderShell('/builder');
    expect(screen.getByText('TreeVuln')).toBeInTheDocument();
    expect(screen.getByRole('navigation', { name: 'Navigation principale' })).toBeInTheDocument();
    expect(screen.getByText('page-builder')).toBeInTheDocument();
  });

  it('charge la liste et l\'arbre par défaut sans ?tree=', async () => {
    renderShell('/builder');
    await waitFor(() => expect(loadTrees).toHaveBeenCalledOnce());
    expect(loadTree).toHaveBeenCalledOnce();
    expect(selectTree).not.toHaveBeenCalled();
  });

  it('sélectionne l\'arbre du query param ?tree=', async () => {
    renderShell('/builder?tree=7');
    await waitFor(() => expect(selectTree).toHaveBeenCalledWith(7));
    expect(loadTree).not.toHaveBeenCalled();
  });

  it('ignore un ?tree= invalide et charge l\'arbre par défaut', async () => {
    renderShell('/builder?tree=abc');
    await waitFor(() => expect(loadTree).toHaveBeenCalledOnce());
    expect(selectTree).not.toHaveBeenCalled();
  });
});
