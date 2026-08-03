import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { useTreeStore } from '@/stores/treeStore';
import { TreeSelector } from '../TreeSelector';

vi.mock('@/components/dialogs/CreateTreeDialog', () => ({
  CreateTreeDialog: () => <div>create-tree-dialog</div>,
}));

const baseTree = {
  description: null,
  api_enabled: false,
  api_slug: null,
  node_count: 8,
  created_at: '2026-07-01T00:00:00Z',
  updated_at: '2026-07-01T00:00:00Z',
};

describe('TreeSelector', () => {
  const selectTree = vi.fn().mockResolvedValue(undefined);

  beforeEach(() => {
    selectTree.mockClear();
    useTreeStore.setState({
      currentUser: { id: '1', username: 'alice', role: 'admin' },
      trees: [
        { id: 1, name: 'SSVC Default', is_default: true, ...baseTree },
        { id: 2, name: 'Arbre Medical', is_default: false, ...baseTree },
      ],
      treeId: 1,
      treeName: 'SSVC Default',
      isDefault: true,
      hasUnsavedChanges: false,
      selectTree,
    });
  });

  it("affiche le nom de l'arbre courant", () => {
    render(<TreeSelector />);
    expect(screen.getByRole('button', { name: /SSVC Default/ })).toBeInTheDocument();
  });

  it('liste les arbres avec le badge défaut et sélectionne au clic', async () => {
    render(<TreeSelector />);
    await userEvent.click(screen.getByRole('button', { name: /SSVC Default/ }));
    expect(screen.getByText('défaut')).toBeInTheDocument();
    await userEvent.click(screen.getByText('Arbre Medical'));
    expect(selectTree).toHaveBeenCalledWith(2);
  });

  it('filtre la liste via la recherche', async () => {
    render(<TreeSelector />);
    await userEvent.click(screen.getByRole('button', { name: /SSVC Default/ }));
    await userEvent.type(screen.getByPlaceholderText('Rechercher un arbre…'), 'medical');
    expect(screen.queryByText('SSVC Default', { selector: 'span' })).not.toBeInTheDocument();
    expect(screen.getByText('Arbre Medical')).toBeInTheDocument();
  });

  it('ouvre le dialog de création via Nouvel arbre', async () => {
    render(<TreeSelector />);
    await userEvent.click(screen.getByRole('button', { name: /SSVC Default/ }));
    await userEvent.click(screen.getByRole('button', { name: /Nouvel arbre/ }));
    expect(screen.getByText('create-tree-dialog')).toBeInTheDocument();
  });

  it("masque les actions d'écriture pour un operator", async () => {
    useTreeStore.setState({
      currentUser: { id: '2', username: 'bob', role: 'operator' },
    });
    render(<TreeSelector />);
    await userEvent.click(screen.getByRole('button', { name: /SSVC Default/ }));
    expect(screen.queryByRole('button', { name: /Nouvel arbre/ })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /Dupliquer/ })).not.toBeInTheDocument();
  });
});
