import { useTreeStore } from '@/stores/treeStore';
import { EmptyState } from '@/components/ui';
import { TestPanel } from '@/components/TreeBuilder/TestPanel';

/** Page Évaluation — Phase 2 : monte le TestPanel existant tel quel (refonte en Phase 3). */
export function EvaluatePage() {
  const treeId = useTreeStore((s) => s.treeId);
  return (
    <div className="flex h-full flex-col p-6">
      <h1 className="mb-4 text-xl font-semibold tracking-tight text-slate-900">Évaluation</h1>
      {treeId ? (
        <div className="flex min-h-0 flex-1">
          {/* onClose no-op : la page est la vue, il n'y a rien à fermer */}
          <TestPanel onClose={() => {}} />
        </div>
      ) : (
        <EmptyState
          title="Aucun arbre sélectionné"
          description="Choisissez un arbre dans le sélecteur en haut de page."
        />
      )}
    </div>
  );
}
