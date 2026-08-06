import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Bell, Download, FileArchive } from 'lucide-react';
import { evaluateApi } from '@/api/evaluate';
import { settingsApi, type CsafSettings } from '@/api/settings';
import { Alert, Button, Tooltip } from '@/components/ui';
import type { EvaluationResult } from '@/types/evaluation';
import type { OutputNodeConfig, TreeStructure } from '@/types/tree';

/** Compte les résultats sans erreur dont le dernier nœud du chemin est un Output flaggé ENISA.
 *  Les endpoints preview ne créent pas de candidats côté serveur : le compteur est purement indicatif. */
export function countNotifiable(structure: TreeStructure, results: EvaluationResult[]): number {
  const notifiable = new Set(
    structure.nodes
      .filter((n) => n.type === 'output' && (n.config as OutputNodeConfig)?.enisa_notifiable === true)
      .map((n) => n.id)
  );
  if (notifiable.size === 0) return 0;
  return results.filter((r) => !r.error && notifiable.has(r.path[r.path.length - 1]?.node_id ?? '')).length;
}

function download(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

interface DeliverablesBarProps {
  file: File;
  structure: TreeStructure;
  treeId: number;
  results: EvaluationResult[];
}

/** Barre « Livrables » d'une campagne : exports CSV/JSON, bundle CSAF, bannière ENISA (spec §3). */
export function DeliverablesBar({ file, structure, treeId, results }: DeliverablesBarProps) {
  const [csafSettings, setCsafSettings] = useState<CsafSettings | null>(null);
  const [exporting, setExporting] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    settingsApi.getCsafSettings()
      .then((s) => { if (!cancelled) setCsafSettings(s); })
      .catch(() => { if (!cancelled) setCsafSettings(null); });
    return () => { cancelled = true; };
  }, []);

  const notifiableCount = countNotifiable(structure, results);
  const csafReady = csafSettings?.publisher != null;
  const date = new Date().toISOString().slice(0, 10);

  const handleExport = async (format: 'csv' | 'json') => {
    setError(null);
    setExporting(format);
    try {
      const blob = await evaluateApi.exportPreviewCsv(file, structure, format, treeId);
      download(blob, `results_${date}.${format}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : `Échec de l'export ${format.toUpperCase()}.`);
    } finally {
      setExporting(null);
    }
  };

  const handleCsaf = async () => {
    setError(null);
    setExporting('csaf');
    try {
      const { blob, filename } = await evaluateApi.exportPreviewCsaf(
        file, structure, treeId, csafSettings?.has_signing_key ?? false
      );
      download(blob, filename);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Échec de la génération du bundle CSAF.");
    } finally {
      setExporting(null);
    }
  };

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2 rounded-card border border-slate-200 bg-white p-3">
        <span className="text-sm font-medium text-slate-700">Livrables</span>
        <div className="ml-auto flex flex-wrap items-center gap-2">
          <Button variant="secondary" size="sm" disabled={exporting !== null} onClick={() => handleExport('csv')}>
            <Download size={14} aria-hidden="true" /> Export CSV
          </Button>
          <Button variant="secondary" size="sm" disabled={exporting !== null} onClick={() => handleExport('json')}>
            <Download size={14} aria-hidden="true" /> Export JSON
          </Button>
          {csafReady ? (
            <Tooltip content={csafSettings?.has_signing_key ? 'Bundle signé (OpenPGP)' : 'Bundle non signé — clé absente'}>
              <Button variant="secondary" size="sm" disabled={exporting !== null} onClick={handleCsaf}>
                <FileArchive size={14} aria-hidden="true" /> Bundle CSAF
              </Button>
            </Tooltip>
          ) : (
            <>
              <Button variant="secondary" size="sm" disabled>
                <FileArchive size={14} aria-hidden="true" /> Bundle CSAF
              </Button>
              <Link to="/compliance/csaf" className="text-sm font-medium text-indigo-600 hover:text-indigo-700">
                Configurer l'identité éditeur
              </Link>
            </>
          )}
        </div>
      </div>

      {error && <Alert variant="error">{error}</Alert>}

      {notifiableCount > 0 && (
        <Alert variant="warning" title={`${notifiableCount} résultat${notifiableCount > 1 ? 's' : ''} notifiable${notifiableCount > 1 ? 's' : ''} (CRA)`}>
          <span className="inline-flex items-center gap-1">
            <Bell size={14} aria-hidden="true" />
            Des décisions atteignent un nœud marqué notifiable ENISA.{' '}
            <Link to="/compliance/enisa" className="font-medium text-indigo-600 hover:text-indigo-700">
              Ouvrir le suivi ENISA
            </Link>
          </span>
        </Alert>
      )}
    </div>
  );
}
