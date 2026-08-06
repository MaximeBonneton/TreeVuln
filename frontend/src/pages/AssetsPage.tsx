import { useCallback, useEffect, useState } from 'react';
import { Boxes, Upload } from 'lucide-react';
import { assetsApi, sbomApi } from '@/api';
import type { SbomSummaryItem } from '@/api/sbom';
import type { Asset } from '@/types';
import { useTreeStore } from '@/stores/treeStore';
import { Alert, Button, EmptyState } from '@/components/ui';
import { AssetsTable } from '@/components/assets/AssetsTable';
import { AssetImportFlow } from '@/components/assets/AssetImportFlow';
import { SbomDrawer } from '@/components/assets/SbomDrawer';

/** Page Assets & SBOM — Phase 3 : table pleine page, import en étape, volet SBOM (spec §3). */
export function AssetsPage() {
  const treeId = useTreeStore((s) => s.treeId);
  const isAdmin = useTreeStore((s) => s.isAdmin);

  if (!treeId) {
    return (
      <div className="p-6">
        <h1 className="mb-4 text-xl font-semibold tracking-tight text-slate-900">Assets & SBOM</h1>
        <EmptyState
          title="Aucun arbre sélectionné"
          description="Les assets sont rattachés à un arbre. Choisissez un arbre dans le sélecteur en haut de page."
        />
      </div>
    );
  }

  // Keyée par treeId : changer d'arbre remet la vue et le volet à zéro
  return <AssetsView key={treeId} treeId={treeId} canWrite={isAdmin()} />;
}

function AssetsView({ treeId, canWrite }: { treeId: number; canWrite: boolean }) {
  const [assets, setAssets] = useState<Asset[]>([]);
  const [summary, setSummary] = useState<Map<string, SbomSummaryItem>>(new Map());
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [view, setView] = useState<'list' | 'import'>('list');
  const [selected, setSelected] = useState<string | null>(null);

  const reload = useCallback(async () => {
    try {
      const [list, sboms] = await Promise.all([
        assetsApi.listAssets(treeId),
        sbomApi.getSummary(treeId),
      ]);
      setAssets(list);
      setSummary(new Map(sboms.map((s) => [s.asset_id, s])));
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Impossible de charger les assets.');
    } finally {
      setLoading(false);
    }
  }, [treeId]);

  useEffect(() => {
    void reload();
  }, [reload]);

  return (
    <div className="p-6">
      <div className="mb-4 flex items-center justify-between">
        <h1 className="text-xl font-semibold tracking-tight text-slate-900">Assets & SBOM</h1>
        {view === 'list' && canWrite && assets.length > 0 && (
          <Button variant="secondary" size="sm" onClick={() => setView('import')}>
            <Upload size={14} aria-hidden="true" /> Importer des assets
          </Button>
        )}
      </div>

      {error && (
        <div className="mb-3">
          <Alert variant="error">{error}</Alert>
        </div>
      )}

      {view === 'import' ? (
        <AssetImportFlow
          treeId={treeId}
          onDone={() => {
            setView('list');
            void reload();
          }}
          onCancel={() => setView('list')}
        />
      ) : loading ? (
        <p className="text-sm text-slate-500">Chargement…</p>
      ) : assets.length === 0 ? (
        <EmptyState
          icon={Boxes}
          title="Aucun asset dans cet arbre"
          description="Importez un fichier CSV ou JSON pour donner un contexte de criticité aux vulnérabilités."
          action={
            canWrite ? (
              <Button onClick={() => setView('import')}>Importer des assets</Button>
            ) : undefined
          }
        />
      ) : (
        <AssetsTable assets={assets} sbomSummary={summary} onSelect={setSelected} />
      )}

      <SbomDrawer
        treeId={treeId}
        assetId={selected}
        hasSbom={selected !== null && summary.has(selected)}
        onClose={() => setSelected(null)}
        onChanged={reload}
      />
    </div>
  );
}
