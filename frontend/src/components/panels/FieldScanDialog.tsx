import { useState, useCallback } from 'react';
import { X, Upload, AlertCircle, Loader2 } from 'lucide-react';
import { fieldMappingApi } from '@/api';
import type { ScanResult } from '@/types';

interface FieldScanDialogProps {
  onClose: () => void;
  onResult: (result: ScanResult) => void;
}

export function FieldScanDialog({ onClose, onResult }: FieldScanDialogProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [isScanning, setIsScanning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [previewResult, setPreviewResult] = useState<ScanResult | null>(null);

  const handleFile = async (file: File) => {
    setError(null);
    setIsScanning(true);

    try {
      const result = await fieldMappingApi.scanFile(file);
      setPreviewResult(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erreur lors du scan');
    } finally {
      setIsScanning(false);
    }
  };

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);

    const file = e.dataTransfer.files[0];
    if (file) {
      handleFile(file);
    }
  }, []);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const handleFileSelect = () => {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.csv,.json';
    input.onchange = (e) => {
      const file = (e.target as HTMLInputElement).files?.[0];
      if (file) {
        handleFile(file);
      }
    };
    input.click();
  };

  const handleConfirm = () => {
    if (previewResult) {
      onResult(previewResult);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-[560px] max-h-[80vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b">
          <div>
            <h3 className="font-bold text-gray-800">Scanner un fichier</h3>
            <p className="text-xs text-gray-500 mt-0.5">
              CSV ou JSON pour détecter automatiquement les champs
            </p>
          </div>
          <button onClick={onClose} className="p-1 hover:bg-gray-100 rounded">
            <X size={20} />
          </button>
        </div>

        {/* Contenu */}
        <div className="flex-1 overflow-y-auto p-4">
          {!previewResult ? (
            <>
              {/* Zone de drop */}
              <div
                onDrop={handleDrop}
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onClick={handleFileSelect}
                className={`
                  border-2 border-dashed rounded-lg p-8 text-center cursor-pointer
                  transition-colors
                  ${
                    isDragging
                      ? 'border-blue-500 bg-blue-50'
                      : 'border-gray-300 hover:border-blue-400 hover:bg-gray-50'
                  }
                  ${isScanning ? 'pointer-events-none opacity-50' : ''}
                `}
              >
                {isScanning ? (
                  <Loader2 size={48} className="mx-auto text-blue-500 animate-spin" />
                ) : (
                  <Upload size={48} className="mx-auto text-gray-400" />
                )}
                <p className="mt-4 font-medium text-gray-700">
                  {isScanning
                    ? 'Analyse en cours...'
                    : 'Glissez un fichier ici ou cliquez pour sélectionner'}
                </p>
                <p className="mt-2 text-sm text-gray-500">
                  Formats supportés: CSV, JSON
                </p>
              </div>

              {/* Erreur */}
              {error && (
                <div className="mt-4 p-3 bg-red-50 text-red-700 text-sm rounded-md flex items-center gap-2">
                  <AlertCircle size={16} />
                  {error}
                </div>
              )}

              {/* Info */}
              <div className="mt-4 p-3 bg-blue-50 rounded-md text-sm text-blue-800">
                <p className="font-medium">Comment ça marche ?</p>
                <ul className="mt-2 space-y-1 text-blue-700">
                  <li>• Les 100 premières lignes sont analysées</li>
                  <li>• Les types sont automatiquement détectés</li>
                  <li>• Des exemples de valeurs sont collectés</li>
                </ul>
              </div>
            </>
          ) : (
            <>
              {/* Résultat du scan */}
              <div className="mb-4 p-3 bg-green-50 rounded-md">
                <p className="font-medium text-green-800">
                  {previewResult.fields.length} champs détectés
                </p>
                <p className="text-sm text-green-700">
                  {previewResult.rows_scanned} lignes analysées ({previewResult.source_type.toUpperCase()})
                </p>
              </div>

              {/* Warnings */}
              {previewResult.warnings.length > 0 && (
                <div className="mb-4 p-3 bg-amber-50 rounded-md">
                  <p className="font-medium text-amber-800">Avertissements</p>
                  <ul className="mt-1 text-sm text-amber-700">
                    {previewResult.warnings.map((w, i) => (
                      <li key={i}>• {w}</li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Liste des champs détectés */}
              <div className="border rounded-md overflow-hidden">
                <table className="w-full text-sm">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-3 py-2 text-left font-medium text-gray-600">
                        Champ
                      </th>
                      <th className="px-3 py-2 text-left font-medium text-gray-600">
                        Type
                      </th>
                      <th className="px-3 py-2 text-left font-medium text-gray-600">
                        Exemples
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y">
                    {previewResult.fields.map((field) => (
                      <tr key={field.name} className="hover:bg-gray-50">
                        <td className="px-3 py-2">
                          <div className="font-medium text-gray-800">
                            {field.name}
                          </div>
                          {field.required && (
                            <span className="text-xs text-blue-600">Requis</span>
                          )}
                        </td>
                        <td className="px-3 py-2">
                          <span className="px-2 py-0.5 bg-gray-100 text-gray-600 text-xs rounded">
                            {field.type}
                          </span>
                        </td>
                        <td className="px-3 py-2 text-gray-600">
                          {field.examples.slice(0, 2).map(String).join(', ')}
                          {field.examples.length > 2 && '...'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-2 p-4 border-t bg-gray-50">
          <button
            onClick={onClose}
            className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-md"
          >
            Annuler
          </button>
          {previewResult && (
            <>
              <button
                onClick={() => setPreviewResult(null)}
                className="px-4 py-2 border rounded-md hover:bg-gray-100"
              >
                Nouveau scan
              </button>
              <button
                onClick={handleConfirm}
                className="px-4 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600"
              >
                Utiliser ces champs
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
