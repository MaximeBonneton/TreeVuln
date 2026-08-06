import { useState } from 'react';
import { useTreeStore } from '@/stores/treeStore';
import { EmptyState, Tabs } from '@/components/ui';
import { QuickTest } from '@/components/evaluation/QuickTest';
import { BatchCampaign } from '@/components/evaluation/BatchCampaign';

/** Page Évaluation — Phase 3 : test rapide (deux cards) et campagne batch pleine page (spec §3). */
export function EvaluatePage() {
  const treeId = useTreeStore((s) => s.treeId);
  const [tab, setTab] = useState<'quick' | 'batch'>('quick');

  return (
    <div className="p-6">
      <div className="mb-4 flex items-center justify-between gap-4">
        <h1 className="text-xl font-semibold tracking-tight text-slate-900">Évaluation</h1>
        {treeId && (
          <Tabs
            tabs={[{ id: 'quick', label: 'Test rapide' }, { id: 'batch', label: 'Campagne batch' }]}
            active={tab}
            onChange={(id) => setTab(id as 'quick' | 'batch')}
          />
        )}
      </div>
      {treeId ? (
        tab === 'quick' ? <QuickTest key={treeId} /> : <BatchCampaign key={treeId} />
      ) : (
        <EmptyState
          title="Aucun arbre sélectionné"
          description="Choisissez un arbre dans le sélecteur en haut de page."
        />
      )}
    </div>
  );
}
