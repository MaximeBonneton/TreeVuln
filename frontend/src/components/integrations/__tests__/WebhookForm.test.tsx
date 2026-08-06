import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { WebhookForm } from '../WebhookForm';
import type { Webhook } from '@/types/webhook';

const existing: Webhook = {
  id: 1, tree_id: 1, name: 'SIEM', url: 'https://siem.example/hook',
  has_secret: true, headers: { 'X-Env': 'prod' }, events: ['on_act'],
  is_active: true, created_at: '2026-08-01T00:00:00Z', updated_at: '2026-08-01T00:00:00Z',
};

describe('WebhookForm', () => {
  it('exige nom, URL et au moins un événement', async () => {
    const onSubmit = vi.fn();
    render(<WebhookForm webhook={null} onSubmit={onSubmit} onCancel={() => {}} />);
    await userEvent.click(screen.getByRole('button', { name: 'Créer' }));
    expect(await screen.findByRole('alert')).toBeInTheDocument();
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it('soumet un webhook complet en création', async () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    render(<WebhookForm webhook={null} onSubmit={onSubmit} onCancel={() => {}} />);
    await userEvent.type(screen.getByLabelText('Nom'), 'Ticketing');
    await userEvent.type(screen.getByLabelText('URL'), 'https://tickets.example/hook');
    await userEvent.click(screen.getByRole('button', { name: 'on_act' }));
    await userEvent.click(screen.getByRole('button', { name: 'Créer' }));
    expect(onSubmit).toHaveBeenCalledWith(
      expect.objectContaining({
        name: 'Ticketing',
        url: 'https://tickets.example/hook',
        events: ['on_act'],
        is_active: true,
      })
    );
    expect(onSubmit.mock.calls[0][0]).not.toHaveProperty('secret');
  });

  it('pré-remplit en édition et n\'envoie pas de secret non modifié', async () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    render(<WebhookForm webhook={existing} onSubmit={onSubmit} onCancel={() => {}} />);
    expect(screen.getByLabelText('Nom')).toHaveValue('SIEM');
    expect(screen.getByLabelText(/Secret/)).toHaveAttribute('placeholder', expect.stringMatching(/inchangé/i));
    await userEvent.click(screen.getByRole('button', { name: 'Enregistrer' }));
    expect(onSubmit.mock.calls[0][0]).not.toHaveProperty('secret');
  });

  it('gère les en-têtes personnalisés', async () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    render(<WebhookForm webhook={existing} onSubmit={onSubmit} onCancel={() => {}} />);
    expect(screen.getByDisplayValue('X-Env')).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Ajouter un en-tête' }));
    const keys = screen.getAllByPlaceholderText('Nom de l\'en-tête');
    await userEvent.type(keys[1], 'X-Token');
    const values = screen.getAllByPlaceholderText('Valeur');
    await userEvent.type(values[1], 'abc');
    await userEvent.click(screen.getByRole('button', { name: 'Enregistrer' }));
    expect(onSubmit.mock.calls[0][0].headers).toEqual({ 'X-Env': 'prod', 'X-Token': 'abc' });
  });
});
