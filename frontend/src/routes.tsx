import { Routes, Route, Navigate } from 'react-router-dom';
import { AppShell, RequireAdmin } from '@/components/shell';
import { BuilderPage } from '@/pages/BuilderPage';
import { EvaluatePage } from '@/pages/EvaluatePage';
import { ComplianceCsafPage } from '@/pages/ComplianceCsafPage';
import { ComplianceEnisaPage } from '@/pages/ComplianceEnisaPage';
import { AssetsPage } from '@/pages/AssetsPage';
import { IntegrationsPage } from '@/pages/IntegrationsPage';
import { AdminUsersPage } from '@/pages/AdminUsersPage';
import { AdminSettingsPage } from '@/pages/AdminSettingsPage';

/** Arbre de routes des vues authentifiées (spec §1). Setup/Login restent hors shell dans App.tsx. */
export function AppRoutes() {
  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route path="/builder" element={<BuilderPage />} />
        <Route path="/evaluate" element={<EvaluatePage />} />
        <Route path="/compliance/csaf" element={<ComplianceCsafPage />} />
        <Route path="/compliance/enisa" element={<ComplianceEnisaPage />} />
        <Route path="/assets" element={<AssetsPage />} />
        <Route path="/integrations" element={<IntegrationsPage />} />
        <Route
          path="/admin/users"
          element={<RequireAdmin><AdminUsersPage /></RequireAdmin>}
        />
        <Route
          path="/admin/settings"
          element={<RequireAdmin><AdminSettingsPage /></RequireAdmin>}
        />
        <Route path="*" element={<Navigate to="/builder" replace />} />
      </Route>
    </Routes>
  );
}
