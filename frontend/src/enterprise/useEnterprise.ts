import { useEnterpriseStore } from './enterpriseStore';

export function useEnterprise() {
  const { edition, features, isLoaded } = useEnterpriseStore();

  return {
    isEnterprise: edition === 'enterprise',
    isLoaded,
    features,
    hasFeature: (name: string) => features[name] === true,
  };
}
