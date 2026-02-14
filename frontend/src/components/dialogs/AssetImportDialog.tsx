import { useState, useRef } from 'react';
import { X, Upload, FileSpreadsheet, Check, AlertCircle, ArrowRight } from 'lucide-react';
import { assetsApi } from '@/api';
import type { AssetImportPreview, AssetImportResult } from '@/types';

interface AssetImportDialogProps {
  treeId: number;
  treeName: string;
  onClose: () => void;
  onImported: () => void;
}

type Step = 'upload' | 'mapping' | 'result';

export function AssetImportDialog({ treeId, treeName, onClose, onImported }: AssetImportDialogProps) {
  const [step, setStep] = useState<Step>('upload');
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<AssetImportPreview | null>(null);
  const [result, setResult] = useState<AssetImportResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Mapping state
  const [colAssetId, setColAssetId] = useState('');
  const [colName, setColName] = useState('');
  const [colCriticality, setColCriticality] = useState('');

  const handleFileSelect = async (selectedFile: File) => {
    const isValid = selectedFile.name.endsWith('.csv') || selectedFile.name.endsWith('.json');
    if (!isValid) {
      setError('Format non supporté. Utilisez CSV ou JSON.');
      return;
    }

    setFile(selectedFile);
    setError(null);
    setLoading(true);

    try {
      const previewData = await assetsApi.previewImport(selectedFile);
      setPreview(previewData);

      // Auto-detect column mapping
      const cols = previewData.columns.map((c) => c.toLowerCase());
      const assetIdIdx = cols.findIndex((c) => c === 'asset_id' || c === 'assetid' || c === 'id');
      const nameIdx = cols.findIndex((c) => c === 'name' || c === 'hostname' || c === 'nom');
      const critIdx = cols.findIndex((c) => c === 'criticality' || c === 'criticite' || c === 'priority');

      if (assetIdIdx >= 0) setColAssetId(previewData.columns[assetIdIdx]);
      if (nameIdx >= 0) setColName(previewData.columns[nameIdx]);
      if (critIdx >= 0) setColCriticality(previewData.columns[critIdx]);

      setStep('mapping');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erreur de preview');
    } finally {
      setLoading(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const droppedFile = e.dataTransfer.files[0];
    if (droppedFile) handleFileSelect(droppedFile);
  };

  const handleImport = async () => {
    if (!file || !colAssetId) return;

    setLoading(true);
    setError(null);

    try {
      const importResult = await assetsApi.importAssets(treeId, file, {
        asset_id: colAssetId,
        name: colName || undefined,
        criticality: colCriticality || undefined,
      });
      setResult(importResult);
      setStep('result');
      onImported();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur lors de l'import");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-2xl max-h-[80vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b">
          <div className="flex items-center gap-2">
            <Upload size={20} className="text-blue-600" />
            <h2 className="text-lg font-semibold">Importer des assets</h2>
            <span className="text-sm text-gray-500">- {treeName}</span>
          </div>
          <button onClick={onClose} className="p-1 hover:bg-gray-100 rounded-md">
            <X size={20} className="text-gray-500" />
          </button>
        </div>

        {/* Steps indicator */}
        <div className="flex items-center gap-2 px-4 pt-3 text-sm">
          {(['upload', 'mapping', 'result'] as Step[]).map((s, i) => (
            <div key={s} className="flex items-center gap-2">
              {i > 0 && <ArrowRight size={14} className="text-gray-300" />}
              <span
                className={`px-2 py-0.5 rounded-full text-xs ${
                  step === s
                    ? 'bg-blue-100 text-blue-700 font-medium'
                    : step === 'result' || (step === 'mapping' && s === 'upload')
                      ? 'bg-green-100 text-green-700'
                      : 'bg-gray-100 text-gray-500'
                }`}
              >
                {s === 'upload' ? '1. Fichier' : s === 'mapping' ? '2. Mapping' : '3. Resultat'}
              </span>
            </div>
          ))}
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-4">
          {error && (
            <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-md text-red-700 text-sm flex items-center gap-2">
              <AlertCircle size={16} />
              {error}
            </div>
          )}

          {step === 'upload' && (
            <UploadStep
              isDragging={isDragging}
              loading={loading}
              fileInputRef={fileInputRef}
              onDrop={handleDrop}
              onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
              onDragLeave={() => setIsDragging(false)}
              onFileSelect={(e) => e.target.files?.[0] && handleFileSelect(e.target.files[0])}
              onClick={() => fileInputRef.current?.click()}
            />
          )}

          {step === 'mapping' && preview && (
            <MappingStep
              preview={preview}
              file={file!}
              colAssetId={colAssetId}
              colName={colName}
              colCriticality={colCriticality}
              onColAssetIdChange={setColAssetId}
              onColNameChange={setColName}
              onColCriticalityChange={setColCriticality}
            />
          )}

          {step === 'result' && result && <ResultStep result={result} />}
        </div>

        {/* Footer */}
        <div className="flex justify-end gap-2 p-4 border-t bg-gray-50 rounded-b-lg">
          {step === 'result' ? (
            <button
              onClick={onClose}
              className="px-4 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600"
            >
              Fermer
            </button>
          ) : (
            <>
              <button
                onClick={onClose}
                className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-md"
              >
                Annuler
              </button>
              {step === 'mapping' && (
                <button
                  onClick={handleImport}
                  disabled={loading || !colAssetId}
                  className="px-4 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600 disabled:opacity-50"
                >
                  {loading ? 'Import en cours...' : 'Importer'}
                </button>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}

function UploadStep({
  isDragging,
  loading,
  fileInputRef,
  onDrop,
  onDragOver,
  onDragLeave,
  onFileSelect,
  onClick,
}: {
  isDragging: boolean;
  loading: boolean;
  fileInputRef: React.RefObject<HTMLInputElement>;
  onDrop: (e: React.DragEvent) => void;
  onDragOver: (e: React.DragEvent) => void;
  onDragLeave: () => void;
  onFileSelect: (e: React.ChangeEvent<HTMLInputElement>) => void;
  onClick: () => void;
}) {
  return (
    <div
      onDrop={onDrop}
      onDragOver={onDragOver}
      onDragLeave={onDragLeave}
      onClick={onClick}
      className={`
        border-2 border-dashed rounded-lg p-12 text-center cursor-pointer transition-colors
        ${isDragging ? 'border-blue-500 bg-blue-50' : 'border-gray-300 hover:border-gray-400'}
      `}
    >
      <input
        ref={fileInputRef}
        type="file"
        accept=".csv,.json"
        onChange={onFileSelect}
        className="hidden"
      />

      {loading ? (
        <div className="text-blue-600">
          <div className="animate-spin w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full mx-auto mb-2" />
          <p className="text-sm">Analyse du fichier...</p>
        </div>
      ) : (
        <>
          <Upload size={40} className="mx-auto text-gray-400 mb-3" />
          <p className="text-sm text-gray-600 font-medium">
            Glissez-deposez un fichier CSV ou JSON
          </p>
          <p className="text-xs text-gray-400 mt-2">
            Colonnes attendues : asset_id, name (optionnel), criticality (optionnel)
          </p>
        </>
      )}
    </div>
  );
}

function MappingStep({
  preview,
  file,
  colAssetId,
  colName,
  colCriticality,
  onColAssetIdChange,
  onColNameChange,
  onColCriticalityChange,
}: {
  preview: AssetImportPreview;
  file: File;
  colAssetId: string;
  colName: string;
  colCriticality: string;
  onColAssetIdChange: (v: string) => void;
  onColNameChange: (v: string) => void;
  onColCriticalityChange: (v: string) => void;
}) {
  return (
    <div className="space-y-4">
      {/* File info */}
      <div className="flex items-center gap-2 p-3 bg-gray-50 rounded-lg">
        <FileSpreadsheet size={20} className="text-green-600" />
        <span className="font-medium text-sm">{file.name}</span>
        <span className="text-xs text-gray-500">
          ({preview.row_count} lignes, {preview.columns.length} colonnes)
        </span>
      </div>

      {/* Column mapping */}
      <div>
        <h4 className="font-medium text-gray-700 mb-3">Mapping des colonnes</h4>
        <div className="space-y-3">
          <MappingSelect
            label="Asset ID *"
            value={colAssetId}
            onChange={onColAssetIdChange}
            columns={preview.columns}
            required
          />
          <MappingSelect
            label="Nom"
            value={colName}
            onChange={onColNameChange}
            columns={preview.columns}
          />
          <MappingSelect
            label="Criticite"
            value={colCriticality}
            onChange={onColCriticalityChange}
            columns={preview.columns}
          />
        </div>
      </div>

      {/* Preview table */}
      {preview.preview.length > 0 && (
        <div>
          <h4 className="font-medium text-gray-700 mb-2">Apercu (5 premieres lignes)</h4>
          <div className="overflow-x-auto border rounded-lg">
            <table className="w-full text-xs">
              <thead>
                <tr className="bg-gray-50">
                  {preview.columns.map((col) => (
                    <th key={col} className="px-3 py-2 text-left font-medium text-gray-600 border-b">
                      {col}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {preview.preview.map((row, i) => (
                  <tr key={i} className="border-b last:border-0">
                    {preview.columns.map((col) => (
                      <td key={col} className="px-3 py-1.5 text-gray-700 truncate max-w-[150px]">
                        {String(row[col] ?? '')}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

function MappingSelect({
  label,
  value,
  onChange,
  columns,
  required = false,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  columns: string[];
  required?: boolean;
}) {
  return (
    <div className="flex items-center gap-3">
      <label className="w-28 text-sm text-gray-600">{label}</label>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className={`flex-1 px-3 py-1.5 border rounded-md text-sm ${
          required && !value ? 'border-red-300' : ''
        }`}
      >
        <option value="">-- Non utilise --</option>
        {columns.map((col) => (
          <option key={col} value={col}>
            {col}
          </option>
        ))}
      </select>
    </div>
  );
}

function ResultStep({ result }: { result: AssetImportResult }) {
  const hasErrors = result.errors > 0;

  return (
    <div className="space-y-4">
      {/* Summary */}
      <div className={`p-4 rounded-lg ${hasErrors ? 'bg-yellow-50' : 'bg-green-50'}`}>
        <div className="flex items-center gap-2 mb-3">
          <Check size={20} className={hasErrors ? 'text-yellow-600' : 'text-green-600'} />
          <span className="font-medium">
            Import {hasErrors ? 'termine avec des erreurs' : 'reussi'}
          </span>
        </div>

        <div className="grid grid-cols-4 gap-2 text-center text-sm">
          <div className="bg-white p-2 rounded border">
            <div className="text-lg font-bold">{result.total_rows}</div>
            <div className="text-xs text-gray-500">Total</div>
          </div>
          <div className="bg-white p-2 rounded border">
            <div className="text-lg font-bold text-green-600">{result.created}</div>
            <div className="text-xs text-gray-500">Crees</div>
          </div>
          <div className="bg-white p-2 rounded border">
            <div className="text-lg font-bold text-blue-600">{result.updated}</div>
            <div className="text-xs text-gray-500">Mis a jour</div>
          </div>
          <div className="bg-white p-2 rounded border">
            <div className="text-lg font-bold text-red-600">{result.errors}</div>
            <div className="text-xs text-gray-500">Erreurs</div>
          </div>
        </div>
      </div>

      {/* Error details */}
      {result.error_details.length > 0 && (
        <div>
          <h4 className="font-medium text-gray-700 mb-2">Detail des erreurs</h4>
          <div className="max-h-48 overflow-y-auto border rounded-lg">
            {result.error_details.map((err, i) => (
              <div key={i} className="px-3 py-2 border-b last:border-0 text-sm flex items-start gap-2">
                <AlertCircle size={14} className="text-red-500 mt-0.5 flex-shrink-0" />
                <div>
                  <span className="text-gray-500">Ligne {err.row}</span>
                  {err.asset_id && <span className="text-gray-500 ml-1">({err.asset_id})</span>}
                  <span className="text-gray-700 ml-1">: {err.error}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export default AssetImportDialog;
