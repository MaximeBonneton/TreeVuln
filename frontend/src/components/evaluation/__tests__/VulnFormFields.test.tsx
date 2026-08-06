import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { VulnFormFields, buildVulnerability } from '../VulnFormFields';
import type { FieldDefinition } from '@/types/fieldMapping';

const fields: FieldDefinition[] = [
  { name: 'cve_id', label: 'CVE ID', type: 'string', examples: [], required: true },
  { name: 'cvss_score', label: 'CVSS Score', type: 'number', examples: [], required: true },
  { name: 'kev', label: 'KEV', type: 'boolean', examples: [], required: false },
];

describe('VulnFormFields', () => {
  it('rend un champ par définition avec le bon contrôle', () => {
    render(<VulnFormFields fields={fields} values={{}} onChange={() => {}} />);
    expect(screen.getByLabelText(/CVE ID/)).toBeInTheDocument();
    expect(screen.getByLabelText(/CVSS Score/)).toHaveAttribute('type', 'number');
    expect(screen.getByLabelText(/KEV/).tagName).toBe('SELECT');
  });

  it('remonte les changements via onChange', async () => {
    const onChange = vi.fn();
    render(<VulnFormFields fields={fields} values={{}} onChange={onChange} />);
    await userEvent.type(screen.getByLabelText(/CVE ID/), 'C');
    expect(onChange).toHaveBeenCalledWith('cve_id', 'C');
  });
});

describe('buildVulnerability', () => {
  it('convertit les types et ignore les champs vides', () => {
    const vuln = buildVulnerability(fields, { cve_id: 'CVE-2024-1', cvss_score: '9.8', kev: 'true' });
    expect(vuln).toEqual({ cve_id: 'CVE-2024-1', cvss_score: 9.8, kev: true });
    expect(buildVulnerability(fields, { cve_id: '', cvss_score: '', kev: '' })).toEqual({});
  });
});
