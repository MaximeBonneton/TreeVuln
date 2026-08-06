import { useState } from 'react';
import { useTreeStore } from '@/stores/treeStore';
import { Button, Card, EmptyState } from '@/components/ui';
import { AssetImportDialog } from '@/components/dialogs/AssetImportDialog';
import { SbomConfigDialog } from '@/components/dialogs/SbomConfigDialog';

/** Page Assets & SBOM — Phase 2 : lanceurs vers les dialogs existants (table pleine page en Phase 3). */
export function AssetsPage() {
  const treeId = useTreeStore((s) => s.treeId);
  const treeName = useTreeStore((s) => s.treeName);
  const [openDialog, setOpenDialog] = useState<'import' | 'sbom' | null>(null);

  return (
    <div className="p-6">
      <h1 className="mb-4 text-xl font-semibold tracking-tight text-slate-900">Assets & SBOM</h1>
      {treeId ? (
        <div className="grid max-w-3xl grid-cols-1 gap-4 md:grid-cols-2">
          <Card title="Référentiel d'assets">
            <p className="mb-4 text-sm text-slate-500">
              Importer des assets (criticité, contexte) depuis un fichier CSV pour l'arbre « {treeName} ».
            </p>
            <Button variant="secondary" onClick={() => setOpenDialog('import')}>
              Importer des assets
            </Button>
          </Card>
          <Card title="SBOM par asset">
            <p className="mb-4 text-sm text-slate-500">
              Déposer des SBOM CycloneDX/SPDX et consulter les composants détectés.
            </p>
            <Button variant="secondary" onClick={() => setOpenDialog('sbom')}>
              Gérer les SBOM
            </Button>
          </Card>
        </div>
      ) : (
        <EmptyState
          title="Aucun arbre sélectionné"
          description="Les assets sont rattachés à un arbre. Choisissez un arbre dans le sélecteur en haut de page."
        />
      )}
      {openDialog === 'import' && treeId && (
        <AssetImportDialog
          treeId={treeId}
          treeName={treeName}
          onClose={() => setOpenDialog(null)}
          onImported={() => {}}
        />
      )}
      {openDialog === 'sbom' && treeId && (
        <SbomConfigDialog treeId={treeId} treeName={treeName} onClose={() => setOpenDialog(null)} />
      )}
    </div>
  );
}
