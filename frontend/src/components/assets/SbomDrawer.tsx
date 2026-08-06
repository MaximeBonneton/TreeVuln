import { useCallback, useEffect, useState } from 'react';
import { Package, Trash2 } from 'lucide-react';
import { sbomApi } from '@/api';
import type { SbomDetail } from '@/api/sbom';
import { useTreeStore } from '@/stores/treeStore';
import { useConfirm } from '@/hooks/useConfirm';
import {
  Alert,
  Badge,
  Button,
  ConfirmDialog,
  Drawer,
  Dropzone,
  EmptyState,
  Input,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeaderCell,
  TableRow,
} from '@/components/ui';

interface SbomDrawerProps {
  treeId: number;
  assetId: string | null;
  /** Le résumé sait déjà si l'asset a un SBOM : évite un appel inutile. */
  hasSbom: boolean;
  onClose: () => void;
  onChanged: () => void;
}

/** Volet SBOM d'un asset : détail, dépôt CycloneDX/SPDX, suppression (spec §3). */
export function SbomDrawer({ treeId, assetId, hasSbom, onClose, onChanged }: SbomDrawerProps) {
  const isAdmin = useTreeStore((s) => s.isAdmin);
  const [detail, setDetail] = useState<SbomDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [warnings, setWarnings] = useState<string[]>([]);
  const [uploading, setUploading] = useState(false);
  const [search, setSearch] = useState('');
  const { confirm, confirmDialogProps } = useConfirm();

  const load = useCallback(async () => {
    if (!assetId || !hasSbom) {
      setDetail(null);
      return;
    }
    try {
      const loaded = await sbomApi.getSbom(assetId, treeId);
      setDetail(loaded);
      setWarnings(loaded.warnings);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Impossible de charger le SBOM.');
    }
  }, [assetId, hasSbom, treeId]);

  // Remise à zéro à chaque changement d'asset : pas de détail résiduel
  useEffect(() => {
    setSearch('');
    setWarnings([]);
    setError(null);
    void load();
  }, [load]);

  const handleUpload = async (file: File) => {
    if (!assetId) return;
    setUploading(true);
    setError(null);
    try {
      const meta = await sbomApi.uploadSbom(assetId, treeId, file);
      setWarnings(meta.warnings);
      setDetail(await sbomApi.getSbom(assetId, treeId));
      onChanged();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Échec du dépôt du SBOM.');
    } finally {
      setUploading(false);
    }
  };

  const handleDelete = async () => {
    if (!assetId) return;
    const ok = await confirm(
      'Supprimer ce SBOM ?',
      `Le SBOM de « ${assetId} » sera retiré. Les champs sbom_* vaudront null pour cet asset.`,
      'warning'
    );
    if (!ok) return;
    try {
      await sbomApi.deleteSbom(assetId, treeId);
      setDetail(null);
      setWarnings([]);
      onChanged();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Échec de la suppression du SBOM.');
    }
  };

  const needle = search.trim().toLowerCase();
  const components = (detail?.components ?? []).filter(
    (c) =>
      !needle ||
      c.name.toLowerCase().includes(needle) ||
      (c.purl ?? '').toLowerCase().includes(needle)
  );

  return (
    <>
      <Drawer open={assetId !== null} onClose={onClose} title={`SBOM — ${assetId ?? ''}`}>
        {error && (
          <div className="mb-3">
            <Alert variant="error">{error}</Alert>
          </div>
        )}

        {warnings.length > 0 && (
          <div className="mb-3">
            <Alert variant="warning" title="Importé avec des avertissements">
              <ul className="list-inside list-disc">
                {warnings.map((w) => (
                  <li key={w}>{w}</li>
                ))}
              </ul>
            </Alert>
          </div>
        )}

        {detail ? (
          <div className="space-y-3">
            <div className="flex flex-wrap items-center gap-2 text-xs text-slate-500">
              <Badge variant="success">
                {detail.format} {detail.spec_version}
              </Badge>
              <span>{detail.total_components} composants</span>
              <span>importé le {new Date(detail.imported_at).toLocaleString()}</span>
              {detail.filename && <span className="font-mono">{detail.filename}</span>}
            </div>

            {detail.components.length < detail.total_components && (
              <Alert variant="warning">
                Les {detail.components.length} premiers composants sur {detail.total_components} sont
                affichés — le filtre ne cherche que dans les composants chargés.
              </Alert>
            )}

            <Input
              aria-label="Filtrer les composants"
              placeholder="Filtrer par nom ou purl…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />

            <Table>
              <TableHead>
                <TableHeaderCell>Composant</TableHeaderCell>
                <TableHeaderCell>Version</TableHeaderCell>
                <TableHeaderCell>purl</TableHeaderCell>
              </TableHead>
              <TableBody>
                {components.map((c, i) => (
                  <TableRow key={`${c.name}-${i}`}>
                    <TableCell>{c.name}</TableCell>
                    <TableCell className="text-slate-500">{c.version ?? '—'}</TableCell>
                    <TableCell className="break-all font-mono text-xs text-slate-500">
                      {c.purl ?? '—'}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        ) : (
          <EmptyState
            icon={Package}
            title="Aucun SBOM pour cet asset"
            description={
              isAdmin()
                ? 'Déposez un fichier CycloneDX ou SPDX au format JSON.'
                : 'Seul un administrateur peut déposer un SBOM.'
            }
          />
        )}

        {isAdmin() && (
          <div className="mt-4 space-y-2 border-t border-slate-200 pt-4">
            <Dropzone
              accept=".json"
              file={null}
              onFileSelect={handleUpload}
              hint={
                detail
                  ? 'Déposer un fichier remplace le SBOM actuel'
                  : 'CycloneDX ou SPDX au format JSON'
              }
            />
            {uploading && <p className="text-sm text-slate-500">Import en cours…</p>}
            {detail && (
              <Button variant="danger" size="sm" onClick={handleDelete}>
                <Trash2 size={14} aria-hidden="true" /> Supprimer le SBOM
              </Button>
            )}
          </div>
        )}
      </Drawer>

      <ConfirmDialog {...confirmDialogProps} />
    </>
  );
}
