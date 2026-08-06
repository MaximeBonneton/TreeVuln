import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { AssetsTable } from '../AssetsTable';
import type { Asset } from '@/types';
import type { SbomSummaryItem } from '@/api/sbom';

function asset(over: Partial<Asset> & { asset_id: string }): Asset {
  return {
    id: 1,
    name: null,
    criticality: 'Low',
    tags: {},
    extra_data: {},
    created_at: '2026-08-01T10:00:00Z',
    updated_at: '2026-08-01T10:00:00Z',
    ...over,
  };
}

const ASSETS: Asset[] = [
  asset({ id: 1, asset_id: 'srv-prod-001', name: 'Production Web', criticality: 'Critical' }),
  asset({ id: 2, asset_id: 'srv-dev-001', name: 'Development', criticality: 'Low' }),
  asset({ id: 3, asset_id: 'ws-admin-001', name: 'Admin Workstation', criticality: 'High' }),
  asset({ id: 4, asset_id: 'srv-staging-001', name: 'Staging Web', criticality: 'Medium' }),
];

const SUMMARY = new Map<string, SbomSummaryItem>([
  [
    'srv-prod-001',
    {
      asset_id: 'srv-prod-001',
      format: 'cyclonedx',
      component_count: 42,
      imported_at: '2026-08-01T10:00:00Z',
    },
  ],
]);

describe('AssetsTable', () => {
  it('rend une ligne par asset avec son badge de criticité', () => {
    render(<AssetsTable assets={ASSETS} sbomSummary={SUMMARY} onSelect={vi.fn()} />);
    expect(screen.getByText('srv-prod-001')).toBeInTheDocument();
    expect(screen.getByText('ws-admin-001')).toBeInTheDocument();
    expect(screen.getAllByRole('row')).toHaveLength(5); // 4 assets + entête
    expect(screen.getByText('Critical')).toBeInTheDocument();
  });

  it('affiche le SBOM quand il existe, un tiret sinon', () => {
    render(<AssetsTable assets={ASSETS} sbomSummary={SUMMARY} onSelect={vi.fn()} />);
    expect(screen.getByText(/cyclonedx/)).toBeInTheDocument();
    expect(screen.getByText(/42 composants/)).toBeInTheDocument();
    expect(screen.getAllByText('—').length).toBeGreaterThanOrEqual(3);
  });

  it('filtre sur asset_id et sur le nom', async () => {
    const user = userEvent.setup();
    render(<AssetsTable assets={ASSETS} sbomSummary={SUMMARY} onSelect={vi.fn()} />);
    const search = screen.getByLabelText('Rechercher un asset');

    await user.type(search, 'staging');
    expect(screen.getByText('srv-staging-001')).toBeInTheDocument();
    expect(screen.queryByText('srv-prod-001')).not.toBeInTheDocument();

    await user.clear(search);
    await user.type(search, 'Admin Workstation');
    expect(screen.getByText('ws-admin-001')).toBeInTheDocument();
    expect(screen.queryByText('srv-dev-001')).not.toBeInTheDocument();
  });

  it('trie la criticité dans l’ordre métier, pas alphabétique', async () => {
    const user = userEvent.setup();
    render(<AssetsTable assets={ASSETS} sbomSummary={SUMMARY} onSelect={vi.fn()} />);

    await user.click(screen.getByRole('button', { name: /Criticité/ }));
    // Premier clic : décroissant — Critical, High, Medium, Low
    const ids = screen.getAllByTestId('asset-id').map((el) => el.textContent);
    expect(ids).toEqual(['srv-prod-001', 'ws-admin-001', 'srv-staging-001', 'srv-dev-001']);

    await user.click(screen.getByRole('button', { name: /Criticité/ }));
    const reversed = screen.getAllByTestId('asset-id').map((el) => el.textContent);
    expect(reversed).toEqual(['srv-dev-001', 'srv-staging-001', 'ws-admin-001', 'srv-prod-001']);
  });

  it('appelle onSelect avec l’asset_id au clic sur le bouton SBOM', async () => {
    const user = userEvent.setup();
    const onSelect = vi.fn();
    render(<AssetsTable assets={ASSETS} sbomSummary={SUMMARY} onSelect={onSelect} />);
    await user.click(screen.getByRole('button', { name: 'Ouvrir le SBOM de srv-dev-001' }));
    expect(onSelect).toHaveBeenCalledWith('srv-dev-001');
  });

  it('pagine au-delà de 100 lignes', async () => {
    const user = userEvent.setup();
    const many = Array.from({ length: 150 }, (_, i) =>
      asset({ id: i + 1, asset_id: `srv-${String(i).padStart(3, '0')}` })
    );
    render(<AssetsTable assets={many} sbomSummary={new Map()} onSelect={vi.fn()} />);

    expect(screen.getAllByTestId('asset-id')).toHaveLength(100);
    expect(screen.getByText('Page 1 / 2')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Page suivante' }));
    expect(screen.getAllByTestId('asset-id')).toHaveLength(50);
    expect(screen.getByText('Page 2 / 2')).toBeInTheDocument();
  });

  it('signale une recherche sans résultat', async () => {
    const user = userEvent.setup();
    render(<AssetsTable assets={ASSETS} sbomSummary={SUMMARY} onSelect={vi.fn()} />);
    await user.type(screen.getByLabelText('Rechercher un asset'), 'zzz');
    expect(screen.getByText('Aucun asset ne correspond à la recherche.')).toBeInTheDocument();
  });
});
