import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { useTreeStore } from '@/stores/treeStore';
import { EvaluatePage } from '../EvaluatePage';
import { IntegrationsPage } from '../IntegrationsPage';
import { AdminUsersPage } from '../AdminUsersPage';

// Les vues existantes font des appels API : remplacées par des marqueurs
vi.mock('@/components/TreeBuilder/TestPanel', () => ({
  TestPanel: () => <div>test-panel</div>,
}));
vi.mock('@/components/integrations/WebhooksSection', () => ({
  WebhooksSection: () => <div>webhooks-section</div>,
}));
vi.mock('@/components/integrations/IngestSection', () => ({
  IngestSection: () => <div>ingest-section</div>,
}));
vi.mock('@/components/panels/UsersPanel', () => ({
  UsersPanel: () => <div>users-panel</div>,
}));

describe('Pages hôtes', () => {
  beforeEach(() => {
    useTreeStore.setState({ treeId: 1, treeName: 'SSVC Default' });
  });

  it('EvaluatePage monte le TestPanel existant', () => {
    render(<EvaluatePage />);
    expect(screen.getByRole('heading', { name: 'Évaluation' })).toBeInTheDocument();
    expect(screen.getByText('test-panel')).toBeInTheDocument();
  });

  it('EvaluatePage affiche un état vide sans arbre courant', () => {
    useTreeStore.setState({ treeId: null });
    render(<EvaluatePage />);
    expect(screen.getByText('Aucun arbre sélectionné')).toBeInTheDocument();
    expect(screen.queryByText('test-panel')).not.toBeInTheDocument();
  });

  it('IntegrationsPage affiche les deux blocs directement', () => {
    render(<IntegrationsPage />);
    expect(screen.getByRole('heading', { name: 'Intégrations' })).toBeInTheDocument();
    expect(screen.getByText('webhooks-section')).toBeInTheDocument();
    expect(screen.getByText('ingest-section')).toBeInTheDocument();
  });

  it('IntegrationsPage affiche un état vide sans arbre courant', () => {
    useTreeStore.setState({ treeId: null });
    render(<IntegrationsPage />);
    expect(screen.getByText('Aucun arbre sélectionné')).toBeInTheDocument();
    expect(screen.queryByText('webhooks-section')).not.toBeInTheDocument();
  });

  it('AdminUsersPage ouvre le panneau utilisateurs depuis son lanceur', async () => {
    render(<AdminUsersPage />);
    expect(screen.getByRole('heading', { name: 'Utilisateurs' })).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: /Gérer les utilisateurs/ }));
    expect(screen.getByText('users-panel')).toBeInTheDocument();
  });
});
