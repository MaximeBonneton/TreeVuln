import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Dialog } from '../Dialog';

describe('Dialog', () => {
  it('renders nothing when open=false', () => {
    const { container } = render(
      <Dialog open={false} onClose={vi.fn()} title="Settings">content</Dialog>
    );
    expect(container.firstChild).toBeNull();
  });

  it('renders title, children and role=dialog when open', () => {
    render(<Dialog open onClose={vi.fn()} title="Settings">content</Dialog>);
    expect(screen.getByRole('dialog', { name: 'Settings' })).toBeInTheDocument();
    expect(screen.getByText('content')).toBeInTheDocument();
  });

  it('calls onClose when pressing Escape', async () => {
    const onClose = vi.fn();
    render(<Dialog open onClose={onClose} title="Settings">content</Dialog>);
    await userEvent.keyboard('{Escape}');
    expect(onClose).toHaveBeenCalledOnce();
  });

  it('calls onClose when clicking the close button', async () => {
    const onClose = vi.fn();
    render(<Dialog open onClose={onClose} title="Settings">content</Dialog>);
    await userEvent.click(screen.getByRole('button', { name: 'Close' }));
    expect(onClose).toHaveBeenCalledOnce();
  });

  it('does not call onClose when clicking inside the panel', async () => {
    const onClose = vi.fn();
    render(<Dialog open onClose={onClose} title="Settings">content</Dialog>);
    await userEvent.click(screen.getByText('content'));
    expect(onClose).not.toHaveBeenCalled();
  });

  it('calls onClose when clicking the backdrop', async () => {
    const onClose = vi.fn();
    const { container } = render(<Dialog open onClose={onClose} title="Settings">content</Dialog>);
    await userEvent.click(container.firstChild as HTMLElement);
    expect(onClose).toHaveBeenCalledOnce();
  });

  it('renders the footer when provided', () => {
    render(
      <Dialog open onClose={vi.fn()} title="Settings" footer={<button>Save</button>}>
        content
      </Dialog>
    );
    expect(screen.getByRole('button', { name: 'Save' })).toBeInTheDocument();
  });
});
