import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, waitFor, fireEvent, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { IngestSection } from '../IngestSection';
import { ingestApi } from '@/api/ingest';
import type { IngestEndpoint, IngestEndpointWithKey, IngestLog } from '@/types/ingest';

vi.mock('@/api/ingest', () => ({
  ingestApi: {
    list: vi.fn(),
    create: vi.fn(),
    update: vi.fn(),
    delete: vi.fn(),
    regenerateKey: vi.fn(),
    getLogs: vi.fn(),
  },
}));

const endpoint: IngestEndpoint = {
  id: 5, tree_id: 1, name: 'Scanner Nessus', slug: 'nessus',
  has_api_key: true, field_mapping: { plugin_name: 'cve_id' },
  is_active: true, auto_evaluate: true,
  created_at: '2026-08-01T00:00:00Z', updated_at: '2026-08-01T00:00:00Z',
};

const withKey: IngestEndpointWithKey = { ...endpoint, api_key: 'tvk_secret_123' };

const log: IngestLog = {
  id: 9, endpoint_id: 5, source_ip: '10.0.0.1', payload_size: 1024,
  vuln_count: 3, success_count: 3, error_count: 0, duration_ms: 12,
  created_at: '2026-08-02T00:00:00Z',
};

describe('IngestSection', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(ingestApi.list).mockResolvedValue([endpoint]);
    vi.mocked(ingestApi.regenerateKey).mockResolvedValue(withKey);
    vi.mocked(ingestApi.getLogs).mockResolvedValue([log]);
    vi.mocked(ingestApi.delete).mockResolvedValue(undefined);
  });

  it('liste les endpoints avec URL d’ingestion et badge auto-eval', async () => {
    render(<IngestSection treeId={1} />);
    expect(await screen.findByText('Scanner Nessus')).toBeInTheDocument();
    expect(screen.getByText(/\/api\/v1\/ingest\/nessus/)).toBeInTheDocument();
    expect(screen.getByText('auto-éval')).toBeInTheDocument();
    expect(screen.getByText('Clé chiffrée — copiez-la à la création')).toBeInTheDocument();
    expect(screen.getByText(/X-API-Key/)).toBeInTheDocument();
  });

  it('régénère la clé après confirmation et la révèle masquée', async () => {
    render(<IngestSection treeId={1} />);
    await screen.findByText('Scanner Nessus');
    await userEvent.click(screen.getByRole('button', { name: 'Régénérer la clé de Scanner Nessus' }));
    await userEvent.click(await screen.findByRole('button', { name: 'Confirm' }));
    await waitFor(() => expect(ingestApi.regenerateKey).toHaveBeenCalledWith(5));
    expect(screen.getByText('••••••••')).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Révéler la clé' }));
    expect(screen.getByText('tvk_secret_123')).toBeInTheDocument();
  });

  it('déplie les logs à la demande', async () => {
    render(<IngestSection treeId={1} />);
    await screen.findByText('Scanner Nessus');
    await userEvent.click(screen.getByRole('button', { name: 'Historique de Scanner Nessus' }));
    expect(await screen.findByText(/3 vulnérabilité/)).toBeInTheDocument();
    expect(ingestApi.getLogs).toHaveBeenCalledWith(5);
  });

  it('supprime après confirmation', async () => {
    render(<IngestSection treeId={1} />);
    await screen.findByText('Scanner Nessus');
    await userEvent.click(screen.getByRole('button', { name: 'Supprimer Scanner Nessus' }));
    await userEvent.click(await screen.findByRole('button', { name: 'Confirm' }));
    await waitFor(() => expect(ingestApi.delete).toHaveBeenCalledWith(5));
  });

  it('ouvre le drawer de création depuis l’état vide', async () => {
    vi.mocked(ingestApi.list).mockResolvedValue([]);
    render(<IngestSection treeId={1} />);
    await userEvent.click(await screen.findByRole('button', { name: 'Créer le premier endpoint' }));
    expect(screen.getByRole('dialog', { name: 'Nouvel endpoint' })).toBeInTheDocument();
  });

  it('affiche une erreur de section si la sauvegarde échoue après fermeture du drawer', async () => {
    vi.mocked(ingestApi.list).mockResolvedValue([]);
    let rejectCreate!: (error: Error) => void;
    const pending = new Promise<IngestEndpointWithKey>((_, reject) => {
      rejectCreate = reject;
    });
    vi.mocked(ingestApi.create).mockReturnValue(pending);

    render(<IngestSection treeId={1} />);
    await userEvent.click(await screen.findByRole('button', { name: 'Créer le premier endpoint' }));

    await userEvent.type(screen.getByLabelText('Nom'), 'Scanner Nessus');
    await userEvent.click(screen.getByRole('button', { name: 'Créer' }));

    fireEvent.keyDown(document, { key: 'Escape' });
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();

    await act(async () => {
      rejectCreate(new Error('Erreur réseau'));
      await pending.catch(() => {});
    });

    await waitFor(() => {
      expect(screen.getByRole('alert')).toHaveTextContent('Erreur réseau');
    });
    expect(ingestApi.create).toHaveBeenCalledWith(1, expect.objectContaining({ name: 'Scanner Nessus' }));
  });
});
