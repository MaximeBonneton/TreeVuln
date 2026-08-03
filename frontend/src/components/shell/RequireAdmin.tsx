import { useTreeStore } from '@/stores/treeStore';
import { AccessDeniedPage } from '@/pages/AccessDeniedPage';

/** Garde de rôle : rend les enfants pour un admin, la page « Accès restreint » sinon. */
export function RequireAdmin({ children }: { children: React.ReactNode }) {
  const currentUser = useTreeStore((s) => s.currentUser);
  if (currentUser?.role !== 'admin') {
    return <AccessDeniedPage />;
  }
  return <>{children}</>;
}
