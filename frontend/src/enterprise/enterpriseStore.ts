import { create } from 'zustand';
import { api } from '../api/client';
import type { LicenseInfo } from '../types/license';

interface EnterpriseState {
  edition: 'community' | 'enterprise';
  features: Record<string, boolean>;
  enterpriseVersion: string | null;
  isLoaded: boolean;
  loadLicense: () => Promise<void>;
}

export const useEnterpriseStore = create<EnterpriseState>((set) => ({
  edition: 'community',
  features: {},
  enterpriseVersion: null,
  isLoaded: false,

  loadLicense: async () => {
    try {
      const data = await api.get<LicenseInfo>('/license');
      set({
        edition: data.edition,
        features: data.features,
        enterpriseVersion: data.enterprise_version,
        isLoaded: true,
      });
    } catch {
      // Serveur down ou erreur — rester en Community
      set({ edition: 'community', features: {}, isLoaded: true });
    }
  },
}));
