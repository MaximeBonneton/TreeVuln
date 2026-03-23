import { useState, useRef, useEffect } from 'react';
import { X, Play, Upload, Download, FileSpreadsheet, ChevronRight, ChevronDown, AlertTriangle, AlertCircle } from 'lucide-react';
import { evaluateApi } from '@/api';
import { useTreeStore } from '@/stores/treeStore';
import { DECISION_COLORS } from '@/constants/decisions';
import type { VulnerabilityInput, EvaluationResult, EvaluationResponse, DecisionPath, DiagnosticResult, DiagnosticItem } from '@/types';

interface TestPanelProps {
  onClose: () => void;
}

type TabType = 'single' | 'batch' | 'diagnostic';

const SAMPLE_VULN: VulnerabilityInput = {
  id: 'test-001',
  cve_id: 'CVE-2024-0001',
  cvss_score: 9.0,
  epss_score: 0.5,
  kev: true,
  asset_id: 'srv-prod-001',
  asset_criticality: 'High',
};

export function TestPanel({ onClose }: TestPanelProps) {
  const [activeTab, setActiveTab] = useState<TabType>('single');

  return (
    <div className="bg-white border-l shadow-lg w-[500px] flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b">
        <h3 className="font-bold text-gray-700">Tester l'arbre</h3>
        <button onClick={onClose} className="p-1 hover:bg-gray-100 rounded">
          <X size={20} />
        </button>
      </div>

      {/* Tabs */}
      <div className="flex border-b">
        <button
          onClick={() => setActiveTab('single')}
          className={`flex-1 px-4 py-2 text-sm font-medium ${
            activeTab === 'single'
              ? 'border-b-2 border-purple-500 text-purple-600'
              : 'text-gray-500 hover:text-gray-700'
          }`}
        >
          Test unitaire
        </button>
        <button
          onClick={() => setActiveTab('batch')}
          className={`flex-1 px-4 py-2 text-sm font-medium ${
            activeTab === 'batch'
              ? 'border-b-2 border-purple-500 text-purple-600'
              : 'text-gray-500 hover:text-gray-700'
          }`}
        >
          Test batch (CSV)
        </button>
        <button
          onClick={() => setActiveTab('diagnostic')}
          className={`flex-1 px-4 py-2 text-sm font-medium ${
            activeTab === 'diagnostic'
              ? 'border-b-2 border-purple-500 text-purple-600'
              : 'text-gray-500 hover:text-gray-700'
          }`}
        >
          Diagnostic
        </button>
      </div>

      {/* Content */}
      {activeTab === 'single' ? (
        <SingleTestTab />
      ) : activeTab === 'batch' ? (
        <BatchTestTab />
      ) : (
        <DiagnosticTab />
      )}
    </div>
  );
}

// ============================================
// ONGLET TEST UNITAIRE
// ============================================

function SingleTestTab() {
  const [vulnJson, setVulnJson] = useState(JSON.stringify(SAMPLE_VULN, null, 2));
  const [result, setResult] = useState<EvaluationResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const toApiStructure = useTreeStore((state) => state.toApiStructure);
  const treeId = useTreeStore((state) => state.treeId);

  const handleTest = async () => {
    setIsLoading(true);
    setError(null);
    setResult(null);

    try {
      const vuln = JSON.parse(vulnJson) as VulnerabilityInput;
      const structure = toApiStructure();
      const response = await evaluateApi.evaluatePreview({
        structure,
        vulnerability: vuln,
        tree_id: treeId,
        include_path: true,
      });
      setResult(response);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erreur inconnue');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      {/* Input */}
      <div className="p-4 border-b">
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Vulnérabilité (JSON)
        </label>
        <textarea
          value={vulnJson}
          onChange={(e) => setVulnJson(e.target.value)}
          className="w-full h-40 px-3 py-2 border rounded-md font-mono text-xs focus:ring-2 focus:ring-purple-500"
          spellCheck={false}
        />
        <button
          onClick={handleTest}
          disabled={isLoading}
          className="mt-3 w-full flex items-center justify-center gap-2 px-4 py-2 bg-purple-500 text-white rounded-md hover:bg-purple-600 disabled:opacity-50"
        >
          <Play size={18} />
          {isLoading ? 'Évaluation...' : 'Évaluer'}
        </button>
      </div>

      {/* Résultat */}
      <div className="flex-1 overflow-y-auto p-4">
        {error && (
          <div className="p-3 bg-red-50 border border-red-200 rounded-md text-red-700 text-sm">
            {error}
          </div>
        )}

        {result && <SingleResult result={result} />}

        {!result && !error && (
          <div className="text-center text-gray-500 py-8">
            <p>Entrez une vulnérabilité et cliquez sur "Évaluer"</p>
          </div>
        )}
      </div>
    </div>
  );
}

function SingleResult({ result }: { result: EvaluationResult }) {
  return (
    <div className="space-y-4">
      {/* Décision */}
      <div
        className="p-4 rounded-lg text-white text-center"
        style={{ backgroundColor: result.decision_color || '#6b7280' }}
      >
        <div className="text-sm opacity-80">Décision</div>
        <div className="text-2xl font-bold">{result.decision}</div>
      </div>

      {result.error && (
        <div className="p-3 bg-yellow-50 border border-yellow-200 rounded-md text-yellow-800 text-sm">
          <strong>Erreur:</strong> {result.error}
        </div>
      )}

      {result.path.length > 0 && (
        <div>
          <h4 className="font-medium text-gray-700 mb-2">Chemin de décision</h4>
          <div className="space-y-2">
            {result.path.map((step, index) => (
              <PathStep key={index} step={step} isLast={index === result.path.length - 1} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ============================================
// ONGLET TEST BATCH
// ============================================

function BatchTestTab() {
  const [file, setFile] = useState<File | null>(null);
  const [response, setResponse] = useState<EvaluationResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const toApiStructure = useTreeStore((state) => state.toApiStructure);
  const treeId = useTreeStore((state) => state.treeId);

  const handleFileSelect = (selectedFile: File) => {
    if (selectedFile.name.endsWith('.csv')) {
      setFile(selectedFile);
      setError(null);
      setResponse(null);
    } else {
      setError('Veuillez sélectionner un fichier CSV');
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const droppedFile = e.dataTransfer.files[0];
    if (droppedFile) handleFileSelect(droppedFile);
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => setIsDragging(false);

  const handleEvaluate = async () => {
    if (!file) return;

    setIsLoading(true);
    setError(null);

    try {
      const structure = toApiStructure();
      const result = await evaluateApi.evaluatePreviewCsv(file, structure, treeId, true);
      setResponse(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erreur lors de l\'évaluation');
    } finally {
      setIsLoading(false);
    }
  };

  const [exporting, setExporting] = useState(false);
  const [showExportMenu, setShowExportMenu] = useState(false);
  const exportMenuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!showExportMenu) return;
    const handleClickOutside = (e: MouseEvent) => {
      if (exportMenuRef.current && !exportMenuRef.current.contains(e.target as Node)) {
        setShowExportMenu(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [showExportMenu]);

  const handleExport = async (format: 'csv' | 'json') => {
    if (!file) return;
    setExporting(true);
    setShowExportMenu(false);

    try {
      const structure = toApiStructure();
      const blob = await evaluateApi.exportPreviewCsv(file, structure, format, treeId);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      const ext = format === 'csv' ? 'csv' : 'json';
      a.download = `results_${new Date().toISOString().slice(0, 10)}.${ext}`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur lors de l'export");
    } finally {
      setExporting(false);
    }
  };

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      {/* Zone d'upload */}
      <div className="p-4 border-b">
        <div
          onDrop={handleDrop}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onClick={() => fileInputRef.current?.click()}
          className={`
            border-2 border-dashed rounded-lg p-6 text-center cursor-pointer transition-colors
            ${isDragging ? 'border-purple-500 bg-purple-50' : 'border-gray-300 hover:border-gray-400'}
            ${file ? 'bg-green-50 border-green-400' : ''}
          `}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept=".csv"
            onChange={(e) => e.target.files?.[0] && handleFileSelect(e.target.files[0])}
            className="hidden"
          />

          {file ? (
            <div className="flex items-center justify-center gap-2 text-green-700">
              <FileSpreadsheet size={24} />
              <span className="font-medium">{file.name}</span>
              <span className="text-sm text-gray-500">
                ({(file.size / 1024).toFixed(1)} Ko)
              </span>
            </div>
          ) : (
            <>
              <Upload size={32} className="mx-auto text-gray-400 mb-2" />
              <p className="text-sm text-gray-600">
                Glissez-déposez un fichier CSV ou cliquez pour sélectionner
              </p>
              <p className="text-xs text-gray-400 mt-1">
                Colonnes attendues: cve_id, cvss_score, kev, asset_id, ...
              </p>
            </>
          )}
        </div>

        {file && (
          <button
            onClick={handleEvaluate}
            disabled={isLoading}
            className="mt-3 w-full flex items-center justify-center gap-2 px-4 py-2 bg-purple-500 text-white rounded-md hover:bg-purple-600 disabled:opacity-50"
          >
            <Play size={18} />
            {isLoading ? 'Évaluation en cours...' : `Évaluer ${file.name}`}
          </button>
        )}
      </div>

      {/* Erreur */}
      {error && (
        <div className="mx-4 mt-4 p-3 bg-red-50 border border-red-200 rounded-md text-red-700 text-sm">
          {error}
        </div>
      )}

      {/* Résultats */}
      {response && (
        <div className="flex-1 flex flex-col overflow-hidden">
          {/* Résumé */}
          <div className="p-4 border-b bg-gray-50">
            <div className="flex items-center justify-between mb-3">
              <h4 className="font-medium text-gray-700">Résumé</h4>
              <div className="relative" ref={exportMenuRef}>
                <button
                  onClick={() => setShowExportMenu(!showExportMenu)}
                  disabled={exporting}
                  className="flex items-center gap-1 px-3 py-1 text-sm bg-white border rounded-md hover:bg-gray-50 disabled:opacity-50"
                >
                  <Download size={14} />
                  {exporting ? 'Export...' : 'Exporter'}
                </button>
                {showExportMenu && (
                  <div className="absolute right-0 top-full mt-1 bg-white border rounded-md shadow-lg z-10 min-w-[140px]">
                    <button
                      onClick={() => handleExport('csv')}
                      className="w-full px-3 py-2 text-left text-sm hover:bg-gray-50 flex items-center gap-2"
                    >
                      <FileSpreadsheet size={14} />
                      Export CSV
                    </button>
                    <button
                      onClick={() => handleExport('json')}
                      className="w-full px-3 py-2 text-left text-sm hover:bg-gray-50 flex items-center gap-2"
                    >
                      <Download size={14} />
                      Export JSON
                    </button>
                  </div>
                )}
              </div>
            </div>

            <div className="grid grid-cols-4 gap-2 text-center text-sm">
              <div className="bg-white p-2 rounded border">
                <div className="text-lg font-bold text-gray-800">{response.total}</div>
                <div className="text-xs text-gray-500">Total</div>
              </div>
              <div className="bg-white p-2 rounded border">
                <div className="text-lg font-bold text-green-600">{response.success_count}</div>
                <div className="text-xs text-gray-500">Succès</div>
              </div>
              <div className="bg-white p-2 rounded border">
                <div className="text-lg font-bold text-red-600">{response.error_count}</div>
                <div className="text-xs text-gray-500">Erreurs</div>
              </div>
              <div className="bg-white p-2 rounded border">
                <div className="text-lg font-bold text-purple-600">
                  {response.total > 0 ? ((response.success_count / response.total) * 100).toFixed(0) : 0}%
                </div>
                <div className="text-xs text-gray-500">Taux</div>
              </div>
            </div>

            {/* Distribution des décisions */}
            <div className="mt-3 flex gap-2">
              {Object.entries(response.decision_summary).map(([decision, count]) => (
                <div
                  key={decision}
                  className="flex-1 p-2 rounded text-center text-white text-sm"
                  style={{ backgroundColor: DECISION_COLORS[decision] || '#6b7280' }}
                >
                  <div className="font-bold">{count}</div>
                  <div className="text-xs opacity-80">{decision}</div>
                </div>
              ))}
            </div>
          </div>

          {/* Tableau des résultats */}
          <div className="flex-1 overflow-y-auto">
            <ResultsTable results={response.results} />
          </div>
        </div>
      )}

      {!response && !error && !file && (
        <div className="flex-1 flex items-center justify-center text-gray-500">
          <p>Importez un fichier CSV pour commencer</p>
        </div>
      )}
    </div>
  );
}

function ResultsTable({ results }: { results: EvaluationResult[] }) {
  const [expandedRows, setExpandedRows] = useState<Set<number>>(new Set());

  const toggleRow = (index: number) => {
    const newExpanded = new Set(expandedRows);
    if (newExpanded.has(index)) {
      newExpanded.delete(index);
    } else {
      newExpanded.add(index);
    }
    setExpandedRows(newExpanded);
  };

  return (
    <div className="text-sm">
      {/* Header */}
      <div className="grid grid-cols-12 gap-2 px-4 py-2 bg-gray-100 font-medium text-gray-600 sticky top-0">
        <div className="col-span-1"></div>
        <div className="col-span-4">CVE / ID</div>
        <div className="col-span-3">Décision</div>
        <div className="col-span-4">Statut</div>
      </div>

      {/* Rows */}
      {results.map((result, index) => (
        <div key={index} className="border-b">
          <div
            className="grid grid-cols-12 gap-2 px-4 py-2 hover:bg-gray-50 cursor-pointer"
            onClick={() => toggleRow(index)}
          >
            <div className="col-span-1 flex items-center">
              {expandedRows.has(index) ? (
                <ChevronDown size={16} className="text-gray-400" />
              ) : (
                <ChevronRight size={16} className="text-gray-400" />
              )}
            </div>
            <div className="col-span-4 font-mono text-xs truncate">
              {result.vuln_id || `#${index + 1}`}
            </div>
            <div className="col-span-3">
              <span
                className="px-2 py-0.5 rounded text-white text-xs font-medium"
                style={{ backgroundColor: result.decision_color || DECISION_COLORS[result.decision] || '#6b7280' }}
              >
                {result.decision}
              </span>
            </div>
            <div className="col-span-4">
              {result.error ? (
                <span className="text-red-600 text-xs">{result.error}</span>
              ) : (
                <span className="text-green-600 text-xs">OK</span>
              )}
            </div>
          </div>

          {/* Expanded path */}
          {expandedRows.has(index) && result.path.length > 0 && (
            <div className="px-4 py-3 bg-gray-50 border-t">
              <div className="text-xs text-gray-500 mb-2">Chemin de décision:</div>
              <div className="flex flex-wrap items-center gap-1 text-xs">
                {result.path.map((step, stepIndex) => (
                  <span key={stepIndex} className="flex items-center gap-1">
                    <span className="bg-white border px-2 py-1 rounded">
                      <span className="font-medium">{step.node_label}</span>
                      {step.field_evaluated && (
                        <span className="text-gray-500 ml-1">
                          ({step.field_evaluated}={JSON.stringify(step.value_found)})
                        </span>
                      )}
                    </span>
                    {stepIndex < result.path.length - 1 && (
                      <ChevronRight size={12} className="text-gray-400" />
                    )}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

// ============================================
// COMPOSANTS PARTAGÉS
// ============================================

// ============================================
// ONGLET DIAGNOSTIC
// ============================================

function DiagnosticTab() {
  const [result, setResult] = useState<DiagnosticResult | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const toApiStructure = useTreeStore((state) => state.toApiStructure);
  const setDiagnosticHighlights = useTreeStore((state) => state.setDiagnosticHighlights);
  const clearDiagnosticHighlights = useTreeStore((state) => state.clearDiagnosticHighlights);
  const allHighlightsRef = useRef<Record<string, 'error' | 'warning'>>({});

  useEffect(() => {
    return () => clearDiagnosticHighlights();
  }, [clearDiagnosticHighlights]);

  const handleDiagnose = async () => {
    setIsLoading(true);
    setError(null);
    setResult(null);
    clearDiagnosticHighlights();

    try {
      const structure = toApiStructure();
      const response = await evaluateApi.diagnoseTree(structure);
      setResult(response);

      const highlights: Record<string, 'error' | 'warning'> = {};
      for (const item of response.errors) {
        if (item.node_id) highlights[item.node_id] = 'error';
      }
      for (const item of response.warnings) {
        if (item.node_id && !highlights[item.node_id]) highlights[item.node_id] = 'warning';
      }
      setDiagnosticHighlights(highlights);
      allHighlightsRef.current = highlights;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erreur lors du diagnostic');
    } finally {
      setIsLoading(false);
    }
  };

  const totalIssues = result ? result.errors.length + result.warnings.length : 0;

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      <div className="p-4 border-b">
        <button
          onClick={handleDiagnose}
          disabled={isLoading}
          className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-purple-500 text-white rounded-md hover:bg-purple-600 disabled:opacity-50"
        >
          <AlertTriangle size={18} />
          {isLoading ? 'Analyse en cours...' : "Analyser l'arbre"}
        </button>
      </div>

      {error && (
        <div className="mx-4 mt-4 p-3 bg-red-50 border border-red-200 rounded-md text-red-700 text-sm">
          {error}
        </div>
      )}

      {result && (
        <div className="flex-1 overflow-y-auto p-4">
          {totalIssues === 0 ? (
            <div className="text-center py-8 text-green-600">
              <p className="font-medium">Aucun probleme detecte</p>
              <p className="text-sm text-gray-500 mt-1">L'arbre est valide</p>
            </div>
          ) : (
            <div className="space-y-3">
              <p className="text-sm text-gray-600">
                {result.errors.length} erreur(s), {result.warnings.length} warning(s)
              </p>

              {result.errors.map((item, i) => (
                <DiagnosticItemRow key={`err-${i}`} item={item} allHighlights={allHighlightsRef.current} />
              ))}

              {result.warnings.map((item, i) => (
                <DiagnosticItemRow key={`warn-${i}`} item={item} allHighlights={allHighlightsRef.current} />
              ))}
            </div>
          )}
        </div>
      )}

      {!result && !error && (
        <div className="text-center text-gray-500 py-8">
          <p className="text-sm">Cliquez sur "Analyser" pour verifier votre arbre</p>
        </div>
      )}
    </div>
  );
}

function DiagnosticItemRow({ item, allHighlights }: { item: DiagnosticItem; allHighlights: Record<string, 'error' | 'warning'> }) {
  const setDiagnosticHighlights = useTreeStore((state) => state.setDiagnosticHighlights);

  const isError = item.severity === 'error';
  const bgClass = isError ? 'bg-red-50 border-red-200' : 'bg-orange-50 border-orange-200';
  const textClass = isError ? 'text-red-700' : 'text-orange-700';
  const badgeClass = isError ? 'bg-red-100 text-red-800' : 'bg-orange-100 text-orange-800';
  const IconComponent = isError ? AlertCircle : AlertTriangle;

  const handleMouseEnter = () => {
    if (item.node_id) {
      setDiagnosticHighlights({ [item.node_id]: item.severity });
    }
  };

  const handleMouseLeave = () => {
    setDiagnosticHighlights(allHighlights);
  };

  return (
    <div
      className={`p-3 border rounded-md ${bgClass} cursor-pointer`}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
    >
      <div className="flex items-start gap-2">
        <IconComponent size={16} className={`mt-0.5 flex-shrink-0 ${textClass}`} />
        <div className="flex-1">
          <span className={`text-xs font-mono px-1.5 py-0.5 rounded ${badgeClass}`}>
            {item.code}
          </span>
          <p className={`text-sm mt-1 ${textClass}`}>{item.message}</p>
          {item.node_id && (
            <p className="text-xs text-gray-500 mt-1 font-mono">
              Noeud: {item.node_id}
            </p>
          )}
        </div>
      </div>
    </div>
  );
}

// ============================================
// COMPOSANTS PARTAGES
// ============================================

function PathStep({ step, isLast }: { step: DecisionPath; isLast: boolean }) {
  const typeColors: Record<string, string> = {
    input: 'bg-blue-100 text-blue-800',
    lookup: 'bg-purple-100 text-purple-800',
    equation: 'bg-amber-100 text-amber-800',
    output: 'bg-green-100 text-green-800',
  };

  return (
    <div className="flex items-start gap-2">
      <div className="flex flex-col items-center">
        <div
          className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-medium ${typeColors[step.node_type] || 'bg-gray-100'}`}
        >
          {step.node_type[0].toUpperCase()}
        </div>
        {!isLast && <div className="w-0.5 h-8 bg-gray-300 mt-1" />}
      </div>

      <div className="flex-1 pb-2">
        <div className="font-medium text-sm">{step.node_label}</div>

        {step.field_evaluated && (
          <div className="text-xs text-gray-500">
            <span className="font-mono bg-gray-100 px-1 rounded">{step.field_evaluated}</span>
            {' = '}
            <span className="font-mono">{JSON.stringify(step.value_found)}</span>
          </div>
        )}

        {step.condition_matched && (
          <div className="flex items-center gap-1 text-xs text-gray-600 mt-1">
            <ChevronRight size={12} />
            <span className="bg-gray-200 px-2 py-0.5 rounded">{step.condition_matched}</span>
          </div>
        )}
      </div>
    </div>
  );
}
