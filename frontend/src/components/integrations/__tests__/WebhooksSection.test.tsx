import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, waitFor, fireEvent, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { WebhooksSection } from '../WebhooksSection';
import { webhooksApi } from '@/api/webhooks';
import type { Webhook, WebhookLog } from '@/types/webhook';

vi.mock('@/api/webhooks', () => ({
  webhooksApi: {
    list: vi.fn(),
    create: vi.fn(),
    update: vi.fn(),
    delete: vi.fn(),
    test: vi.fn(),
    getLogs: vi.fn(),
  },
}));

const webhook: Webhook = {
  id: 1, tree_id: 1, name: 'SIEM', url: 'https://siem.example/hook',
  has_secret: true, headers: {}, events: ['on_act'],
  is_active: true, created_at: '2026-08-01T00:00:00Z', updated_at: '2026-08-01T00:00:00Z',
};

const log: WebhookLog = {
  id: 10, webhook_id: 1, event: 'on_act', status_code: 200,
  request_body: { decision: 'Act' }, response_body: 'ok', success: true,
  error_message: null, duration_ms: 42, created_at: '2026-08-02T00:00:00Z',
};

describe('WebhooksSection', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(webhooksApi.list).mockResolvedValue([webhook]);
    vi.mocked(webhooksApi.update).mockResolvedValue({ ...webhook, is_active: false });
    vi.mocked(webhooksApi.test).mockResolvedValue({
      success: true, status_code: 200, response_body: 'ok', error_message: null, duration_ms: 42,
    });
    vi.mocked(webhooksApi.getLogs).mockResolvedValue([log]);
    vi.mocked(webhooksApi.delete).mockResolvedValue(undefined);
  });

  it('liste les webhooks avec URL, secret et événements', async () => {
    render(<WebhooksSection treeId={1} />);
    expect(await screen.findByText('SIEM')).toBeInTheDocument();
    expect(screen.getByText('https://siem.example/hook')).toBeInTheDocument();
    expect(screen.getByText('secret configuré')).toBeInTheDocument();
    expect(screen.getByText('on_act')).toBeInTheDocument();
  });

  it('bascule le statut actif via le switch', async () => {
    render(<WebhooksSection treeId={1} />);
    await screen.findByText('SIEM');
    await userEvent.click(screen.getByRole('switch', { name: 'Webhook actif' }));
    expect(webhooksApi.update).toHaveBeenCalledWith(1, 1, { is_active: false });
  });

  it('teste le webhook et affiche le résultat', async () => {
    render(<WebhooksSection treeId={1} />);
    await screen.findByText('SIEM');
    await userEvent.click(screen.getByRole('button', { name: 'Tester SIEM' }));
    await waitFor(() => expect(screen.getByText(/200/)).toBeInTheDocument());
    expect(webhooksApi.test).toHaveBeenCalledWith(1, 1);
  });

  it('déplie les logs à la demande', async () => {
    render(<WebhooksSection treeId={1} />);
    await screen.findByText('SIEM');
    await userEvent.click(screen.getByRole('button', { name: 'Historique de SIEM' }));
    expect(await screen.findByText('on_act', { selector: '[data-testid="log-event"]' })).toBeInTheDocument();
    expect(webhooksApi.getLogs).toHaveBeenCalledWith(1, 1);
  });

  it('ouvre le drawer de création depuis l’état vide', async () => {
    vi.mocked(webhooksApi.list).mockResolvedValue([]);
    render(<WebhooksSection treeId={1} />);
    await userEvent.click(await screen.findByRole('button', { name: 'Créer le premier webhook' }));
    expect(screen.getByRole('dialog', { name: 'Nouveau webhook' })).toBeInTheDocument();
  });

  it('supprime après confirmation', async () => {
    render(<WebhooksSection treeId={1} />);
    await screen.findByText('SIEM');
    await userEvent.click(screen.getByRole('button', { name: 'Supprimer SIEM' }));
    await userEvent.click(await screen.findByRole('button', { name: 'Confirm' }));
    await waitFor(() => expect(webhooksApi.delete).toHaveBeenCalledWith(1, 1));
  });

  it('affiche une erreur de section si la sauvegarde échoue après fermeture du drawer', async () => {
    vi.mocked(webhooksApi.list).mockResolvedValue([]);
    let rejectCreate!: (error: Error) => void;
    const pending = new Promise<Webhook>((_, reject) => {
      rejectCreate = reject;
    });
    vi.mocked(webhooksApi.create).mockReturnValue(pending);

    render(<WebhooksSection treeId={1} />);
    await userEvent.click(await screen.findByRole('button', { name: 'Créer le premier webhook' }));

    await userEvent.type(screen.getByLabelText('Nom'), 'SIEM');
    await userEvent.type(screen.getByLabelText('URL'), 'https://siem.example/hook');
    await userEvent.click(screen.getByRole('button', { name: 'on_act' }));
    await userEvent.click(screen.getByRole('button', { name: 'Créer' }));

    fireEvent.keyDown(document, { key: 'Escape' });
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();

    await act(async () => {
      rejectCreate(new Error('Erreur réseau'));
      await pending.catch(() => {});
    });

    await waitFor(() => {
      expect(screen.getByRole('alert')).toHaveTextContent('Erreur réseau');
    });
    expect(webhooksApi.create).toHaveBeenCalledWith(1, expect.objectContaining({ name: 'SIEM' }));
  });
});
