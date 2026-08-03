import { useState } from 'react';
import { useTreeStore } from '@/stores/treeStore';
import { Button, Card, EmptyState } from '@/components/ui';
import { WebhookConfigDialog } from '@/components/dialogs/WebhookConfigDialog';
import { IngestConfigDialog } from '@/components/dialogs/IngestConfigDialog';

/** Page Intégrations — Phase 2 : lanceurs vers les dialogs existants (drawers en Phase 3). */
export function IntegrationsPage() {
  const treeId = useTreeStore((s) => s.treeId);
  const treeName = useTreeStore((s) => s.treeName);
  const [openDialog, setOpenDialog] = useState<'webhooks' | 'ingest' | null>(null);

  return (
    <div className="p-6">
      <h1 className="mb-4 text-xl font-semibold tracking-tight text-slate-900">Intégrations</h1>
      {treeId ? (
        <div className="grid max-w-3xl grid-cols-1 gap-4 md:grid-cols-2">
          <Card title="Webhooks sortants">
            <p className="mb-4 text-sm text-slate-500">
              Notifier un ticketing ou un SIEM à chaque évaluation de l'arbre « {treeName} ».
            </p>
            <Button variant="secondary" onClick={() => setOpenDialog('webhooks')}>
              Configurer les webhooks sortants
            </Button>
          </Card>
          <Card title="Ingestion entrante">
            <p className="mb-4 text-sm text-slate-500">
              Recevoir des vulnérabilités en temps réel via des endpoints à clé API.
            </p>
            <Button variant="secondary" onClick={() => setOpenDialog('ingest')}>
              Configurer l'ingestion entrante
            </Button>
          </Card>
        </div>
      ) : (
        <EmptyState
          title="Aucun arbre sélectionné"
          description="Les intégrations sont configurées par arbre. Choisissez un arbre dans le sélecteur en haut de page."
        />
      )}
      {openDialog === 'webhooks' && treeId && (
        <WebhookConfigDialog treeId={treeId} treeName={treeName} onClose={() => setOpenDialog(null)} />
      )}
      {openDialog === 'ingest' && treeId && (
        <IngestConfigDialog treeId={treeId} treeName={treeName} onClose={() => setOpenDialog(null)} />
      )}
    </div>
  );
}
