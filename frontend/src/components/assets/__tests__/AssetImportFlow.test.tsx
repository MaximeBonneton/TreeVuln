import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { AssetImportFlow } from '../AssetImportFlow';
import { assetsApi } from '@/api';

vi.mock('@/api', () => ({
  assetsApi: { previewImport: vi.fn(), importAssets: vi.fn() },
}));

const PREVIEW = {
  columns: ['asset_id', 'name', 'criticality'],
  row_count: 3,
  preview: [
    { asset_id: 'srv-001', name: 'Web', criticality: 'High' },
    { asset_id: 'srv-002', name: 'DB', criticality: 'Critical' },
  ],
};

const csv = () => new File(['asset_id,name,criticality\n'], 'assets.csv', { type: 'text/csv' });

describe('AssetImportFlow', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(assetsApi.previewImport).mockResolvedValue(PREVIEW);
  });

  it('passe au mapping après le dépôt, avec auto-détection des colonnes', async () => {
    const user = userEvent.setup();
    render(<AssetImportFlow treeId={1} onDone={vi.fn()} onCancel={vi.fn()} />);

    await user.upload(screen.getByTestId('dropzone-input'), csv());

    await waitFor(() => expect(assetsApi.previewImport).toHaveBeenCalled());
    expect(await screen.findByText(/3 lignes/)).toBeInTheDocument();
    expect(screen.getByLabelText('Colonne identifiant')).toHaveValue('asset_id');
    expect(screen.getByLabelText('Colonne nom')).toHaveValue('name');
    expect(screen.getByLabelText('Colonne criticité')).toHaveValue('criticality');
    // Aperçu des premières lignes
    expect(screen.getByText('srv-002')).toBeInTheDocument();
  });

  it('importe avec le mapping choisi puis affiche le résultat', async () => {
    const user = userEvent.setup();
    vi.mocked(assetsApi.importAssets).mockResolvedValue({
      total_rows: 3,
      created: 2,
      updated: 1,
      errors: 0,
      error_details: [],
    });
    render(<AssetImportFlow treeId={7} onDone={vi.fn()} onCancel={vi.fn()} />);

    await user.upload(screen.getByTestId('dropzone-input'), csv());
    await screen.findByLabelText('Colonne identifiant');
    await user.click(screen.getByRole('button', { name: 'Importer' }));

    await waitFor(() =>
      expect(assetsApi.importAssets).toHaveBeenCalledWith(7, expect.any(File), {
        asset_id: 'asset_id',
        name: 'name',
        criticality: 'criticality',
      })
    );
    expect(await screen.findByText('Import terminé')).toBeInTheDocument();
    expect(screen.getByTestId('tile-created')).toHaveTextContent('2');
    expect(screen.getByTestId('tile-updated')).toHaveTextContent('1');
  });

  it('détaille les lignes en erreur', async () => {
    const user = userEvent.setup();
    vi.mocked(assetsApi.importAssets).mockResolvedValue({
      total_rows: 2,
      created: 1,
      updated: 0,
      errors: 1,
      error_details: [{ row: 2, asset_id: 'srv-002', error: 'criticality invalide' }],
    });
    render(<AssetImportFlow treeId={1} onDone={vi.fn()} onCancel={vi.fn()} />);

    await user.upload(screen.getByTestId('dropzone-input'), csv());
    await screen.findByLabelText('Colonne identifiant');
    await user.click(screen.getByRole('button', { name: 'Importer' }));

    expect(await screen.findByText('Import terminé avec des erreurs')).toBeInTheDocument();
    expect(screen.getByText(/Ligne 2/)).toBeInTheDocument();
    expect(screen.getByText(/criticality invalide/)).toBeInTheDocument();
  });

  it('affiche l’erreur de preview et reste à l’étape de dépôt', async () => {
    const user = userEvent.setup();
    vi.mocked(assetsApi.previewImport).mockRejectedValue(new Error('Parsing error: ligne 1'));
    render(<AssetImportFlow treeId={1} onDone={vi.fn()} onCancel={vi.fn()} />);

    await user.upload(screen.getByTestId('dropzone-input'), csv());

    expect(await screen.findByText(/Parsing error: ligne 1/)).toBeInTheDocument();
    expect(screen.getByTestId('dropzone-input')).toBeInTheDocument();
    expect(screen.queryByLabelText('Colonne identifiant')).not.toBeInTheDocument();
  });

  it('désactive Importer sans colonne identifiant', async () => {
    const user = userEvent.setup();
    vi.mocked(assetsApi.previewImport).mockResolvedValue({
      columns: ['host', 'tier'],
      row_count: 1,
      preview: [{ host: 'srv', tier: 'a' }],
    });
    render(<AssetImportFlow treeId={1} onDone={vi.fn()} onCancel={vi.fn()} />);

    await user.upload(screen.getByTestId('dropzone-input'), csv());
    await screen.findByLabelText('Colonne identifiant');
    expect(screen.getByRole('button', { name: 'Importer' })).toBeDisabled();

    await user.selectOptions(screen.getByLabelText('Colonne identifiant'), 'host');
    expect(screen.getByRole('button', { name: 'Importer' })).toBeEnabled();
  });

  it('revient à la liste depuis le résultat', async () => {
    const user = userEvent.setup();
    const onDone = vi.fn();
    vi.mocked(assetsApi.importAssets).mockResolvedValue({
      total_rows: 1,
      created: 1,
      updated: 0,
      errors: 0,
      error_details: [],
    });
    render(<AssetImportFlow treeId={1} onDone={onDone} onCancel={vi.fn()} />);

    await user.upload(screen.getByTestId('dropzone-input'), csv());
    await screen.findByLabelText('Colonne identifiant');
    await user.click(screen.getByRole('button', { name: 'Importer' }));
    await screen.findByText('Import terminé');
    await user.click(screen.getByRole('button', { name: 'Retour à la liste' }));

    expect(onDone).toHaveBeenCalled();
  });
});
