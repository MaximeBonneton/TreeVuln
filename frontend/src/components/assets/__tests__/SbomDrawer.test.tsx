import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { SbomDrawer } from '../SbomDrawer';
import { sbomApi } from '@/api';

vi.mock('@/api', () => ({
  sbomApi: {
    getSbom: vi.fn(),
    uploadSbom: vi.fn(),
    deleteSbom: vi.fn(),
  },
}));

let admin = true;
vi.mock('@/stores/treeStore', () => ({
  useTreeStore: (selector: (s: Record<string, unknown>) => unknown) =>
    selector({ isAdmin: () => admin }),
}));

const DETAIL = {
  format: 'cyclonedx',
  spec_version: '1.5',
  filename: 'sbom.json',
  component_count: 2,
  imported_at: '2026-08-01T10:00:00Z',
  warnings: [],
  total_components: 2,
  components: [
    { purl: 'pkg:npm/lodash@4.17.21', name: 'lodash', version: '4.17.21', component_type: 'library' },
    { purl: 'pkg:npm/left-pad@1.3.0', name: 'left-pad', version: '1.3.0', component_type: 'library' },
  ],
};

describe('SbomDrawer', () => {
  beforeEach(() => {
    admin = true;
    vi.clearAllMocks();
    vi.mocked(sbomApi.getSbom).mockResolvedValue(DETAIL);
  });

  it('ne rend rien quand aucun asset n’est sélectionné', () => {
    const { container } = render(
      <SbomDrawer treeId={1} assetId={null} hasSbom={false} onClose={vi.fn()} onChanged={vi.fn()} />
    );
    expect(container).toBeEmptyDOMElement();
    expect(sbomApi.getSbom).not.toHaveBeenCalled();
  });

  it('charge et affiche le détail du SBOM', async () => {
    render(
      <SbomDrawer treeId={1} assetId="srv-001" hasSbom onClose={vi.fn()} onChanged={vi.fn()} />
    );
    await waitFor(() => expect(sbomApi.getSbom).toHaveBeenCalledWith('srv-001', 1));
    expect(screen.getByRole('dialog', { name: /srv-001/ })).toBeInTheDocument();
    expect(await screen.findByText(/cyclonedx 1\.5/)).toBeInTheDocument();
    expect(await screen.findByText('lodash')).toBeInTheDocument();
    expect(screen.getByText('left-pad')).toBeInTheDocument();
  });

  it('filtre les composants par nom ou purl', async () => {
    const user = userEvent.setup();
    render(
      <SbomDrawer treeId={1} assetId="srv-001" hasSbom onClose={vi.fn()} onChanged={vi.fn()} />
    );
    await screen.findByText('lodash');
    await user.type(screen.getByLabelText('Filtrer les composants'), 'left');
    expect(screen.getByText('left-pad')).toBeInTheDocument();
    expect(screen.queryByText('lodash')).not.toBeInTheDocument();
  });

  it('affiche un état vide sans SBOM, sans appeler l’API', async () => {
    render(
      <SbomDrawer treeId={1} assetId="srv-002" hasSbom={false} onClose={vi.fn()} onChanged={vi.fn()} />
    );
    expect(await screen.findByText('Aucun SBOM pour cet asset')).toBeInTheDocument();
    expect(sbomApi.getSbom).not.toHaveBeenCalled();
  });

  it('masque le dépôt et la suppression pour un operator', async () => {
    admin = false;
    render(
      <SbomDrawer treeId={1} assetId="srv-001" hasSbom onClose={vi.fn()} onChanged={vi.fn()} />
    );
    await screen.findByText('lodash');
    expect(screen.queryByTestId('dropzone-input')).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Supprimer le SBOM' })).not.toBeInTheDocument();
  });

  it('supprime le SBOM après confirmation et prévient le parent', async () => {
    const user = userEvent.setup();
    const onChanged = vi.fn();
    vi.mocked(sbomApi.deleteSbom).mockResolvedValue(undefined);
    render(
      <SbomDrawer treeId={1} assetId="srv-001" hasSbom onClose={vi.fn()} onChanged={onChanged} />
    );
    await screen.findByText('lodash');

    await user.click(screen.getByRole('button', { name: 'Supprimer le SBOM' }));
    // ConfirmDialog libelle ses boutons « Cancel »/« Confirm » (en anglais — dette signalée)
    await user.click(screen.getByRole('button', { name: 'Confirm' }));

    await waitFor(() => expect(sbomApi.deleteSbom).toHaveBeenCalledWith('srv-001', 1));
    expect(onChanged).toHaveBeenCalled();
  });

  it('signale les composants non chargés et les warnings d’import', async () => {
    vi.mocked(sbomApi.getSbom).mockResolvedValue({
      ...DETAIL,
      warnings: ['3 composants sans purl'],
      total_components: 1500,
    });
    render(
      <SbomDrawer treeId={1} assetId="srv-001" hasSbom onClose={vi.fn()} onChanged={vi.fn()} />
    );
    expect(await screen.findByText(/3 composants sans purl/)).toBeInTheDocument();
    expect(screen.getByText(/2 premiers composants sur 1500/)).toBeInTheDocument();
  });
});
