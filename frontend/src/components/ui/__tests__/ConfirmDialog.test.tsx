import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ConfirmDialog } from '../ConfirmDialog';

describe('ConfirmDialog', () => {
  const defaultProps = {
    open: true,
    title: 'Supprimer ?',
    message: 'Cette action est irréversible.',
    onConfirm: vi.fn(),
    onCancel: vi.fn(),
  };

  it('ne rend rien quand open=false', () => {
    const { container } = render(
      <ConfirmDialog {...defaultProps} open={false} />
    );
    expect(container.firstChild).toBeNull();
  });

  it('affiche le titre et le message', () => {
    render(<ConfirmDialog {...defaultProps} />);
    expect(screen.getByText('Supprimer ?')).toBeInTheDocument();
    expect(screen.getByText('Cette action est irréversible.')).toBeInTheDocument();
  });

  it('affiche les boutons Confirmer et Annuler', () => {
    render(<ConfirmDialog {...defaultProps} />);
    expect(screen.getByText('Confirmer')).toBeInTheDocument();
    expect(screen.getByText('Annuler')).toBeInTheDocument();
  });

  it('appelle onConfirm au clic sur Confirmer', async () => {
    const onConfirm = vi.fn();
    render(<ConfirmDialog {...defaultProps} onConfirm={onConfirm} />);

    await userEvent.click(screen.getByText('Confirmer'));
    expect(onConfirm).toHaveBeenCalledOnce();
  });

  it('appelle onCancel au clic sur Annuler', async () => {
    const onCancel = vi.fn();
    render(<ConfirmDialog {...defaultProps} onCancel={onCancel} />);

    await userEvent.click(screen.getByText('Annuler'));
    expect(onCancel).toHaveBeenCalledOnce();
  });

  it('utilise le style danger par défaut', () => {
    render(<ConfirmDialog {...defaultProps} />);
    const confirmBtn = screen.getByText('Confirmer');
    expect(confirmBtn.className).toContain('bg-red-500');
  });

  it('applique le style warning', () => {
    render(<ConfirmDialog {...defaultProps} variant="warning" />);
    const confirmBtn = screen.getByText('Confirmer');
    expect(confirmBtn.className).toContain('bg-orange-500');
  });

  it('applique le style info', () => {
    render(<ConfirmDialog {...defaultProps} variant="info" />);
    const confirmBtn = screen.getByText('Confirmer');
    expect(confirmBtn.className).toContain('bg-blue-500');
  });
});
