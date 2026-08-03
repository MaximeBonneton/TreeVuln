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
    const parsed = Number(initialParam.current);
    const bootstrap = async () => {
      if (initialParam.current !== null && Number.isInteger(parsed) && parsed > 0) {
        // selectTree internally calls loadTree + loadTrees, avoid redundancy
        await selectTree(parsed);
        // Repli : si l'arbre référencé par l'URL n'existe plus (404 avalé par
        // loadTree, qui laisse treeId à null sans lever), on bascule sur
        // l'arbre par défaut et on retire le paramètre `tree` fautif de
        // l'URL, sinon un simple refresh reproduirait l'état à l'infini.
        if (useTreeStore.getState().treeId === null) {
          await loadTree();
          setSearchParams(
            (prev) => {
              const next = new URLSearchParams(prev);
              next.delete('tree');
              return next;
            },
            { replace: true }
          );
        }
      } else {
        // loadTree doesn't call loadTrees, so we need to call both
        loadTrees();
        loadTree();
      }
    };
    bootstrap();
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
