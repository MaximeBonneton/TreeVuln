import { api } from './client';

export interface CsafPublisher {
  name: string;
  namespace: string;
  category: string;
}

export interface CsafSettings {
  publisher: CsafPublisher | null;
  has_signing_key: boolean;
  signing_key_fingerprint: string | null;
}

export interface CsafSettingsUpdate {
  publisher?: CsafPublisher;
  signing_key?: string;
  signing_key_passphrase?: string;
  remove_signing_key?: boolean;
}

export const settingsApi = {
  getCsafSettings: () => api.get<CsafSettings>('/settings/csaf'),
  updateCsafSettings: (payload: CsafSettingsUpdate) =>
    api.put<CsafSettings>('/settings/csaf', payload),
};
