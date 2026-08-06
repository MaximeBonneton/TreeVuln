import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { useTreeStore } from '@/stores/treeStore';
import { AppRoutes } from '@/routes';

// Le shell fait des appels API au mount : remplacé par un passthrough de route
vi.mock('@/components/shell', async () => {
  const { Outlet } = await import('react-router-dom');
  const actual = await vi.importActual<typeof import('@/components/shell')>('@/components/shell');
  return { ...actual, AppShell: () => <Outlet /> };
});

// Pages remplacées par des marqueurs : on teste le routage, pas les pages
vi.mock('@/pages/BuilderPage', () => ({ BuilderPage: () => <div>page-builder</div> }));
vi.mock('@/pages/EvaluatePage', () => ({ EvaluatePage: () => <div>page-evaluate</div> }));
vi.mock('@/pages/ComplianceCsafPage', () => ({ ComplianceCsafPage: () => <div>page-csaf</div> }));
vi.mock('@/pages/ComplianceEnisaPage', () => ({ ComplianceEnisaPage: () => <div>page-enisa</div> }));
vi.mock('@/pages/AssetsPage', () => ({ AssetsPage: () => <div>page-assets</div> }));
vi.mock('@/pages/IntegrationsPage', () => ({ IntegrationsPage: () => <div>page-integrations</div> }));
vi.mock('@/pages/AdminUsersPage', () => ({ AdminUsersPage: () => <div>page-admin-users</div> }));
vi.mock('@/pages/AdminSettingsPage', () => ({ AdminSettingsPage: () => <div>page-admin-settings</div> }));

const admin = { id: '1', username: 'alice', role: 'admin' as const };
const operator = { id: '2', username: 'bob', role: 'operator' as const };

function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <AppRoutes />
    </MemoryRouter>
  );
}

describe('AppRoutes', () => {
  beforeEach(() => {
    useTreeStore.setState({ currentUser: admin });
  });

  it.each([
    ['/builder', 'page-builder'],
    ['/evaluate', 'page-evaluate'],
    ['/compliance/csaf', 'page-csaf'],
    ['/compliance/enisa', 'page-enisa'],
    ['/assets', 'page-assets'],
    ['/integrations', 'page-integrations'],
    ['/admin/users', 'page-admin-users'],
    ['/admin/settings', 'page-admin-settings'],
  ])('rend %s', (path, marker) => {
    renderAt(path);
    expect(screen.getByText(marker)).toBeInTheDocument();
  });

  it('redirige les chemins inconnus vers /builder', () => {
    renderAt('/nulle-part');
    expect(screen.getByText('page-builder')).toBeInTheDocument();
  });

  it('bloque /admin/* pour un operator', () => {
    useTreeStore.setState({ currentUser: operator });
    renderAt('/admin/users');
    expect(screen.queryByText('page-admin-users')).not.toBeInTheDocument();
    expect(screen.getByText('Accès restreint')).toBeInTheDocument();
  });
});
