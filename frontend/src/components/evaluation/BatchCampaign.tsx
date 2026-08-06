import { useRef, useState } from 'react';
import { useTreeStore } from '@/stores/treeStore';
import { evaluateApi } from '@/api/evaluate';
import { Alert, Button, Card, Dropzone } from '@/components/ui';
import { BatchSummary } from './BatchSummary';
import { BatchResultsTable } from './BatchResultsTable';
import { DeliverablesBar } from './DeliverablesBar';
import type { EvaluationResponse } from '@/types/evaluation';
import type { TreeStructure } from '@/types/tree';

/** Campagne batch : dropzone CSV → résumé → table de résultats → livrables (spec §3 Évaluation). */
export function BatchCampaign() {
  const treeId = useTreeStore((s) => s.treeId);
  const toApiStructure = useTreeStore((s) => s.toApiStructure);

  const [file, setFile] = useState<File | null>(null);
  const [response, setResponse] = useState<EvaluationResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  // Structure figée au lancement : les exports du DeliverablesBar doivent porter
  // sur la même structure que l'évaluation, même si l'arbre change ensuite.
  const structureRef = useRef<TreeStructure | null>(null);

  const handleRun = async () => {
    if (!file) return;
    setError(null);
    setIsLoading(true);
    try {
      const structure = toApiStructure();
      structureRef.current = structure;
      const res = await evaluateApi.evaluatePreviewCsv(file, structure, treeId ?? undefined, true);
      setResponse(res);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Échec de l'évaluation du fichier.");
      setResponse(null);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="space-y-4">
      <Card title="Fichier de campagne">
        <Dropzone
          accept=".csv"
          file={file}
          onFileSelect={(f) => { setFile(f); setResponse(null); setError(null); }}
          hint="Fichier CSV avec en-têtes (jusqu'à 50 000 lignes)"
        />
        {error && <div className="mt-3"><Alert variant="error">{error}</Alert></div>}
        <div className="mt-3">
          <Button onClick={handleRun} disabled={!file || isLoading}>
            {isLoading ? 'Évaluation en cours…' : 'Lancer la campagne'}
          </Button>
        </div>
      </Card>

      {response && (
        <>
          <BatchSummary response={response} />
          {file && structureRef.current && treeId != null && (
            <DeliverablesBar file={file} structure={structureRef.current} treeId={treeId} results={response.results} />
          )}
          <Card title="Résultats">
            <BatchResultsTable results={response.results} />
          </Card>
        </>
      )}
    </div>
  );
}
