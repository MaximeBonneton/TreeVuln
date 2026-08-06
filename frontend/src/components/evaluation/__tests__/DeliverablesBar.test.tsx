import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { DeliverablesBar, countNotifiable } from '../DeliverablesBar';
import { settingsApi } from '@/api/settings';
import type { EvaluationResult } from '@/types/evaluation';
import type { TreeStructure } from '@/types/tree';

vi.mock('@/api/evaluate', () => ({
  evaluateApi: {
    exportPreviewCsv: vi.fn().mockResolvedValue(new Blob(['x'])),
    exportPreviewCsaf: vi.fn().mockResolvedValue({ blob: new Blob(['x']), filename: 'bundle.zip' }),
  },
}));
vi.mock('@/api/settings', () => ({
  settingsApi: { getCsafSettings: vi.fn() },
}));

const structure = {
  nodes: [
    { id: 'out-act', type: 'output', label: 'Act', position: { x: 0, y: 0 }, config: { decision: 'Act', enisa_notifiable: true }, conditions: [] },
    { id: 'out-track', type: 'output', label: 'Track', position: { x: 0, y: 0 }, config: { decision: 'Track' }, conditions: [] },
  ],
  edges: [],
} as unknown as TreeStructure;

const results: EvaluationResult[] = [
  { vuln_id: 'CVE-1', decision: 'Act', decision_color: '#dc2626', path: [
    { node_id: 'out-act', node_label: 'Act', node_type: 'output', field_evaluated: null, value_found: null, condition_matched: null },
  ], error: null },
  { vuln_id: 'CVE-2', decision: 'Track', decision_color: '#22c55e', path: [
    { node_id: 'out-track', node_label: 'Track', node_type: 'output', field_evaluated: null, value_found: null, condition_matched: null },
  ], error: null },
];

function renderBar() {
  return render(
    <MemoryRouter>
      <DeliverablesBar file={new File(['x'], 'vulns.csv')} structure={structure} treeId={1} results={results} />
    </MemoryRouter>
  );
}

describe('countNotifiable', () => {
  it('compte les résultats atteignant un output notifiable', () => {
    expect(countNotifiable(structure, results)).toBe(1);
  });
});

describe('DeliverablesBar', () => {
  beforeEach(() => {
    vi.mocked(settingsApi.getCsafSettings).mockResolvedValue({
      publisher: { name: 'ACME', namespace: 'https://acme.example', category: 'vendor' },
      has_signing_key: false,
      signing_key_fingerprint: null,
    });
  });

  it('affiche les exports et la bannière ENISA', async () => {
    renderBar();
    expect(screen.getByRole('button', { name: 'Export CSV' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Export JSON' })).toBeInTheDocument();
    await waitFor(() => expect(screen.getByRole('button', { name: /Bundle CSAF/ })).toBeEnabled());
    expect(screen.getByText(/1 résultat notifiable/)).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /suivi ENISA/ })).toHaveAttribute('href', '/compliance/enisa');
  });

  it('désactive le bundle CSAF sans identité éditeur', async () => {
    vi.mocked(settingsApi.getCsafSettings).mockResolvedValue({
      publisher: null, has_signing_key: false, signing_key_fingerprint: null,
    });
    renderBar();
    await waitFor(() => expect(screen.getByRole('button', { name: /Bundle CSAF/ })).toBeDisabled());
    expect(screen.getByRole('link', { name: /Configurer/ })).toHaveAttribute('href', '/compliance/csaf');
  });
});
