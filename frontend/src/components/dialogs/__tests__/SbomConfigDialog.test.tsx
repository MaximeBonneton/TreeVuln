import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { SbomConfigDialog } from '../SbomConfigDialog';

vi.mock('@/api', () => ({
  assetsApi: {
    listAssets: vi.fn().mockResolvedValue([
      { id: 1, asset_id: 'srv-001', name: 'Web Server', criticality: 'High' },
      { id: 2, asset_id: 'srv-002', name: 'DB Server', criticality: 'Low' },
    ]),
  },
  sbomApi: {
    getSummary: vi.fn().mockResolvedValue([
      { asset_id: 'srv-001', format: 'cyclonedx', component_count: 42,
        imported_at: '2026-07-17T10:00:00Z' },
    ]),
    getSbom: vi.fn(),
    uploadSbom: vi.fn(),
    deleteSbom: vi.fn(),
  },
}));

// Le dialog lit isAdmin dans le treeStore
vi.mock('@/stores/treeStore', () => ({
  useTreeStore: (selector: (s: Record<string, unknown>) => unknown) =>
    selector({ isAdmin: () => true }),
}));

describe('SbomConfigDialog', () => {
  beforeEach(() => vi.clearAllMocks());

  it('liste les assets avec badge SBOM pour ceux qui en ont un', async () => {
    render(
      <SbomConfigDialog treeId={1} treeName="Test" onClose={vi.fn()} />
    );
    await waitFor(() => {
      expect(screen.getByText('srv-001')).toBeInTheDocument();
      expect(screen.getByText('srv-002')).toBeInTheDocument();
    });
    // Badge : nombre de composants pour l'asset avec SBOM
    expect(screen.getByText(/42 components/)).toBeInTheDocument();
    // Pas de badge pour l'asset sans SBOM
    expect(screen.getByText(/No SBOM/)).toBeInTheDocument();
  });

  it('affiche le titre avec le nom de l’arbre', async () => {
    render(
      <SbomConfigDialog treeId={1} treeName="Mon arbre" onClose={vi.fn()} />
    );
    // Scopé au h2 : "No SBOM" (badge d'un asset sans SBOM) matche aussi /SBOM/
    await waitFor(() =>
      expect(screen.getByText(/SBOM/, { selector: 'h2' })).toBeInTheDocument()
    );
    expect(screen.getByText(/Mon arbre/)).toBeInTheDocument();
  });
});
