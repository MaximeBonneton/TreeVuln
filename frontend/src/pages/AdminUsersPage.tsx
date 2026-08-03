import { useState } from 'react';
import { Button, Card } from '@/components/ui';
import { UsersPanel } from '@/components/panels/UsersPanel';

/** Page Administration · Utilisateurs — Phase 2 : lanceur vers le panneau existant (table pleine page en Phase 3). */
export function AdminUsersPage() {
  const [showPanel, setShowPanel] = useState(false);

  return (
    <div className="p-6">
      <h1 className="mb-4 text-xl font-semibold tracking-tight text-slate-900">Utilisateurs</h1>
      <div className="max-w-3xl">
        <Card title="Comptes et rôles">
          <p className="mb-4 text-sm text-slate-500">
            Créer des comptes, attribuer les rôles admin/operator et réinitialiser les mots de passe.
          </p>
          <Button variant="secondary" onClick={() => setShowPanel(true)}>
            Gérer les utilisateurs
          </Button>
        </Card>
      </div>
      {showPanel && <UsersPanel onClose={() => setShowPanel(false)} />}
    </div>
  );
}
