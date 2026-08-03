import { ShieldOff } from 'lucide-react';
import { EmptyState } from '@/components/ui';

/** Page affichée quand un operator tente d'accéder à une route /admin/*. */
export function AccessDeniedPage() {
  return (
    <div className="flex h-full items-center justify-center p-6">
      <div className="w-full max-w-md">
        <EmptyState
          icon={ShieldOff}
          title="Accès restreint"
          description="Cette section est réservée aux administrateurs. Contactez un administrateur si vous pensez qu'il s'agit d'une erreur."
        />
      </div>
    </div>
  );
}
