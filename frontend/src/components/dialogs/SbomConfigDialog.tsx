import { useCallback, useEffect, useRef, useState } from 'react';
import { X, Upload, Trash2, Package, Search } from 'lucide-react';
import {
  assetsApi,
  sbomApi,
  type SbomDetail,
  type SbomSummaryItem,
} from '@/api';
import type { Asset } from '@/types';
import { useTreeStore } from '@/stores/treeStore';
import { useConfirm } from '@/hooks/useConfirm';
import { ConfirmDialog } from '@/components/ui/ConfirmDialog';

interface SbomConfigDialogProps {
  treeId: number;
  treeName: string;
  onClose: () => void;
}

/**
 * Gestion des SBOM par asset : liste des assets de l'arbre avec badge
 * (format + nb composants), upload/consultation/suppression du SBOM
 * de l'asset sélectionné. Écriture réservée aux admins.
 */
export function SbomConfigDialog({ treeId, treeName, onClose }: SbomConfigDialogProps) {
  const isAdmin = useTreeStore((s) => s.isAdmin);
  const [assets, setAssets] = useState<Asset[]>([]);
  const [summary, setSummary] = useState<Map<string, SbomSummaryItem>>(new Map());
  const [selected, setSelected] = useState<string | null>(null);
  const [detail, setDetail] = useState<SbomDetail | null>(null);
  const [search, setSearch] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const { confirm, confirmDialogProps } = useConfirm();

  const refresh = useCallback(async () => {
    try {
      const [assetList, summaryList] = await Promise.all([
        assetsApi.listAssets(treeId),
        sbomApi.getSummary(treeId),
      ]);
      setAssets(assetList);
      setSummary(new Map(summaryList.map((s) => [s.asset_id, s])));
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Loading failed');
    }
  }, [treeId]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const loadDetail = async (assetId: string) => {
    setSelected(assetId);
    setDetail(null);
    setSearch('');
    if (!summary.has(assetId)) return; // pas de SBOM : rien à charger
    try {
      setDetail(await sbomApi.getSbom(assetId, treeId));
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Loading failed');
    }
  };

  const handleUpload = async (file: File) => {
    if (!selected) return;
    setUploading(true);
    setError(null);
    try {
      const meta = await sbomApi.uploadSbom(selected, treeId, file);
      if (meta.warnings.length > 0) {
        setError(`Imported with warnings: ${meta.warnings.join('; ')}`);
      }
      await refresh();
      await loadDetailAfterUpload(selected);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Upload failed');
    } finally {
      setUploading(false);
    }
  };

  // Après upload, le summary vient d'être rafraîchi : recharge le détail
  const loadDetailAfterUpload = async (assetId: string) => {
    try {
      setDetail(await sbomApi.getSbom(assetId, treeId));
    } catch {
      setDetail(null);
    }
  };

  const handleDelete = async () => {
    if (!selected) return;
    const ok = await confirm(
      'Delete SBOM',
      `The SBOM of "${selected}" will be removed. sbom_* fields will evaluate to null for this asset. Continue?`,
      'warning'
    );
    if (!ok) return;
    try {
      await sbomApi.deleteSbom(selected, treeId);
      setDetail(null);
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Deletion failed');
    }
  };

  const filteredComponents = detail
    ? detail.components.filter(
        (c) =>
          !search ||
          c.name.toLowerCase().includes(search.toLowerCase()) ||
          (c.purl ?? '').toLowerCase().includes(search.toLowerCase())
      )
    : [];

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-[820px] max-h-[85vh] flex flex-col">
        <div className="flex items-center justify-between p-4 border-b">
          <h2 className="font-bold text-gray-800">SBOM — {treeName}</h2>
          <button onClick={onClose} className="p-1 hover:bg-gray-100 rounded">
            <X size={20} />
          </button>
        </div>

        {error && (
          <p className="mx-4 mt-3 text-sm text-amber-700 bg-amber-50 rounded p-2">
            {error}
          </p>
        )}

        <div className="flex-1 flex overflow-hidden">
          {/* Liste des assets */}
          <div className="w-72 border-r overflow-y-auto">
            {assets.map((asset) => {
              const meta = summary.get(asset.asset_id);
              return (
                <button
                  key={asset.asset_id}
                  onClick={() => loadDetail(asset.asset_id)}
                  className={`w-full text-left px-3 py-2 border-b hover:bg-gray-50 ${
                    selected === asset.asset_id ? 'bg-blue-50' : ''
                  }`}
                >
                  <div className="font-medium text-sm text-gray-800">
                    {asset.asset_id}
                  </div>
                  <div className="text-xs text-gray-500">{asset.name}</div>
                  {meta ? (
                    <span className="inline-flex items-center gap-1 mt-1 text-xs text-green-700 bg-green-50 px-1.5 py-0.5 rounded">
                      <Package size={12} />
                      {meta.component_count} components ({meta.format})
                    </span>
                  ) : (
                    <span className="inline-block mt-1 text-xs text-gray-400">
                      No SBOM
                    </span>
                  )}
                </button>
              );
            })}
            {assets.length === 0 && (
              <p className="p-4 text-sm text-gray-500 italic">
                No assets in this tree. Import assets first.
              </p>
            )}
          </div>

          {/* Détail de l'asset sélectionné */}
          <div className="flex-1 flex flex-col overflow-hidden">
            {!selected ? (
              <p className="p-6 text-sm text-gray-500 italic">
                Select an asset to view or import its SBOM.
              </p>
            ) : (
              <>
                <div className="p-3 border-b flex items-center gap-2">
                  {isAdmin() && (
                    <>
                      <input
                        ref={fileInputRef}
                        type="file"
                        accept=".json,application/json"
                        className="hidden"
                        onChange={(e) => {
                          const file = e.target.files?.[0];
                          if (file) handleUpload(file);
                          e.target.value = '';
                        }}
                      />
                      <button
                        onClick={() => fileInputRef.current?.click()}
                        disabled={uploading}
                        className="flex items-center gap-1 px-3 py-1.5 text-sm bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
                      >
                        <Upload size={14} />
                        {uploading
                          ? 'Importing…'
                          : detail
                            ? 'Replace SBOM'
                            : 'Import SBOM'}
                      </button>
                      {detail && (
                        <button
                          onClick={handleDelete}
                          className="flex items-center gap-1 px-3 py-1.5 text-sm text-red-600 hover:bg-red-50 rounded-md"
                        >
                          <Trash2 size={14} />
                          Delete
                        </button>
                      )}
                    </>
                  )}
                  {detail && (
                    <span className="ml-auto text-xs text-gray-500">
                      {detail.format} {detail.spec_version} —{' '}
                      {detail.total_components} components —{' '}
                      {new Date(detail.imported_at).toLocaleString()}
                    </span>
                  )}
                </div>

                {detail ? (
                  <>
                    {detail.components.length < detail.total_components && (
                      <p className="mx-3 mt-3 text-sm text-amber-700 bg-amber-50 rounded p-2">
                        Showing first {detail.components.length} of{' '}
                        {detail.total_components} components — the filter only
                        searches loaded components.
                      </p>
                    )}
                    <div className="p-3 border-b">
                      <div className="relative">
                        <Search
                          size={14}
                          className="absolute left-2 top-1/2 -translate-y-1/2 text-gray-400"
                        />
                        <input
                          type="text"
                          value={search}
                          onChange={(e) => setSearch(e.target.value)}
                          placeholder="Filter components…"
                          className="w-full pl-7 pr-3 py-1.5 text-sm border rounded-md"
                        />
                      </div>
                    </div>
                    <div className="flex-1 overflow-y-auto">
                      <table className="w-full text-sm">
                        <thead className="sticky top-0 bg-gray-50">
                          <tr className="text-left text-xs text-gray-500">
                            <th className="px-3 py-2">Name</th>
                            <th className="px-3 py-2">Version</th>
                            <th className="px-3 py-2">purl</th>
                          </tr>
                        </thead>
                        <tbody>
                          {filteredComponents.map((c, i) => (
                            <tr key={`${c.name}-${i}`} className="border-t">
                              <td className="px-3 py-1.5">{c.name}</td>
                              <td className="px-3 py-1.5 text-gray-600">
                                {c.version ?? '—'}
                              </td>
                              <td className="px-3 py-1.5 font-mono text-xs text-gray-500 break-all">
                                {c.purl ?? '—'}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </>
                ) : (
                  <p className="p-6 text-sm text-gray-500 italic">
                    No SBOM for this asset.
                    {isAdmin() && ' Import a CycloneDX or SPDX JSON file.'}
                  </p>
                )}
              </>
            )}
          </div>
        </div>
      </div>
      <ConfirmDialog {...confirmDialogProps} />
    </div>
  );
}
