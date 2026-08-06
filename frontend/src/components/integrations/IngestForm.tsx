import { useState } from 'react';
import { Plus, Trash2 } from 'lucide-react';
import { Alert, Button, Input, Switch } from '@/components/ui';
import type { IngestEndpoint, IngestEndpointCreate } from '@/types/ingest';

interface MappingPair {
  source: string;
  target: string;
}

interface IngestFormProps {
  /** null = création ; sinon édition. */
  endpoint: IngestEndpoint | null;
  onSubmit: (data: IngestEndpointCreate) => Promise<void>;
  onCancel: () => void;
}

const slugify = (value: string) =>
  value.toLowerCase().replace(/[^a-z0-9-]/g, '-').replace(/-+/g, '-').replace(/^-|-$/g, '');

// Sanitisation « live » du champ slug lui-même : contrairement à `slugify`, ne retire pas
// le tiret final tant que la saisie est en cours (sinon un tiret tapé est aussitôt effacé
// avant l'arrivée du caractère suivant, ce qui « mange » les tirets au fil de la frappe).
const sanitizeSlugInput = (value: string) =>
  value.toLowerCase().replace(/[^a-z0-9-]/g, '-').replace(/-+/g, '-').replace(/^-/, '');

/** Formulaire endpoint d'ingestion (drawer) : nom, slug, mapping de champs, toggles. */
export function IngestForm({ endpoint, onSubmit, onCancel }: IngestFormProps) {
  const [name, setName] = useState(endpoint?.name ?? '');
  const [slug, setSlug] = useState(endpoint?.slug ?? '');
  // En création, le slug suit le nom tant qu'il n'a pas été édité à la main
  const [slugTouched, setSlugTouched] = useState(endpoint !== null);
  const [mapping, setMapping] = useState<MappingPair[]>(
    Object.entries(endpoint?.field_mapping ?? {}).map(([source, target]) => ({ source, target }))
  );
  const [autoEvaluate, setAutoEvaluate] = useState(endpoint?.auto_evaluate ?? true);
  const [isActive, setIsActive] = useState(endpoint?.is_active ?? true);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const handleNameChange = (value: string) => {
    setName(value);
    if (!slugTouched) setSlug(slugify(value));
  };

  const handleSubmit = async () => {
    setError(null);
    if (!name.trim() || !slug.trim()) {
      setError('Nom et slug sont requis.');
      return;
    }
    const data: IngestEndpointCreate = {
      name: name.trim(),
      // slugify() final : nettoie un éventuel tiret de fin laissé par la saisie manuelle
      slug: slugify(slug),
      field_mapping: Object.fromEntries(
        mapping.filter((m) => m.source.trim() && m.target.trim()).map((m) => [m.source.trim(), m.target.trim()])
      ),
      auto_evaluate: autoEvaluate,
      is_active: isActive,
    };
    setSaving(true);
    try {
      await onSubmit(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Échec de la sauvegarde de l'endpoint.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-4">
      <div>
        <label htmlFor="ing-name" className="mb-1 block text-sm font-medium text-slate-700">Nom</label>
        <Input id="ing-name" value={name} onChange={(e) => handleNameChange(e.target.value)} placeholder="Scanner Nessus" />
      </div>
      <div>
        <label htmlFor="ing-slug" className="mb-1 block text-sm font-medium text-slate-700">Slug</label>
        <Input
          id="ing-slug"
          value={slug}
          onChange={(e) => { setSlugTouched(true); setSlug(sanitizeSlugInput(e.target.value)); }}
          placeholder="scanner-nessus"
        />
        <p className="mt-1 text-xs text-slate-500">
          URL d'ingestion : POST /api/v1/ingest/{slug || '…'} — clé à passer dans l'en-tête <code className="font-mono">X-API-Key</code>
        </p>
      </div>

      <div>
        <p className="mb-1 text-sm font-medium text-slate-700">Mapping de champs (source → champ TreeVuln)</p>
        <div className="space-y-2">
          {mapping.map((m, i) => (
            <div key={i} className="flex items-center gap-2">
              <Input
                placeholder="Champ source"
                value={m.source}
                onChange={(e) => setMapping((prev) => prev.map((p, j) => (j === i ? { ...p, source: e.target.value } : p)))}
              />
              <Input
                placeholder="Champ TreeVuln"
                value={m.target}
                onChange={(e) => setMapping((prev) => prev.map((p, j) => (j === i ? { ...p, target: e.target.value } : p)))}
              />
              <button
                type="button"
                aria-label={`Supprimer le mapping ${m.source || i + 1}`}
                onClick={() => setMapping((prev) => prev.filter((_, j) => j !== i))}
                className="shrink-0 rounded-md p-1.5 text-slate-400 hover:bg-red-50 hover:text-red-600"
              >
                <Trash2 size={14} />
              </button>
            </div>
          ))}
          <Button variant="ghost" size="sm" onClick={() => setMapping((prev) => [...prev, { source: '', target: '' }])}>
            <Plus size={14} aria-hidden="true" /> Ajouter un mapping
          </Button>
        </div>
      </div>

      <div className="space-y-2">
        <div className="flex items-center gap-2">
          <Switch checked={autoEvaluate} onChange={setAutoEvaluate} label="Évaluation automatique" />
          <span className="text-sm text-slate-700">Évaluer automatiquement à la réception</span>
        </div>
        <div className="flex items-center gap-2">
          <Switch checked={isActive} onChange={setIsActive} label="Endpoint actif" />
          <span className="text-sm text-slate-700">Actif</span>
        </div>
      </div>

      {error && <Alert variant="error">{error}</Alert>}

      <div className="flex justify-end gap-2 pt-2">
        <Button variant="ghost" onClick={onCancel}>Annuler</Button>
        <Button onClick={handleSubmit} disabled={saving}>
          {saving ? 'Sauvegarde…' : endpoint ? 'Enregistrer' : 'Créer'}
        </Button>
      </div>
    </div>
  );
}
