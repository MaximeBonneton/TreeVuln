import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { useTreeStore } from '@/stores/treeStore';
import { BatchCampaign } from '../BatchCampaign';
import { evaluateApi } from '@/api/evaluate';

vi.mock('@/api/evaluate', () => ({
  evaluateApi: {
    evaluatePreviewCsv: vi.fn().mockResolvedValue({
      total: 1, success_count: 1, error_count: 0,
      results: [{ vuln_id: 'CVE-1', decision: 'Act', decision_color: '#dc2626', path: [], error: null }],
      decision_summary: { Act: 1 },
    }),
  },
}));
vi.mock('@/api/settings', () => ({
  settingsApi: { getCsafSettings: vi.fn().mockResolvedValue({ publisher: null, has_signing_key: false, signing_key_fingerprint: null }) },
}));

describe('BatchCampaign', () => {
  beforeEach(() => {
    vi.mocked(evaluateApi.evaluatePreviewCsv).mockClear();
    useTreeStore.setState({ treeId: 1, toApiStructure: () => ({ nodes: [], edges: [], metadata: {} }) });
  });

  it('évalue le fichier déposé et affiche résumé, table et livrables', async () => {
    render(<MemoryRouter><BatchCampaign /></MemoryRouter>);
    const input = screen.getByTestId('dropzone-input');
    await userEvent.upload(input, new File(['cve_id\nCVE-1'], 'vulns.csv', { type: 'text/csv' }));
    await userEvent.click(screen.getByRole('button', { name: /Lancer la campagne/ }));
    await waitFor(() => expect(screen.getByText('Taux de succès')).toBeInTheDocument());
    expect(screen.getByText('CVE-1')).toBeInTheDocument();
    expect(screen.getByText('Livrables')).toBeInTheDocument();
    expect(evaluateApi.evaluatePreviewCsv).toHaveBeenCalledOnce();
  });

  it('affiche une Alert quand l evaluation échoue', async () => {
    vi.mocked(evaluateApi.evaluatePreviewCsv).mockRejectedValueOnce(new Error('CSV illisible'));
    render(<MemoryRouter><BatchCampaign /></MemoryRouter>);
    await userEvent.upload(screen.getByTestId('dropzone-input'), new File(['x'], 'vulns.csv', { type: 'text/csv' }));
    await userEvent.click(screen.getByRole('button', { name: /Lancer la campagne/ }));
    expect(await screen.findByRole('alert')).toHaveTextContent('CSV illisible');
  });

  it('désactive le lancement sans fichier', () => {
    render(<MemoryRouter><BatchCampaign /></MemoryRouter>);
    expect(screen.getByRole('button', { name: /Lancer la campagne/ })).toBeDisabled();
  });
});
