import { useState } from 'react';
import { Plus, Trash2 } from 'lucide-react';
import { Alert, Button, Input, Switch } from '@/components/ui';
import { WEBHOOK_EVENTS, type Webhook, type WebhookCreate } from '@/types/webhook';

interface HeaderPair {
  key: string;
  value: string;
}

interface WebhookFormProps {
  /** null = création ; sinon édition. */
  webhook: Webhook | null;
  onSubmit: (data: WebhookCreate) => Promise<void>;
  onCancel: () => void;
}

/** Formulaire webhook (drawer) : nom, URL, secret, en-têtes, événements, actif. */
export function WebhookForm({ webhook, onSubmit, onCancel }: WebhookFormProps) {
  const [name, setName] = useState(webhook?.name ?? '');
  const [url, setUrl] = useState(webhook?.url ?? '');
  const [secret, setSecret] = useState('');
  const [headers, setHeaders] = useState<HeaderPair[]>(
    Object.entries(webhook?.headers ?? {}).map(([key, value]) => ({ key, value }))
  );
  const [events, setEvents] = useState<string[]>(webhook?.events ?? []);
  const [isActive, setIsActive] = useState(webhook?.is_active ?? true);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const toggleEvent = (value: string) =>
    setEvents((prev) => (prev.includes(value) ? prev.filter((e) => e !== value) : [...prev, value]));

  const handleSubmit = async () => {
    setError(null);
    if (!name.trim() || !url.trim() || events.length === 0) {
      setError('Nom, URL et au moins un événement sont requis.');
      return;
    }
    const data: WebhookCreate = {
      name: name.trim(),
      url: url.trim(),
      headers: Object.fromEntries(
        headers.filter((h) => h.key.trim()).map((h) => [h.key.trim(), h.value])
      ),
      events,
      is_active: isActive,
    };
    // Secret envoyé seulement s'il a été saisi (sinon le backend conserve l'existant)
    if (secret) data.secret = secret;
    setSaving(true);
    try {
      await onSubmit(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Échec de la sauvegarde du webhook.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-4">
      <div>
        <label htmlFor="wh-name" className="mb-1 block text-sm font-medium text-slate-700">Nom</label>
        <Input id="wh-name" value={name} onChange={(e) => setName(e.target.value)} placeholder="SIEM production" />
      </div>
      <div>
        <label htmlFor="wh-url" className="mb-1 block text-sm font-medium text-slate-700">URL</label>
        <Input id="wh-url" type="url" value={url} onChange={(e) => setUrl(e.target.value)} placeholder="https://…" />
      </div>
      <div>
        <label htmlFor="wh-secret" className="mb-1 block text-sm font-medium text-slate-700">
          Secret (signature HMAC)
        </label>
        <Input
          id="wh-secret"
          type="password"
          value={secret}
          onChange={(e) => setSecret(e.target.value)}
          placeholder={webhook?.has_secret ? 'Laisser vide pour garder le secret inchangé' : 'Optionnel'}
        />
      </div>

      <div>
        <p className="mb-1 text-sm font-medium text-slate-700">Événements déclencheurs</p>
        <div className="flex flex-wrap gap-1.5">
          {WEBHOOK_EVENTS.map((ev) => {
            const selected = events.includes(ev.value);
            return (
              <button
                key={ev.value}
                type="button"
                onClick={() => toggleEvent(ev.value)}
                className={`rounded-full border px-2.5 py-1 text-xs font-medium transition-colors ${
                  selected ? 'border-transparent text-white' : 'border-slate-300 text-slate-600 hover:bg-slate-100'
                }`}
                style={selected ? { backgroundColor: ev.color } : undefined}
              >
                {ev.value}
              </button>
            );
          })}
        </div>
      </div>

      <div>
        <p className="mb-1 text-sm font-medium text-slate-700">En-têtes personnalisés</p>
        <div className="space-y-2">
          {headers.map((h, i) => (
            <div key={i} className="flex items-center gap-2">
              <Input
                placeholder="Nom de l’en-tête"
                value={h.key}
                onChange={(e) => setHeaders((prev) => prev.map((p, j) => (j === i ? { ...p, key: e.target.value } : p)))}
              />
              <Input
                placeholder="Valeur"
                value={h.value}
                onChange={(e) => setHeaders((prev) => prev.map((p, j) => (j === i ? { ...p, value: e.target.value } : p)))}
              />
              <button
                type="button"
                aria-label={`Supprimer l’en-tête ${h.key || i + 1}`}
                onClick={() => setHeaders((prev) => prev.filter((_, j) => j !== i))}
                className="shrink-0 rounded-md p-1.5 text-slate-400 hover:bg-red-50 hover:text-red-600"
              >
                <Trash2 size={14} />
              </button>
            </div>
          ))}
          <Button variant="ghost" size="sm" onClick={() => setHeaders((prev) => [...prev, { key: '', value: '' }])}>
            <Plus size={14} aria-hidden="true" /> Ajouter un en-tête
          </Button>
        </div>
      </div>

      <div className="flex items-center gap-2">
        <Switch checked={isActive} onChange={setIsActive} label="Webhook actif" />
        <span className="text-sm text-slate-700">Actif</span>
      </div>

      {error && <Alert variant="error">{error}</Alert>}

      <div className="flex justify-end gap-2 pt-2">
        <Button variant="ghost" onClick={onCancel}>Annuler</Button>
        <Button onClick={handleSubmit} disabled={saving}>
          {saving ? 'Sauvegarde…' : webhook ? 'Enregistrer' : 'Créer'}
        </Button>
      </div>
    </div>
  );
}
