import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { IngestForm } from '../IngestForm';
import type { IngestEndpoint } from '@/types/ingest';

const existing: IngestEndpoint = {
  id: 5, tree_id: 1, name: 'Scanner Nessus', slug: 'nessus',
  has_api_key: true, field_mapping: { plugin_name: 'cve_id' },
  is_active: true, auto_evaluate: true,
  created_at: '2026-08-01T00:00:00Z', updated_at: '2026-08-01T00:00:00Z',
};

describe('IngestForm', () => {
  it('auto-génère le slug depuis le nom en création', async () => {
    render(<IngestForm endpoint={null} onSubmit={vi.fn()} onCancel={() => {}} />);
    await userEvent.type(screen.getByLabelText('Nom'), 'Scanner Qualys VM');
    expect(screen.getByLabelText('Slug')).toHaveValue('scanner-qualys-vm');
  });

  it('ne réécrase pas un slug modifié manuellement', async () => {
    render(<IngestForm endpoint={null} onSubmit={vi.fn()} onCancel={() => {}} />);
    await userEvent.type(screen.getByLabelText('Slug'), 'mon-slug');
    await userEvent.type(screen.getByLabelText('Nom'), 'Autre Nom');
    expect(screen.getByLabelText('Slug')).toHaveValue('mon-slug');
  });

  it('exige nom et slug', async () => {
    const onSubmit = vi.fn();
    render(<IngestForm endpoint={null} onSubmit={onSubmit} onCancel={() => {}} />);
    await userEvent.click(screen.getByRole('button', { name: 'Créer' }));
    expect(await screen.findByRole('alert')).toBeInTheDocument();
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it('soumet le mapping de champs et les toggles en édition', async () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    render(<IngestForm endpoint={existing} onSubmit={onSubmit} onCancel={() => {}} />);
    expect(screen.getByDisplayValue('plugin_name')).toBeInTheDocument();
    await userEvent.click(screen.getByRole('switch', { name: 'Évaluation automatique' }));
    await userEvent.click(screen.getByRole('button', { name: 'Enregistrer' }));
    expect(onSubmit).toHaveBeenCalledWith(
      expect.objectContaining({
        name: 'Scanner Nessus',
        slug: 'nessus',
        field_mapping: { plugin_name: 'cve_id' },
        auto_evaluate: false,
        is_active: true,
      })
    );
  });
});
