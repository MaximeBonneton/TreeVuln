import { useState } from 'react';
import { useTreeStore } from '@/stores/treeStore';
import { Button, Card } from '@/components/ui';
import { ApiConfigDialog } from '@/components/dialogs/ApiConfigDialog';

/** Page Administration · Paramètres — Phase 2 : API dédiée de l'arbre courant (paramètres globaux en Phase 3). */
export function AdminSettingsPage() {
  const treeId = useTreeStore((s) => s.treeId);
  const treeName = useTreeStore((s) => s.treeName);
  const [showApiConfig, setShowApiConfig] = useState(false);

  return (
    <div className="p-6">
      <h1 className="mb-4 text-xl font-semibold tracking-tight text-slate-900">Paramètres</h1>
      <div className="max-w-3xl">
        <Card title="API dédiée par arbre">
          <p className="mb-4 text-sm text-slate-500">
            {treeId
              ? `Activer et configurer le slug de l'API dédiée de l'arbre « ${treeName} ».`
              : 'Sélectionnez un arbre pour configurer son API dédiée.'}
          </p>
          <Button variant="secondary" disabled={!treeId} onClick={() => setShowApiConfig(true)}>
            Configurer l'API dédiée
          </Button>
        </Card>
      </div>
      {showApiConfig && <ApiConfigDialog onClose={() => setShowApiConfig(false)} />}
    </div>
  );
}
