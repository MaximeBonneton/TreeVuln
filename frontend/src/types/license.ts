export interface LicenseInfo {
  edition: 'community' | 'enterprise';
  features: Record<string, boolean>;
  enterprise_version: string | null;
}
