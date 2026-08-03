import { Trees } from 'lucide-react';
import { TreeSelector } from './TreeSelector';
import { UserMenu } from './UserMenu';

/** Topbar du shell : logo, sélecteur d'arbre courant, menu utilisateur (spec §1). */
export function Topbar() {
  return (
    <header className="flex h-12 shrink-0 items-center gap-4 border-b border-slate-200 bg-white px-4">
      <div className="flex items-center gap-2">
        <Trees size={18} className="text-indigo-600" aria-hidden="true" />
        <span className="text-sm font-semibold tracking-tight text-slate-900">TreeVuln</span>
      </div>
      <TreeSelector />
      <div className="flex-1" />
      <UserMenu />
    </header>
  );
}
