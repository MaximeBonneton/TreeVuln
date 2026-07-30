import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { Card } from '../Card';

describe('Card', () => {
  it('renders its children', () => {
    render(<Card>content</Card>);
    expect(screen.getByText('content')).toBeInTheDocument();
  });

  it('renders a header when title is provided', () => {
    render(<Card title="Assets">content</Card>);
    expect(screen.getByRole('heading', { name: 'Assets' })).toBeInTheDocument();
  });

  it('renders no header without title or actions', () => {
    render(<Card>content</Card>);
    expect(screen.queryByRole('heading')).not.toBeInTheDocument();
  });
});
