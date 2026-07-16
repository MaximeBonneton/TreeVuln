// Valeurs normalisées CSAF 2.0 (profil VEX) — doivent rester alignées avec
// backend/app/schemas/csaf.py
export const VEX_STATUSES = [
  { value: 'not_affected', label: 'Not affected' },
  { value: 'affected', label: 'Affected' },
  { value: 'fixed', label: 'Fixed' },
  { value: 'under_investigation', label: 'Under investigation' },
] as const;

export const VEX_JUSTIFICATIONS = [
  { value: 'component_not_present', label: 'Component not present' },
  { value: 'vulnerable_code_not_present', label: 'Vulnerable code not present' },
  {
    value: 'vulnerable_code_not_in_execute_path',
    label: 'Vulnerable code not in execute path',
  },
  {
    value: 'vulnerable_code_cannot_be_controlled_by_adversary',
    label: 'Vulnerable code cannot be controlled by adversary',
  },
  {
    value: 'inline_mitigations_already_exist',
    label: 'Inline mitigations already exist',
  },
] as const;
