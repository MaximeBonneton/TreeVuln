import { useState } from 'react';
import { FlaskConical } from 'lucide-react';
import { useTreeStore } from '@/stores/treeStore';
import { evaluateApi } from '@/api/evaluate';
import { Alert, Button, Card, DecisionBadge, EmptyState, Tabs, Textarea } from '@/components/ui';
import { DecisionTimeline } from './DecisionTimeline';
import { VulnFormFields, buildVulnerability } from './VulnFormFields';
import type { EvaluationResult } from '@/types/evaluation';

const SAMPLE_JSON = JSON.stringify(
  { cve_id: 'CVE-2024-1234', kev: true, epss_score: 0.5, cvss_score: 9.8, asset_criticality: 'High' },
  null,
  2
);

/** Test rapide : deux cards côte à côte — saisie (JSON ou formulaire) / résultat (badge + timeline). */
export function QuickTest() {
  const treeId = useTreeStore((s) => s.treeId);
  const fieldMapping = useTreeStore((s) => s.fieldMapping);
  const toApiStructure = useTreeStore((s) => s.toApiStructure);

  const [inputMode, setInputMode] = useState<'json' | 'form'>('json');
  const [json, setJson] = useState(SAMPLE_JSON);
  const [formValues, setFormValues] = useState<Record<string, string>>({});
  const [result, setResult] = useState<EvaluationResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const hasMapping = fieldMapping !== null && fieldMapping.fields.length > 0;

  const handleEvaluate = async () => {
    setError(null);
    let vulnerability: Record<string, unknown>;
    if (inputMode === 'form' && hasMapping) {
      vulnerability = buildVulnerability(fieldMapping.fields, formValues);
    } else {
      try {
        vulnerability = JSON.parse(json);
      } catch {
        setError('JSON invalide : vérifiez la syntaxe de la vulnérabilité de test.');
        return;
      }
    }
    setIsLoading(true);
    try {
      const res = await evaluateApi.evaluatePreview({
        structure: toApiStructure(),
        vulnerability,
        tree_id: treeId ?? undefined,
        include_path: true,
      });
      setResult(res);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Échec de l'évaluation.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
      <Card
        title="Vulnérabilité de test"
        actions={
          hasMapping ? (
            <Tabs
              tabs={[{ id: 'json', label: 'JSON' }, { id: 'form', label: 'Formulaire' }]}
              active={inputMode}
              onChange={(id) => setInputMode(id as 'json' | 'form')}
            />
          ) : undefined
        }
      >
        {inputMode === 'form' && hasMapping ? (
          <VulnFormFields
            fields={fieldMapping.fields}
            values={formValues}
            onChange={(name, value) => setFormValues((v) => ({ ...v, [name]: value }))}
          />
        ) : (
          <Textarea rows={10} value={json} onChange={(e) => setJson(e.target.value)} spellCheck={false} />
        )}
        {error && <div className="mt-3"><Alert variant="error">{error}</Alert></div>}
        <div className="mt-3">
          <Button onClick={handleEvaluate} disabled={isLoading}>
            {isLoading ? 'Évaluation…' : 'Évaluer'}
          </Button>
        </div>
      </Card>

      <Card title="Résultat">
        {result ? (
          <div>
            <div className="mb-4 flex items-center gap-3">
              <DecisionBadge decision={result.decision} />
              {result.vuln_id && <span className="text-sm text-slate-500">{result.vuln_id}</span>}
            </div>
            {result.error ? (
              <Alert variant="error" title="Erreur d'évaluation">{result.error}</Alert>
            ) : (
              <DecisionTimeline path={result.path} />
            )}
          </div>
        ) : (
          <EmptyState
            icon={FlaskConical}
            title="Aucun test lancé"
            description="Saisissez une vulnérabilité et cliquez sur Évaluer pour voir la décision et son chemin."
          />
        )}
      </Card>
    </div>
  );
}
