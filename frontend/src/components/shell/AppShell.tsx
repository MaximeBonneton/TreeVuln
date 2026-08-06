import { Outlet } from 'react-router-dom';
import { Topbar } from './Topbar';
import { SidebarNav } from './SidebarNav';
import { useTreeUrlSync } from '@/hooks/useTreeUrlSync';

/** Layout des vues authentifiées : topbar + sidebar + contenu de la route. */
export function AppShell() {
  useTreeUrlSync();
  return (
    <div className="flex h-screen flex-col bg-slate-50">
      <Topbar />
      <div className="flex flex-1 overflow-hidden">
        <SidebarNav />
        <main className="flex-1 overflow-auto">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
