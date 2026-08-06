import { useTreeStore } from '@/stores/treeStore';
import { EmptyState } from '@/components/ui';
import { WebhooksSection } from '@/components/integrations/WebhooksSection';
import { IngestSection } from '@/components/integrations/IngestSection';

/** Page Intégrations — Phase 3 : blocs webhooks sortants et ingestion entrante, édition en drawer (spec §3). */
export function IntegrationsPage() {
  const treeId = useTreeStore((s) => s.treeId);

  return (
    <div className="p-6">
      <h1 className="mb-4 text-xl font-semibold tracking-tight text-slate-900">Intégrations</h1>
      {treeId ? (
        <div className="max-w-4xl space-y-8">
          <WebhooksSection key={`wh-${treeId}`} treeId={treeId} />
          <IngestSection key={`in-${treeId}`} treeId={treeId} />
        </div>
      ) : (
        <EmptyState
          title="Aucun arbre sélectionné"
          description="Les intégrations sont configurées par arbre. Choisissez un arbre dans le sélecteur en haut de page."
        />
      )}
    </div>
  );
}
