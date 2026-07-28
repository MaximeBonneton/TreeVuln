import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { Inbox } from 'lucide-react';
import { EmptyState } from '../EmptyState';

describe('EmptyState', () => {
  it('renders title and description', () => {
    render(
      <EmptyState
        icon={Inbox}
        title="No webhooks configured"
        description="Create your first webhook to get notified."
      />
    );
    expect(screen.getByText('No webhooks configured')).toBeInTheDocument();
    expect(screen.getByText('Create your first webhook to get notified.')).toBeInTheDocument();
  });

  it('renders the action when provided', () => {
    render(<EmptyState title="Empty" action={<button>Create</button>} />);
    expect(screen.getByRole('button', { name: 'Create' })).toBeInTheDocument();
  });
});
