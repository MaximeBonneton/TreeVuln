import { useEffect, useRef } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useTreeStore } from '@/stores/treeStore';

/**
 * Contexte d'arbre ↔ URL (spec §1) :
 * - au montage du shell, `?tree=N` valide est prioritaire sur l'arbre par défaut ;
 * - ensuite l'URL suit l'arbre courant (liens partageables), en `replace` pour
 *   ne pas polluer l'historique.
 */
export function useTreeUrlSync() {
  const [searchParams, setSearchParams] = useSearchParams();
  const treeId = useTreeStore((s) => s.treeId);
  const loadTree = useTreeStore((s) => s.loadTree);
  const loadTrees = useTreeStore((s) => s.loadTrees);
  const selectTree = useTreeStore((s) => s.selectTree);
  // Capturé une seule fois : seule la valeur à l'arrivée compte pour le bootstrap
  const initialParam = useRef(searchParams.get('tree'));

  useEffect(() => {
    loadTrees();
    const parsed = Number(initialParam.current);
    if (initialParam.current !== null && Number.isInteger(parsed) && parsed > 0) {
      selectTree(parsed);
    } else {
      loadTree();
    }
    // Bootstrap volontairement exécuté une seule fois au montage du shell
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (treeId === null) return;
    setSearchParams(
      (prev) => {
        if (prev.get('tree') === String(treeId)) return prev;
        const next = new URLSearchParams(prev);
        next.set('tree', String(treeId));
        return next;
      },
      { replace: true }
    );
  }, [treeId, setSearchParams]);
}
