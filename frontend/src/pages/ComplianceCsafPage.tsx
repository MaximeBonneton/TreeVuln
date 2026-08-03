import { useState } from 'react';
import { useTreeStore } from '@/stores/treeStore';
import { Button, Card, EmptyState } from '@/components/ui';
import { CsafConfigDialog } from '@/components/dialogs/CsafConfigDialog';

/** Page Conformité CSAF — Phase 2 : lanceur vers la config existante (page complète en Phase 3). */
export function ComplianceCsafPage() {
  const treeId = useTreeStore((s) => s.treeId);
  const [showConfig, setShowConfig] = useState(false);

  return (
    <div className="p-6">
      <h1 className="mb-4 text-xl font-semibold tracking-tight text-slate-900">Conformité CSAF</h1>
      {treeId ? (
        <div className="max-w-3xl">
          <Card title="Export VEX CSAF 2.0">
            <p className="mb-4 text-sm text-slate-500">
              Identité éditeur, signature GPG et statuts VEX des nœuds de décision. La génération du
              bundle se fait depuis l'onglet batch du panel de test (export au format CSAF).
            </p>
            <Button variant="secondary" onClick={() => setShowConfig(true)}>
              Configurer l'export CSAF
            </Button>
          </Card>
        </div>
      ) : (
        <EmptyState
          title="Aucun arbre sélectionné"
          description="La configuration VEX porte sur les nœuds de l'arbre courant. Choisissez un arbre dans le sélecteur en haut de page."
        />
      )}
      {showConfig && <CsafConfigDialog onClose={() => setShowConfig(false)} />}
    </div>
  );
}
