import { useState } from 'react';
import { useTreeStore } from '@/stores/treeStore';
import { Button, Card, EmptyState } from '@/components/ui';
import { EnisaPanel } from '@/components/panels/EnisaPanel';

/** Page Conformité ENISA — Phase 2 : lanceur vers le panel existant (pleine page en Phase 3). */
export function ComplianceEnisaPage() {
  const treeId = useTreeStore((s) => s.treeId);
  const [showPanel, setShowPanel] = useState(false);

  return (
    <div className="p-6">
      <h1 className="mb-4 text-xl font-semibold tracking-tight text-slate-900">Conformité ENISA</h1>
      {treeId ? (
        <div className="max-w-3xl">
          <Card title="Notifications ENISA (CRA art. 14)">
            <p className="mb-4 text-sm text-slate-500">
              Suivi des échéances 24 h / 72 h / 14 j, pré-remplissage des notifications et rappels webhook.
            </p>
            <Button variant="secondary" onClick={() => setShowPanel(true)}>
              Ouvrir le suivi ENISA
            </Button>
          </Card>
        </div>
      ) : (
        <EmptyState
          title="Aucun arbre sélectionné"
          description="Les événements ENISA sont suivis par arbre. Choisissez un arbre dans le sélecteur en haut de page."
        />
      )}
      {treeId && (
        <EnisaPanel open={showPanel} onClose={() => setShowPanel(false)} treeId={treeId} />
      )}
    </div>
  );
}
