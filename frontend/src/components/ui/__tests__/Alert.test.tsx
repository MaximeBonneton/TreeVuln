import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { Alert } from '../Alert';

describe('Alert', () => {
  it('renders with role="alert"', () => {
    render(<Alert>Something happened</Alert>);
    expect(screen.getByRole('alert')).toBeInTheDocument();
  });

  it('renders title and children', () => {
    render(<Alert variant="error" title="Save failed">Tree contains a cycle.</Alert>);
    expect(screen.getByText('Save failed')).toBeInTheDocument();
    expect(screen.getByText('Tree contains a cycle.')).toBeInTheDocument();
  });

  it('applies the error variant classes', () => {
    render(<Alert variant="error">boom</Alert>);
    expect(screen.getByRole('alert').className).toContain('bg-red-50');
  });

  it('uses the info variant by default', () => {
    render(<Alert>fyi</Alert>);
    expect(screen.getByRole('alert').className).toContain('bg-indigo-50');
  });
});
