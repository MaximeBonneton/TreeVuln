import { Input, Select } from '@/components/ui';
import type { FieldDefinition } from '@/types/fieldMapping';

interface VulnFormFieldsProps {
  fields: FieldDefinition[];
  values: Record<string, string>;
  onChange: (name: string, value: string) => void;
}

/** Formulaire de saisie de vulnérabilité généré depuis le field mapping (spec §3 Évaluation). */
export function VulnFormFields({ fields, values, onChange }: VulnFormFieldsProps) {
  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
      {fields.map((field) => {
        const id = `vuln-field-${field.name}`;
        const label = field.label || field.name;
        return (
          <div key={field.name}>
            <label htmlFor={id} className="mb-1 block text-sm font-medium text-slate-700">
              {label}
              {field.required && <span className="text-red-600"> *</span>}
            </label>
            {field.type === 'boolean' ? (
              <Select id={id} value={values[field.name] ?? ''} onChange={(e) => onChange(field.name, e.target.value)}>
                <option value="">—</option>
                <option value="true">true</option>
                <option value="false">false</option>
              </Select>
            ) : (
              <Input
                id={id}
                type={field.type === 'number' ? 'number' : 'text'}
                step={field.type === 'number' ? 'any' : undefined}
                value={values[field.name] ?? ''}
                onChange={(e) => onChange(field.name, e.target.value)}
                placeholder={field.examples[0] != null ? String(field.examples[0]) : undefined}
              />
            )}
          </div>
        );
      })}
    </div>
  );
}

/** Convertit les valeurs texte du formulaire en payload API typé ; les champs vides sont omis. */
export function buildVulnerability(
  fields: FieldDefinition[],
  values: Record<string, string>
): Record<string, unknown> {
  const vuln: Record<string, unknown> = {};
  for (const field of fields) {
    const raw = values[field.name];
    if (raw == null || raw === '') continue;
    if (field.type === 'number') {
      const parsed = Number(raw);
      if (!Number.isNaN(parsed)) vuln[field.name] = parsed;
    } else if (field.type === 'boolean') {
      vuln[field.name] = raw === 'true';
    } else {
      vuln[field.name] = raw;
    }
  }
  return vuln;
}
