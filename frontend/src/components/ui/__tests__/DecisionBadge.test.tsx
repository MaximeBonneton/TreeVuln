import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { DecisionBadge } from '../DecisionBadge';

describe('DecisionBadge', () => {
  it('renders the decision with its SSVC color', () => {
    render(<DecisionBadge decision="Act" />);
    const badge = screen.getByText('Act');
    expect(badge).toHaveStyle({ backgroundColor: '#dc2626' });
    expect(badge.className).toContain('text-white');
  });

  it('uses dark text on Track* (AA contrast on yellow)', () => {
    render(<DecisionBadge decision="Track*" />);
    const badge = screen.getByText('Track*');
    expect(badge).toHaveStyle({ backgroundColor: '#eab308' });
    expect(badge.className).toContain('text-slate-900');
  });

  it('falls back to a neutral pill for unknown decisions', () => {
    render(<DecisionBadge decision="Remediate" />);
    const badge = screen.getByText('Remediate');
    expect(badge.className).toContain('bg-slate-200');
  });
});
