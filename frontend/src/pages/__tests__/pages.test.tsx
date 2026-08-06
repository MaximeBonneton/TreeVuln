import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { useTreeStore } from '@/stores/treeStore';
import { EvaluatePage } from '../EvaluatePage';
import { IntegrationsPage } from '../IntegrationsPage';
import { AssetsPage } from '../AssetsPage';
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
vi.mock('@/components/integrations/WebhooksSection', () => ({
  WebhooksSection: () => <div>webhooks-section</div>,
}));
vi.mock('@/components/integrations/IngestSection', () => ({
  IngestSection: () => <div>ingest-section</div>,
}));
vi.mock('@/components/panels/UsersPanel', () => ({
  UsersPanel: () => <div>users-panel</div>,
}));
vi.mock('@/components/assets/AssetsTable', () => ({
  AssetsTable: ({ onSelect }: { onSelect: (id: string) => void }) => (
    <button onClick={() => onSelect('srv-001')}>assets-table</button>
  ),
}));
vi.mock('@/components/assets/AssetImportFlow', () => ({
  AssetImportFlow: ({ onDone }: { onDone: () => void }) => (
    <button onClick={onDone}>import-flow</button>
  ),
}));
vi.mock('@/components/assets/SbomDrawer', () => ({
  SbomDrawer: ({ assetId }: { assetId: string | null }) =>
    assetId ? <div>sbom-drawer:{assetId}</div> : null,
}));
vi.mock('@/api', () => ({
  assetsApi: {
    listAssets: vi.fn().mockResolvedValue([
      {
        id: 1,
        asset_id: 'srv-001',
        name: 'Web',
        criticality: 'High',
        tags: {},
        extra_data: {},
        created_at: '2026-08-01T10:00:00Z',
        updated_at: '2026-08-01T10:00:00Z',
      },
    ]),
  },
  sbomApi: { getSummary: vi.fn().mockResolvedValue([]) },
}));

describe('Pages hôtes', () => {
  beforeEach(() => {
    useTreeStore.setState({ treeId: 1, treeName: 'SSVC Default', isAdmin: () => true });
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

  it('AssetsPage charge et affiche la table', async () => {
    render(<AssetsPage />);
    expect(screen.getByRole('heading', { name: 'Assets & SBOM' })).toBeInTheDocument();
    expect(await screen.findByText('assets-table')).toBeInTheDocument();
  });

  it('AssetsPage affiche un état vide sans arbre courant', () => {
    useTreeStore.setState({ treeId: null });
    render(<AssetsPage />);
    expect(screen.getByText('Aucun arbre sélectionné')).toBeInTheDocument();
    expect(screen.queryByText('assets-table')).not.toBeInTheDocument();
  });

  it('AssetsPage bascule vers l\'import puis revient à la liste', async () => {
    const user = userEvent.setup();
    render(<AssetsPage />);
    await screen.findByText('assets-table');

    await user.click(screen.getByRole('button', { name: /Importer des assets/ }));
    expect(screen.getByText('import-flow')).toBeInTheDocument();
    expect(screen.queryByText('assets-table')).not.toBeInTheDocument();

    await user.click(screen.getByText('import-flow')); // déclenche onDone
    expect(await screen.findByText('assets-table')).toBeInTheDocument();
  });

  it('AssetsPage cache l\'import pour un operator', async () => {
    useTreeStore.setState({ isAdmin: () => false });
    render(<AssetsPage />);
    await screen.findByText('assets-table');
    expect(screen.queryByRole('button', { name: /Importer des assets/ })).not.toBeInTheDocument();
  });

  it('AssetsPage ouvre le volet SBOM depuis la table', async () => {
    const user = userEvent.setup();
    render(<AssetsPage />);
    await user.click(await screen.findByText('assets-table'));
    expect(screen.getByText('sbom-drawer:srv-001')).toBeInTheDocument();
  });

  it('AdminUsersPage ouvre le panneau utilisateurs depuis son lanceur', async () => {
    render(<AdminUsersPage />);
    expect(screen.getByRole('heading', { name: 'Utilisateurs' })).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: /Gérer les utilisateurs/ }));
    expect(screen.getByText('users-panel')).toBeInTheDocument();
  });
});
