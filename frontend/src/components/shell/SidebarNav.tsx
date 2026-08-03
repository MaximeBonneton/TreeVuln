import { useEffect, useState } from 'react';
import { NavLink } from 'react-router-dom';
import {
  Workflow,
  PlayCircle,
  FileCheck,
  Bell,
  Package,
  Link2,
  Users,
  Settings,
  PanelLeftClose,
  PanelLeftOpen,
  type LucideIcon,
} from 'lucide-react';
import { useTreeStore } from '@/stores/treeStore';
import { getEnisaSummary, type EnisaSummary } from '@/api/enisa';

interface NavItem {
  to: string;
  label: string;
  icon: LucideIcon;
}

const MAIN_ITEMS: NavItem[] = [
  { to: '/builder', label: 'Builder', icon: Workflow },
  { to: '/evaluate', label: 'Évaluation', icon: PlayCircle },
];

const COMPLIANCE_ITEMS: NavItem[] = [
  { to: '/compliance/csaf', label: 'CSAF', icon: FileCheck },
  { to: '/compliance/enisa', label: 'ENISA', icon: Bell },
];

const CONTEXT_ITEMS: NavItem[] = [
  { to: '/assets', label: 'Assets & SBOM', icon: Package },
  { to: '/integrations', label: 'Intégrations', icon: Link2 },
];

const ADMIN_ITEMS: NavItem[] = [
  { to: '/admin/users', label: 'Utilisateurs', icon: Users },
  { to: '/admin/settings', label: 'Paramètres', icon: Settings },
];

function NavEntry({
  item,
  collapsed,
  badge,
}: {
  item: NavItem;
  collapsed: boolean;
  badge?: React.ReactNode;
}) {
  const Icon = item.icon;
  return (
    <NavLink
      to={item.to}
      aria-label={item.label}
      title={collapsed ? item.label : undefined}
      className={({ isActive }) =>
        `relative flex items-center gap-2.5 rounded-lg px-2.5 py-2 text-sm font-medium transition-colors ${
          isActive
            ? 'bg-indigo-50 text-indigo-700'
            : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'
        } ${collapsed ? 'justify-center' : ''}`
      }
    >
      <Icon size={16} className="shrink-0" aria-hidden="true" />
      {!collapsed && <span className="flex-1 truncate">{item.label}</span>}
      {badge}
    </NavLink>
  );
}

function SectionLabel({ children, collapsed }: { children: string; collapsed: boolean }) {
  if (collapsed) return <div className="my-2 border-t border-slate-200" aria-hidden="true" />;
  return (
    <p className="mt-4 mb-1 px-2.5 text-[11px] font-semibold uppercase tracking-wide text-slate-400">
      {children}
    </p>
  );
}

/** Sidebar de navigation par domaine, repliable en mode icônes (spec §1). */
export function SidebarNav() {
  const currentUser = useTreeStore((s) => s.currentUser);
  const treeId = useTreeStore((s) => s.treeId);
  const [collapsed, setCollapsed] = useState(false);
  const [enisaSummary, setEnisaSummary] = useState<EnisaSummary | null>(null);

  // Badge ENISA : rechargé au changement d'arbre, sans polling (cf. follow-up PR #3)
  useEffect(() => {
    if (!treeId) {
      setEnisaSummary(null);
      return;
    }
    let cancelled = false;
    getEnisaSummary(treeId)
      .then((s) => { if (!cancelled) setEnisaSummary(s); })
      .catch(() => { if (!cancelled) setEnisaSummary(null); });
    return () => { cancelled = true; };
  }, [treeId]);

  const enisaCount = enisaSummary
    ? enisaSummary.candidates + enisaSummary.overdue_milestones
    : 0;
  const enisaBadge = enisaCount > 0 ? (
    <span
      className={`flex h-4 min-w-[16px] items-center justify-center rounded-full px-1 text-[10px] font-medium text-white ${
        enisaSummary && enisaSummary.overdue_milestones > 0 ? 'bg-red-600' : 'bg-slate-400'
      } ${collapsed ? 'absolute -right-0.5 -top-0.5' : ''}`}
    >
      {enisaCount}
    </span>
  ) : undefined;

  return (
    <nav
      aria-label="Navigation principale"
      className={`flex shrink-0 flex-col border-r border-slate-200 bg-white p-2 transition-all ${
        collapsed ? 'w-14' : 'w-56'
      }`}
    >
      <div className="flex flex-1 flex-col gap-0.5 overflow-y-auto">
        {MAIN_ITEMS.map((item) => (
          <NavEntry key={item.to} item={item} collapsed={collapsed} />
        ))}
        <SectionLabel collapsed={collapsed}>Conformité</SectionLabel>
        {COMPLIANCE_ITEMS.map((item) => (
          <NavEntry
            key={item.to}
            item={item}
            collapsed={collapsed}
            badge={item.to === '/compliance/enisa' ? enisaBadge : undefined}
          />
        ))}
        <SectionLabel collapsed={collapsed}>Contexte</SectionLabel>
        {CONTEXT_ITEMS.map((item) => (
          <NavEntry key={item.to} item={item} collapsed={collapsed} />
        ))}
        {currentUser?.role === 'admin' && (
          <>
            <SectionLabel collapsed={collapsed}>Administration</SectionLabel>
            {ADMIN_ITEMS.map((item) => (
              <NavEntry key={item.to} item={item} collapsed={collapsed} />
            ))}
          </>
        )}
      </div>
      <button
        type="button"
        onClick={() => setCollapsed((c) => !c)}
        aria-label={collapsed ? 'Déplier la navigation' : 'Replier la navigation'}
        className="mt-2 flex items-center justify-center rounded-lg p-2 text-slate-400 transition-colors hover:bg-slate-100 hover:text-slate-600 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500"
      >
        {collapsed ? <PanelLeftOpen size={16} /> : <PanelLeftClose size={16} />}
      </button>
    </nav>
  );
}
