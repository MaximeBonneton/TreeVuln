import { useEffect, useMemo, useRef, useState } from 'react';
import { Check, ChevronDown, Copy, Plus, Star, Trash2, Trees, X } from 'lucide-react';
import { useTreeStore } from '@/stores/treeStore';
import { useConfirm } from '@/hooks/useConfirm';
import { ConfirmDialog, Input } from '@/components/ui';
import { CreateTreeDialog } from '@/components/dialogs/CreateTreeDialog';

/**
 * Sélecteur d'arbre courant de la topbar : recherche, badge « défaut »,
 * création, duplication, définir par défaut, suppression (spec §1).
 */
export function TreeSelector() {
  const trees = useTreeStore((s) => s.trees);
  const treeId = useTreeStore((s) => s.treeId);
  const treeName = useTreeStore((s) => s.treeName);
  const isDefault = useTreeStore((s) => s.isDefault);
  const hasUnsavedChanges = useTreeStore((s) => s.hasUnsavedChanges);
  const selectTree = useTreeStore((s) => s.selectTree);
  const duplicateTree = useTreeStore((s) => s.duplicateTree);
  const setAsDefault = useTreeStore((s) => s.setAsDefault);
  const deleteCurrentTree = useTreeStore((s) => s.deleteCurrentTree);
  const isAdmin = useTreeStore((s) => s.isAdmin);

  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState('');
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [duplicating, setDuplicating] = useState<number | null>(null);
  const [duplicateName, setDuplicateName] = useState('');
  const ref = useRef<HTMLDivElement>(null);
  const { confirm, confirmDialogProps } = useConfirm();

  const canEdit = isAdmin();

  // Fermeture au clic hors du dropdown ; reset de la recherche à la fermeture
  useEffect(() => {
    if (!open) return;
    const onMouseDown = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
        setSearch('');
        setDuplicating(null);
      }
    };
    document.addEventListener('mousedown', onMouseDown);
    return () => document.removeEventListener('mousedown', onMouseDown);
  }, [open]);

  const filteredTrees = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return trees;
    return trees.filter((t) => t.name.toLowerCase().includes(q));
  }, [trees, search]);

  const handleSelect = async (id: number) => {
    if (id === treeId) {
      setOpen(false);
      setSearch('');
      return;
    }
    if (hasUnsavedChanges) {
      const ok = await confirm(
        'Modifications non sauvegardées',
        'Vous avez des modifications non sauvegardées. Continuer ?',
        'warning'
      );
      if (!ok) return;
    }
    try {
      await selectTree(id);
      setOpen(false);
      setSearch('');
    } catch {
      // Error handled in store
    }
  };

  const handleDuplicateConfirm = async (id: number) => {
    if (!duplicateName.trim()) return;
    try {
      await duplicateTree(id, { new_name: duplicateName.trim(), include_assets: true });
      setDuplicating(null);
      setDuplicateName('');
    } catch {
      // Error handled in store
    }
  };

  const handleDelete = async () => {
    const ok = await confirm(
      'Supprimer cet arbre ?',
      `« ${treeName} » et ses assets seront définitivement supprimés.`
    );
    if (!ok) return;
    try {
      await deleteCurrentTree();
      setOpen(false);
    } catch {
      // Error handled in store
    }
  };

  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        aria-expanded={open}
        onClick={() => setOpen((o) => !o)}
        className="flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-sm font-medium text-slate-900 transition-colors hover:bg-slate-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500"
      >
        <Trees size={16} className="text-indigo-600" aria-hidden="true" />
        <div className="max-w-[16rem] truncate">{treeName || 'Aucun arbre'}</div>
        {hasUnsavedChanges && (
          <span title="Modifications non sauvegardées" className="h-1.5 w-1.5 rounded-full bg-amber-500" />
        )}
        {!open && isDefault && (
          <span className="rounded-full bg-indigo-50 px-1.5 py-0.5 text-[10px] font-medium text-indigo-700">
            défaut
          </span>
        )}
        <ChevronDown size={14} className="text-slate-400" aria-hidden="true" />
      </button>

      {open && (
        <div className="absolute left-0 top-full z-40 mt-1 w-80 rounded-lg border border-slate-200 bg-white p-2 shadow-md">
          <Input
            autoFocus
            placeholder="Rechercher un arbre…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="mb-2"
          />
          <ul className="max-h-72 overflow-y-auto" role="listbox" aria-label="Arbres">
            {filteredTrees.map((tree) => (
              <li key={tree.id}>
                {duplicating === tree.id ? (
                  <div className="flex items-center gap-1 px-2 py-1.5">
                    <Input
                      autoFocus
                      value={duplicateName}
                      onChange={(e) => setDuplicateName(e.target.value)}
                      placeholder="Nom de la copie"
                      onKeyDown={(e) => { if (e.key === 'Enter') handleDuplicateConfirm(tree.id); }}
                    />
                    <button
                      type="button"
                      aria-label="Confirmer la duplication"
                      onClick={() => handleDuplicateConfirm(tree.id)}
                      className="rounded-md p-1.5 text-emerald-600 hover:bg-emerald-50"
                    >
                      <Check size={14} />
                    </button>
                    <button
                      type="button"
                      aria-label="Annuler la duplication"
                      onClick={() => { setDuplicating(null); setDuplicateName(''); }}
                      className="rounded-md p-1.5 text-slate-400 hover:bg-slate-100"
                    >
                      <X size={14} />
                    </button>
                  </div>
                ) : (
                  <div
                    className={`group flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-sm ${
                      tree.id === treeId ? 'bg-indigo-50 text-indigo-700' : 'text-slate-700 hover:bg-slate-100'
                    }`}
                  >
                    <button
                      type="button"
                      onClick={() => handleSelect(tree.id)}
                      className="flex min-w-0 flex-1 items-center gap-2 text-left"
                    >
                      <span className="truncate">{tree.name}</span>
                      {tree.is_default && (
                        <span className="shrink-0 rounded-full bg-indigo-50 px-1.5 py-0.5 text-[10px] font-medium text-indigo-700">
                          défaut
                        </span>
                      )}
                    </button>
                    {canEdit && (
                      <span className="hidden shrink-0 items-center gap-0.5 group-hover:flex group-focus-within:flex">
                        <button
                          type="button"
                          aria-label={`Dupliquer ${tree.name}`}
                          title="Dupliquer"
                          onClick={() => { setDuplicating(tree.id); setDuplicateName(`${tree.name} (copie)`); }}
                          className="rounded-md p-1 text-slate-400 hover:bg-slate-200 hover:text-slate-600"
                        >
                          <Copy size={13} />
                        </button>
                        {tree.id === treeId && !tree.is_default && (
                          <>
                            <button
                              type="button"
                              aria-label={`Définir ${tree.name} par défaut`}
                              title="Définir par défaut"
                              onClick={async () => {
                                try {
                                  await setAsDefault();
                                } catch {
                                  // Error handled in store
                                }
                              }}
                              className="rounded-md p-1 text-slate-400 hover:bg-slate-200 hover:text-slate-600"
                            >
                              <Star size={13} />
                            </button>
                            <button
                              type="button"
                              aria-label={`Supprimer ${tree.name}`}
                              title="Supprimer"
                              onClick={handleDelete}
                              className="rounded-md p-1 text-slate-400 hover:bg-red-50 hover:text-red-600"
                            >
                              <Trash2 size={13} />
                            </button>
                          </>
                        )}
                      </span>
                    )}
                  </div>
                )}
              </li>
            ))}
            {filteredTrees.length === 0 && (
              <li className="px-2 py-3 text-center text-sm text-slate-500">Aucun arbre trouvé</li>
            )}
          </ul>
          {canEdit && (
            <button
              type="button"
              onClick={() => { setOpen(false); setShowCreateDialog(true); }}
              className="mt-1 flex w-full items-center gap-2 rounded-md border-t border-slate-200 px-2 pb-1 pt-2 text-sm font-medium text-indigo-600 hover:text-indigo-700"
            >
              <Plus size={14} aria-hidden="true" />
              Nouvel arbre
            </button>
          )}
        </div>
      )}

      {showCreateDialog && <CreateTreeDialog onClose={() => setShowCreateDialog(false)} />}
      <ConfirmDialog {...confirmDialogProps} />
    </div>
  );
}
