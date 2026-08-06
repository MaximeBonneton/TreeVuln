import { describe, it, expect } from 'vitest';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BatchSummary } from '../BatchSummary';
import { BatchResultsTable } from '../BatchResultsTable';
import type { EvaluationResponse, EvaluationResult } from '@/types/evaluation';

const results: EvaluationResult[] = [
  { vuln_id: 'CVE-2024-0001', decision: 'Act', decision_color: '#dc2626', path: [
    { node_id: 'n1', node_label: 'Exploitation', node_type: 'input', field_evaluated: 'kev', value_found: true, condition_matched: 'Active' },
  ], error: null },
  { vuln_id: 'CVE-2024-0002', decision: 'Track', decision_color: '#22c55e', path: [], error: null },
];

const response: EvaluationResponse = {
  total: 2, success_count: 2, error_count: 0,
  results, decision_summary: { Act: 1, Track: 1 },
};

describe('BatchSummary', () => {
  it('affiche les tuiles et la distribution', () => {
    render(<BatchSummary response={response} />);
    expect(screen.getByText('Total')).toBeInTheDocument();
    expect(screen.getByText('Taux de succès')).toBeInTheDocument();
    expect(screen.getByText('100%')).toBeInTheDocument();
    const distribution = screen.getByRole('list', { name: 'Distribution des décisions' });
    expect(within(distribution).getByText('Act')).toBeInTheDocument();
    expect(within(distribution).getByText('Track')).toBeInTheDocument();
  });
});

describe('BatchResultsTable', () => {
  it('liste les résultats et filtre par décision', async () => {
    render(<BatchResultsTable results={results} />);
    expect(screen.getByText('CVE-2024-0001')).toBeInTheDocument();
    await userEvent.selectOptions(screen.getByLabelText('Filtrer par décision'), 'Track');
    expect(screen.queryByText('CVE-2024-0001')).not.toBeInTheDocument();
    expect(screen.getByText('CVE-2024-0002')).toBeInTheDocument();
  });

  it("déplie l'audit trail au clic", async () => {
    render(<BatchResultsTable results={results} />);
    await userEvent.click(screen.getByRole('button', { name: /Déplier CVE-2024-0001/ }));
    expect(screen.getByText('Exploitation')).toBeInTheDocument();
  });

  it("trie par décision au clic sur l'en-tête", async () => {
    render(<BatchResultsTable results={results} />);
    await userEvent.click(screen.getByRole('button', { name: 'Trier par décision' }));
    const rows = screen.getAllByTestId('result-row');
    expect(within(rows[0]).getByText('CVE-2024-0001')).toBeInTheDocument(); // Act < Track asc
    await userEvent.click(screen.getByRole('button', { name: 'Trier par décision' }));
    const rowsDesc = screen.getAllByTestId('result-row');
    expect(within(rowsDesc[0]).getByText('CVE-2024-0002')).toBeInTheDocument();
  });
});
