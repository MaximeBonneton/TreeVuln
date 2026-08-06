import { Fragment, useMemo, useState } from 'react';
import { ArrowUpDown, ChevronDown, ChevronRight } from 'lucide-react';
import {
  Button, DecisionBadge, EmptyState, Select,
  Table, TableBody, TableCell, TableHead, TableHeaderCell,
} from '@/components/ui';
import { DecisionTimeline } from './DecisionTimeline';
import type { EvaluationResult } from '@/types/evaluation';

// F-7 : pagination pour les gros batchs (jusqu'à 10 000 résultats) — sinon l'UI se fige
const PAGE_SIZE = 100;

type SortKey = 'vuln_id' | 'decision';

/** Table des résultats : filtre par décision, tri, audit trail dépliable, pagination (spec §3). */
export function BatchResultsTable({ results }: { results: EvaluationResult[] }) {
  const [decisionFilter, setDecisionFilter] = useState('');
  const [sortKey, setSortKey] = useState<SortKey | null>(null);
  const [sortAsc, setSortAsc] = useState(true);
  const [page, setPage] = useState(0);
  const [expanded, setExpanded] = useState<Set<string>>(new Set());

  const decisions = useMemo(
    () => Array.from(new Set(results.map((r) => r.decision))).sort(),
    [results]
  );

  const visible = useMemo(() => {
    let rows = decisionFilter ? results.filter((r) => r.decision === decisionFilter) : [...results];
    if (sortKey) {
      rows.sort((a, b) => {
        const av = (a[sortKey] ?? '').toString();
        const bv = (b[sortKey] ?? '').toString();
        return sortAsc ? av.localeCompare(bv) : bv.localeCompare(av);
      });
    }
    return rows;
  }, [results, decisionFilter, sortKey, sortAsc]);

  const pageRows = visible.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE);
  const pageCount = Math.max(1, Math.ceil(visible.length / PAGE_SIZE));

  const toggleSort = (key: SortKey) => {
    if (sortKey === key) setSortAsc((a) => !a);
    else { setSortKey(key); setSortAsc(true); }
    setPage(0);
  };

  const toggleRow = (resultId: string) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(resultId)) next.delete(resultId);
      else next.add(resultId);
      return next;
    });
  };

  if (results.length === 0) {
    return <EmptyState title="Aucun résultat" description="La campagne n'a produit aucun résultat." />;
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        <label htmlFor="decision-filter" className="text-sm text-slate-600">Filtrer par décision</label>
        <Select
          id="decision-filter"
          value={decisionFilter}
          onChange={(e) => { setDecisionFilter(e.target.value); setPage(0); setExpanded(new Set()); }}
          className="w-44"
        >
          <option value="">Toutes</option>
          {decisions.map((d) => <option key={d} value={d}>{d}</option>)}
        </Select>
        <span className="ml-auto text-sm text-slate-500">{visible.length} résultat(s)</span>
      </div>

      <Table>
        <TableHead>
          <TableHeaderCell className="w-8">{''}</TableHeaderCell>
          <TableHeaderCell>
            <button type="button" aria-label="Trier par identifiant" onClick={() => toggleSort('vuln_id')} className="inline-flex items-center gap-1">
              Identifiant <ArrowUpDown size={12} aria-hidden="true" />
            </button>
          </TableHeaderCell>
          <TableHeaderCell>
            <button type="button" aria-label="Trier par décision" onClick={() => toggleSort('decision')} className="inline-flex items-center gap-1">
              Décision <ArrowUpDown size={12} aria-hidden="true" />
            </button>
          </TableHeaderCell>
          <TableHeaderCell>Erreur</TableHeaderCell>
        </TableHead>
        <TableBody>
          {pageRows.map((result) => {
            const resultId = result.vuln_id || '';
            const isOpen = expanded.has(resultId);
            return (
              <Fragment key={resultId || Math.random()}>
                <tr data-testid="result-row" className="hover:bg-slate-50">
                  <TableCell>
                    <button
                      type="button"
                      aria-label={`${isOpen ? 'Replier' : 'Déplier'} ${resultId}`}
                      aria-expanded={isOpen}
                      onClick={() => toggleRow(resultId)}
                      className="rounded p-0.5 text-slate-400 hover:bg-slate-100 hover:text-slate-600"
                    >
                      {isOpen ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                    </button>
                  </TableCell>
                  <TableCell className="font-mono text-xs">{result.vuln_id ?? '—'}</TableCell>
                  <TableCell><DecisionBadge decision={result.decision} size="sm" /></TableCell>
                  <TableCell className="text-xs text-red-600">{result.error ?? ''}</TableCell>
                </tr>
                {isOpen && (
                  <tr className="hover:bg-slate-50">
                    <td className="bg-slate-50 px-4 py-3 text-slate-700" colSpan={4}>
                      {result.path.length > 0
                        ? <DecisionTimeline path={result.path} />
                        : <span className="text-xs text-slate-500">Pas de chemin de décision disponible.</span>}
                    </td>
                  </tr>
                )}
              </Fragment>
            );
          })}
        </TableBody>
      </Table>

      {pageCount > 1 && (
        <div className="flex items-center justify-end gap-2 text-sm text-slate-600">
          <Button variant="ghost" size="sm" disabled={page === 0} onClick={() => setPage((p) => p - 1)}>Précédent</Button>
          <span>Page {page + 1} / {pageCount}</span>
          <Button variant="ghost" size="sm" disabled={page >= pageCount - 1} onClick={() => setPage((p) => p + 1)}>Suivant</Button>
        </div>
      )}
    </div>
  );
}
