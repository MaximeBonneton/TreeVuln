import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Input } from '../Input';
import { Select } from '../Select';
import { Textarea } from '../Textarea';

describe('form fields', () => {
  it('Input accepts typed text', async () => {
    render(<Input placeholder="CVE ID" />);
    const input = screen.getByPlaceholderText('CVE ID');
    await userEvent.type(input, 'CVE-2024-1234');
    expect(input).toHaveValue('CVE-2024-1234');
  });

  it('Input marks invalid state with aria-invalid and red border', () => {
    render(<Input placeholder="CVE ID" invalid />);
    const input = screen.getByPlaceholderText('CVE ID');
    expect(input).toHaveAttribute('aria-invalid', 'true');
    expect(input.className).toContain('border-red-500');
  });

  it('Input has no aria-invalid by default', () => {
    render(<Input placeholder="CVE ID" />);
    expect(screen.getByPlaceholderText('CVE ID')).not.toHaveAttribute('aria-invalid');
  });

  it('Select renders its options', () => {
    render(
      <Select aria-label="Criticality">
        <option value="low">Low</option>
        <option value="high">High</option>
      </Select>
    );
    expect(screen.getByRole('combobox', { name: 'Criticality' })).toBeInTheDocument();
    expect(screen.getAllByRole('option')).toHaveLength(2);
  });

  it('Textarea accepts typed text', async () => {
    render(<Textarea placeholder="JSON" />);
    const area = screen.getByPlaceholderText('JSON');
    await userEvent.type(area, '{{"kev": true}');
    expect(area).toHaveValue('{"kev": true}');
  });
});
