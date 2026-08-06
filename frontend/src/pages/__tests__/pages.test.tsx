import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { useTreeStore } from '@/stores/treeStore';
import { EvaluatePage } from '../EvaluatePage';
import { IntegrationsPage } from '../IntegrationsPage';
import { AdminUsersPage } from '../AdminUsersPage';

// Compteur module-level de montages : permet de vérifier qu'un changement d'arbre
// force bien un unmount/remount de la vue (clé sur treeId) plutôt qu'un simple re-render.
const quickTestMounts = vi.hoisted(() => ({ count: 0 }));

// Les vues existantes font des appels API : remplacées par des marqueurs
vi.mock('@/components/evaluation/QuickTest', () => ({
  QuickTest: () => {
    quickTestMounts.count += 1;
    return <div>quick-test</div>;
  },
}));
vi.mock('@/components/evaluation/BatchCampaign', () => ({
  BatchCampaign: () => <div>batch-campaign</div>,
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

  it('EvaluatePage affiche le test rapide et bascule sur la campagne batch', async () => {
    render(<EvaluatePage />);
    expect(screen.getByRole('heading', { name: 'Évaluation' })).toBeInTheDocument();
    expect(screen.getByText('quick-test')).toBeInTheDocument();
    expect(screen.queryByText('batch-campaign')).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole('tab', { name: 'Campagne batch' }));
    expect(screen.getByText('batch-campaign')).toBeInTheDocument();
  });

  it('EvaluatePage remonte les vues au changement d\'arbre', () => {
    quickTestMounts.count = 0;
    render(<EvaluatePage />);
    expect(quickTestMounts.count).toBe(1);

    act(() => {
      useTreeStore.setState({ treeId: 2 });
    });

    expect(quickTestMounts.count).toBe(2);
  });

  it('EvaluatePage affiche un état vide sans arbre courant', () => {
    useTreeStore.setState({ treeId: null });
    render(<EvaluatePage />);
    expect(screen.getByText('Aucun arbre sélectionné')).toBeInTheDocument();
    expect(screen.queryByText('quick-test')).not.toBeInTheDocument();
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
