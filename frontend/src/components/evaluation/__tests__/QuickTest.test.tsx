import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { useTreeStore } from '@/stores/treeStore';
import { QuickTest } from '../QuickTest';
import { evaluateApi } from '@/api/evaluate';
import type { FieldMapping } from '@/types/fieldMapping';

vi.mock('@/api/evaluate', () => ({
  evaluateApi: {
    evaluatePreview: vi.fn().mockResolvedValue({
      vuln_id: 'CVE-2024-1',
      decision: 'Act',
      decision_color: '#dc2626',
      path: [
        { node_id: 'exploitation', node_label: 'Exploitation', node_type: 'input', field_evaluated: 'kev', value_found: true, condition_matched: 'Active' },
      ],
      error: null,
    }),
  },
}));

const mapping: FieldMapping = {
  fields: [
    { name: 'cve_id', label: 'CVE ID', type: 'string', examples: [], required: true },
    { name: 'kev', label: 'KEV', type: 'boolean', examples: [], required: false },
  ],
  version: 1,
};

describe('QuickTest', () => {
  beforeEach(() => {
    vi.mocked(evaluateApi.evaluatePreview).mockClear();
    useTreeStore.setState({
      treeId: 1,
      fieldMapping: mapping,
      toApiStructure: () => ({ nodes: [], edges: [], metadata: {} }),
    });
  });

  it('évalue le JSON saisi et affiche le badge et la timeline', async () => {
    render(<QuickTest />);
    await userEvent.click(screen.getByRole('button', { name: 'Évaluer' }));
    await waitFor(() => expect(screen.getByText('Act')).toBeInTheDocument());
    expect(screen.getByText('Exploitation')).toBeInTheDocument();
    expect(evaluateApi.evaluatePreview).toHaveBeenCalledWith(
      expect.objectContaining({ tree_id: 1, include_path: true })
    );
  });

  it('affiche une Alert sur JSON invalide sans appeler l API', async () => {
    render(<QuickTest />);
    const textarea = screen.getByRole('textbox');
    await userEvent.clear(textarea);
    await userEvent.type(textarea, 'pas du json');
    await userEvent.click(screen.getByRole('button', { name: 'Évaluer' }));
    expect(await screen.findByRole('alert')).toHaveTextContent(/JSON invalide/);
    expect(evaluateApi.evaluatePreview).not.toHaveBeenCalled();
  });

  it('bascule sur le formulaire généré depuis le mapping', async () => {
    render(<QuickTest />);
    await userEvent.click(screen.getByRole('tab', { name: 'Formulaire' }));
    expect(screen.getByLabelText(/CVE ID/)).toBeInTheDocument();
    expect(screen.getByLabelText(/KEV/).tagName).toBe('SELECT');
  });

  it('masque l onglet Formulaire sans field mapping', () => {
    useTreeStore.setState({ fieldMapping: null });
    render(<QuickTest />);
    expect(screen.queryByRole('tab', { name: 'Formulaire' })).not.toBeInTheDocument();
    expect(screen.getByRole('textbox')).toBeInTheDocument();
  });
});
