import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Switch } from '../Switch';
import { CopyButton } from '../CopyButton';

describe('Switch', () => {
  it('expose role switch avec aria-checked et bascule au clic', async () => {
    const onChange = vi.fn();
    render(<Switch checked={false} onChange={onChange} label="Actif" />);
    const sw = screen.getByRole('switch', { name: 'Actif' });
    expect(sw).toHaveAttribute('aria-checked', 'false');
    await userEvent.click(sw);
    expect(onChange).toHaveBeenCalledWith(true);
  });

  it('ne bascule pas quand désactivé', async () => {
    const onChange = vi.fn();
    render(<Switch checked disabled onChange={onChange} label="Actif" />);
    await userEvent.click(screen.getByRole('switch', { name: 'Actif' }));
    expect(onChange).not.toHaveBeenCalled();
  });
});

describe('CopyButton', () => {
  beforeEach(() => {
    Object.assign(navigator, { clipboard: { writeText: vi.fn().mockResolvedValue(undefined) } });
  });

  it('copie la valeur et affiche le feedback', async () => {
    render(<CopyButton value="https://example.test/ingest/scanner" />);
    await userEvent.click(screen.getByRole('button', { name: 'Copier' }));
    expect(navigator.clipboard.writeText).toHaveBeenCalledWith('https://example.test/ingest/scanner');
    expect(await screen.findByTestId('copy-done')).toBeInTheDocument();
  });
});
