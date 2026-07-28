import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { Badge } from '../Badge';

describe('Badge', () => {
  it('renders its children', () => {
    render(<Badge>default</Badge>);
    expect(screen.getByText('default')).toBeInTheDocument();
  });

  it('uses the neutral variant by default', () => {
    render(<Badge>default</Badge>);
    expect(screen.getByText('default').className).toContain('bg-slate-100');
  });

  it('applies the indigo variant', () => {
    render(<Badge variant="indigo">active</Badge>);
    expect(screen.getByText('active').className).toContain('bg-indigo-50');
  });
});
