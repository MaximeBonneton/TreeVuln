import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { OutputConfig } from '../OutputConfig';

describe('OutputConfig — section VEX / CSAF', () => {
  const baseConfig = { decision: 'Act', color: '#dc2626' };

  it('affiche le dropdown vex_status avec option non mappé', () => {
    render(<OutputConfig config={baseConfig} onChange={vi.fn()} />);
    const select = screen.getByLabelText('VEX status');
    expect(select).toBeInTheDocument();
    expect((select as HTMLSelectElement).value).toBe('');
  });

  it("masque la justification tant que le statut n'est pas not_affected", () => {
    render(
      <OutputConfig
        config={{ ...baseConfig, vex_status: 'affected' }}
        onChange={vi.fn()}
      />
    );
    expect(screen.queryByLabelText('VEX justification')).not.toBeInTheDocument();
  });

  it('affiche la justification (requise) quand not_affected est sélectionné', () => {
    render(
      <OutputConfig
        config={{ ...baseConfig, vex_status: 'not_affected' }}
        onChange={vi.fn()}
      />
    );
    expect(screen.getByLabelText(/VEX justification/)).toBeInTheDocument();
    expect(screen.getByText(/required/i)).toBeInTheDocument();
  });

  it('propage vex_status via onChange', () => {
    const onChange = vi.fn();
    render(<OutputConfig config={baseConfig} onChange={onChange} />);
    fireEvent.change(screen.getByLabelText('VEX status'), {
      target: { value: 'affected' },
    });
    expect(onChange).toHaveBeenCalledWith({ ...baseConfig, vex_status: 'affected' });
  });

  it('efface la justification quand le statut quitte not_affected', () => {
    const onChange = vi.fn();
    render(
      <OutputConfig
        config={{
          ...baseConfig,
          vex_status: 'not_affected',
          vex_justification: 'component_not_present',
        }}
        onChange={onChange}
      />
    );
    fireEvent.change(screen.getByLabelText('VEX status'), {
      target: { value: 'fixed' },
    });
    expect(onChange).toHaveBeenCalledWith({ ...baseConfig, vex_status: 'fixed' });
  });

  it('retire les champs VEX quand on repasse à non mappé', () => {
    const onChange = vi.fn();
    render(
      <OutputConfig
        config={{ ...baseConfig, vex_status: 'affected' }}
        onChange={onChange}
      />
    );
    fireEvent.change(screen.getByLabelText('VEX status'), {
      target: { value: '' },
    });
    expect(onChange).toHaveBeenCalledWith(baseConfig);
  });
});

describe('OutputConfig — flag ENISA', () => {
  const baseConfig = { decision: 'Act', color: '#dc2626' };

  it('affiche la case Notifiable ENISA décochée par défaut', () => {
    render(<OutputConfig config={baseConfig} onChange={vi.fn()} />);
    const checkbox = screen.getByLabelText(/notifiable enisa/i);
    expect(checkbox).not.toBeChecked();
  });

  it('coche -> onChange avec enisa_notifiable: true', () => {
    const onChange = vi.fn();
    render(<OutputConfig config={baseConfig} onChange={onChange} />);
    fireEvent.click(screen.getByLabelText(/notifiable enisa/i));
    expect(onChange).toHaveBeenCalledWith(
      expect.objectContaining({ enisa_notifiable: true })
    );
  });

  it('décoche -> le flag est retiré de la config (pas false)', () => {
    const onChange = vi.fn();
    render(
      <OutputConfig config={{ ...baseConfig, enisa_notifiable: true }} onChange={onChange} />
    );
    fireEvent.click(screen.getByLabelText(/notifiable enisa/i));
    const arg = onChange.mock.calls[0][0];
    expect('enisa_notifiable' in arg).toBe(false);
  });
});
