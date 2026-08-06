import { useState } from 'react';
import { AlertCircle } from 'lucide-react';
import { assetsApi } from '@/api';
import type { AssetImportPreview, AssetImportResult } from '@/types';
import {
  Alert,
  Button,
  Card,
  Dropzone,
  Select,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeaderCell,
  TableRow,
} from '@/components/ui';

type Step = 'upload' | 'mapping' | 'result';

const STEPS: { key: Step; label: string }[] = [
  { key: 'upload', label: 'Fichier' },
  { key: 'mapping', label: 'Mapping' },
  { key: 'result', label: 'Résultat' },
];

interface AssetImportFlowProps {
  treeId: number;
  onDone: () => void;
  onCancel: () => void;
}

/** Import d'assets en étape de page : dépôt → mapping des colonnes → résultat (spec §3). */
export function AssetImportFlow({ treeId, onDone, onCancel }: AssetImportFlowProps) {
  const [step, setStep] = useState<Step>('upload');
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<AssetImportPreview | null>(null);
  const [result, setResult] = useState<AssetImportResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const [colAssetId, setColAssetId] = useState('');
  const [colName, setColName] = useState('');
  const [colCriticality, setColCriticality] = useState('');

  const handleFile = async (selected: File) => {
    setFile(selected);
    setError(null);
    setBusy(true);
    try {
      const data = await assetsApi.previewImport(selected);
      // Auto-détection : mêmes alias que l'ancien dialog
      const lower = data.columns.map((c) => c.toLowerCase());
      const pick = (names: string[]) => {
        const idx = lower.findIndex((c) => names.includes(c));
        return idx >= 0 ? data.columns[idx] : '';
      };
      setColAssetId(pick(['asset_id', 'assetid', 'id']));
      setColName(pick(['name', 'hostname', 'nom']));
      setColCriticality(pick(['criticality', 'criticite', 'priority']));
      setPreview(data);
      setStep('mapping');
    } catch (e) {
      setError(e instanceof Error ? e.message : "Échec de l'analyse du fichier.");
    } finally {
      setBusy(false);
    }
  };

  const handleImport = async () => {
    if (!file || !colAssetId) return;
    setBusy(true);
    setError(null);
    try {
      setResult(
        await assetsApi.importAssets(treeId, file, {
          asset_id: colAssetId,
          name: colName || undefined,
          criticality: colCriticality || undefined,
        })
      );
      setStep('result');
    } catch (e) {
      setError(e instanceof Error ? e.message : "Échec de l'import.");
    } finally {
      setBusy(false);
    }
  };

  const columnSelect = (
    label: string,
    value: string,
    onChange: (v: string) => void,
    required = false
  ) => (
    <label className="flex items-center gap-3 text-sm">
      <span className="w-40 text-slate-600">
        {label}
        {required && ' *'}
      </span>
      <Select
        aria-label={label}
        value={value}
        invalid={required && !value}
        onChange={(e) => onChange(e.target.value)}
        className="flex-1"
      >
        <option value="">— Non utilisée —</option>
        {preview?.columns.map((c) => (
          <option key={c} value={c}>
            {c}
          </option>
        ))}
      </Select>
    </label>
  );

  return (
    <div className="max-w-4xl space-y-4">
      <ol className="flex items-center gap-2 text-xs" aria-label="Étapes de l'import">
        {STEPS.map((s, i) => {
          const active = s.key === step;
          const done = STEPS.findIndex((x) => x.key === step) > i;
          return (
            <li
              key={s.key}
              aria-current={active ? 'step' : undefined}
              className={`rounded-full px-2.5 py-1 font-medium ${
                active
                  ? 'bg-indigo-600 text-white'
                  : done
                    ? 'bg-indigo-50 text-indigo-700'
                    : 'bg-slate-100 text-slate-500'
              }`}
            >
              {i + 1}. {s.label}
            </li>
          );
        })}
      </ol>

      {error && <Alert variant="error">{error}</Alert>}

      {step === 'upload' && (
        <Card title="Fichier à importer">
          <Dropzone
            accept=".csv,.json"
            file={file}
            onFileSelect={handleFile}
            hint="CSV ou JSON — colonnes attendues : asset_id, name (optionnel), criticality (optionnel)"
          />
          {busy && <p className="mt-2 text-sm text-slate-500">Analyse du fichier…</p>}
          <div className="mt-4">
            <Button variant="ghost" size="sm" onClick={onCancel}>
              Annuler
            </Button>
          </div>
        </Card>
      )}

      {step === 'mapping' && preview && (
        <Card title="Mapping des colonnes">
          <p className="mb-3 text-sm text-slate-500">
            {file?.name} — {preview.row_count} lignes, {preview.columns.length} colonnes.
          </p>

          <div className="space-y-2">
            {columnSelect('Colonne identifiant', colAssetId, setColAssetId, true)}
            {columnSelect('Colonne nom', colName, setColName)}
            {columnSelect('Colonne criticité', colCriticality, setColCriticality)}
          </div>

          {preview.preview.length > 0 && (
            <div className="mt-4">
              <p className="mb-2 text-xs font-medium uppercase tracking-wide text-slate-400">
                Aperçu des premières lignes
              </p>
              <Table>
                <TableHead>
                  {preview.columns.map((c) => (
                    <TableHeaderCell key={c}>{c}</TableHeaderCell>
                  ))}
                </TableHead>
                <TableBody>
                  {preview.preview.map((row, i) => (
                    <TableRow key={i}>
                      {preview.columns.map((c) => (
                        <TableCell key={c} className="max-w-[180px] truncate text-xs">
                          {String(row[c] ?? '')}
                        </TableCell>
                      ))}
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}

          <div className="mt-4 flex gap-2">
            <Button onClick={handleImport} disabled={!colAssetId || busy}>
              {busy ? 'Import en cours…' : 'Importer'}
            </Button>
            <Button
              variant="ghost"
              onClick={() => {
                setStep('upload');
                setPreview(null);
              }}
            >
              Retour
            </Button>
          </div>
        </Card>
      )}

      {step === 'result' && result && (
        <Card title="Résultat de l'import">
          <Alert variant={result.errors > 0 ? 'warning' : 'success'}>
            {result.errors > 0 ? 'Import terminé avec des erreurs' : 'Import terminé'}
          </Alert>

          <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
            {(
              [
                ['tile-total', 'Lignes', result.total_rows, 'text-slate-900'],
                ['tile-created', 'Créés', result.created, 'text-emerald-600'],
                ['tile-updated', 'Mis à jour', result.updated, 'text-indigo-600'],
                ['tile-errors', 'Erreurs', result.errors, 'text-red-600'],
              ] as const
            ).map(([testid, label, value, color]) => (
              <div
                key={testid}
                data-testid={testid}
                className="rounded-card border border-slate-200 p-3 text-center"
              >
                <p className={`text-lg font-semibold ${color}`}>{value}</p>
                <p className="text-xs text-slate-500">{label}</p>
              </div>
            ))}
          </div>

          {result.error_details.length > 0 && (
            <ul className="mt-4 max-h-64 space-y-1 overflow-y-auto">
              {result.error_details.map((err, i) => (
                <li key={i} className="flex items-start gap-2 text-sm text-slate-700">
                  <AlertCircle size={14} className="mt-0.5 shrink-0 text-red-500" aria-hidden="true" />
                  <span>
                    <span className="text-slate-500">Ligne {err.row}</span>
                    {err.asset_id && <span className="text-slate-500"> ({err.asset_id})</span>}
                    {' : '}
                    {err.error}
                  </span>
                </li>
              ))}
            </ul>
          )}

          <div className="mt-4">
            <Button onClick={onDone}>Retour à la liste</Button>
          </div>
        </Card>
      )}
    </div>
  );
}
