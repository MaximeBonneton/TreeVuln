import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { DecisionTimeline } from '../DecisionTimeline';
import type { DecisionPath } from '@/types/evaluation';

const path: DecisionPath[] = [
  { node_id: 'exploitation', node_label: 'Exploitation', node_type: 'input', field_evaluated: 'kev', value_found: true, condition_matched: 'Active' },
  { node_id: 'output-act', node_label: 'Act', node_type: 'output', field_evaluated: null, value_found: null, condition_matched: null },
];

describe('DecisionTimeline', () => {
  it('affiche une étape par nœud avec champ, valeur et condition', () => {
    render(<DecisionTimeline path={path} />);
    expect(screen.getByText('Exploitation')).toBeInTheDocument();
    expect(screen.getByText(/kev/)).toBeInTheDocument();
    expect(screen.getByText(/Active/)).toBeInTheDocument();
    expect(screen.getByText('Act')).toBeInTheDocument();
    expect(screen.getAllByRole('listitem')).toHaveLength(2);
  });

  it('rend une liste vide sans erreur', () => {
    render(<DecisionTimeline path={[]} />);
    expect(screen.getByRole('list')).toBeEmptyDOMElement();
  });
});
