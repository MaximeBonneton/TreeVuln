import { useEffect, useRef, useState } from 'react';
import { CircleUserRound, KeyRound, LogOut } from 'lucide-react';
import { useTreeStore } from '@/stores/treeStore';
import { authApi } from '@/api/auth';
import ChangePasswordDialog from '@/components/ChangePasswordDialog';

/** Menu utilisateur de la topbar : identité, changement de mot de passe, déconnexion. */
export function UserMenu() {
  const currentUser = useTreeStore((s) => s.currentUser);
  const [open, setOpen] = useState(false);
  const [showChangePassword, setShowChangePassword] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  // Fermeture au clic hors du menu
  useEffect(() => {
    if (!open) return;
    const onMouseDown = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener('mousedown', onMouseDown);
    return () => document.removeEventListener('mousedown', onMouseDown);
  }, [open]);

  const handleLogout = async () => {
    try {
      await authApi.logout();
    } catch {
      // Erreurs de déconnexion ignorées : la session locale est de toute façon abandonnée
    }
    window.location.reload();
  };

  if (!currentUser) return null;

  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        aria-label="Menu utilisateur"
        aria-expanded={open}
        onClick={() => setOpen((o) => !o)}
        className="flex items-center gap-2 rounded-lg px-2 py-1.5 text-sm text-slate-600 transition-colors hover:bg-slate-100 hover:text-slate-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500"
      >
        <CircleUserRound size={18} aria-hidden="true" />
      </button>

      {open && (
        <div className="absolute right-0 top-full z-40 mt-1 w-56 rounded-lg border border-slate-200 bg-white p-1 shadow-md">
          <div className="border-b border-slate-200 px-3 py-2">
            <p className="text-sm font-semibold text-slate-900">{currentUser.username}</p>
            <p className="text-xs text-slate-500">{currentUser.role}</p>
          </div>
          <button
            type="button"
            onClick={() => { setOpen(false); setShowChangePassword(true); }}
            className="flex w-full items-center gap-2 rounded-md px-3 py-2 text-left text-sm text-slate-600 hover:bg-slate-100 hover:text-slate-900"
          >
            <KeyRound size={14} aria-hidden="true" />
            Changer le mot de passe
          </button>
          <button
            type="button"
            onClick={handleLogout}
            className="flex w-full items-center gap-2 rounded-md px-3 py-2 text-left text-sm text-red-600 hover:bg-red-50"
          >
            <LogOut size={14} aria-hidden="true" />
            Déconnexion
          </button>
        </div>
      )}

      {showChangePassword && (
        <ChangePasswordDialog
          onComplete={() => setShowChangePassword(false)}
          onClose={() => setShowChangePassword(false)}
        />
      )}
    </div>
  );
}
