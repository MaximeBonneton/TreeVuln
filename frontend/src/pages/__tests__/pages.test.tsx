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
vi.mock('@/components/dialogs/WebhookConfigDialog', () => ({
  WebhookConfigDialog: () => <div>webhook-config-dialog</div>,
}));
vi.mock('@/components/dialogs/IngestConfigDialog', () => ({
  IngestConfigDialog: () => <div>ingest-config-dialog</div>,
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

  it('IntegrationsPage ouvre le dialog webhooks depuis son lanceur', async () => {
    render(<IntegrationsPage />);
    expect(screen.getByRole('heading', { name: 'Intégrations' })).toBeInTheDocument();
    expect(screen.queryByText('webhook-config-dialog')).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: /Configurer les webhooks sortants/ }));
    expect(screen.getByText('webhook-config-dialog')).toBeInTheDocument();
  });

  it("IntegrationsPage ouvre le dialog d'ingestion depuis son lanceur", async () => {
    render(<IntegrationsPage />);
    await userEvent.click(screen.getByRole('button', { name: /Configurer l'ingestion entrante/ }));
    expect(screen.getByText('ingest-config-dialog')).toBeInTheDocument();
  });

  it('AdminUsersPage ouvre le panneau utilisateurs depuis son lanceur', async () => {
    render(<AdminUsersPage />);
    expect(screen.getByRole('heading', { name: 'Utilisateurs' })).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: /Gérer les utilisateurs/ }));
    expect(screen.getByText('users-panel')).toBeInTheDocument();
  });
});
