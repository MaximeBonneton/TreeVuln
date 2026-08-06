import { useMemo, useState } from 'react';
import { ArrowDown, ArrowUp, Package, Search } from 'lucide-react';
import {
  Badge,
  Input,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeaderCell,
  TableRow,
} from '@/components/ui';
import { criticalityRank, criticalityVariant } from '@/constants/criticality';
import type { Asset } from '@/types';
import type { SbomSummaryItem } from '@/api/sbom';

const PAGE_SIZE = 100;

type SortKey = 'asset_id' | 'name' | 'criticality' | 'components';

interface AssetsTableProps {
  assets: Asset[];
  sbomSummary: Map<string, SbomSummaryItem>;
  onSelect: (assetId: string) => void;
}

/** Table des assets de l'arbre courant : recherche, tri, pagination (spec §3 Assets & SBOM). */
export function AssetsTable({ assets, sbomSummary, onSelect }: AssetsTableProps) {
  const [search, setSearch] = useState('');
  const [sortKey, setSortKey] = useState<SortKey>('asset_id');
  const [desc, setDesc] = useState(false);
  const [page, setPage] = useState(0);

  const sorted = useMemo(() => {
    const componentsOf = (assetId: string) => sbomSummary.get(assetId)?.component_count ?? 0;
    const needle = search.trim().toLowerCase();
    const filtered = needle
      ? assets.filter(
          (a) =>
            a.asset_id.toLowerCase().includes(needle) ||
            (a.name ?? '').toLowerCase().includes(needle)
        )
      : assets;

    const compare = (a: Asset, b: Asset): number => {
      switch (sortKey) {
        case 'name':
          return (a.name ?? '').localeCompare(b.name ?? '');
        case 'criticality':
          return criticalityRank(a.criticality) - criticalityRank(b.criticality);
        case 'components':
          return componentsOf(a.asset_id) - componentsOf(b.asset_id);
        default:
          return a.asset_id.localeCompare(b.asset_id);
      }
    };

    return [...filtered].sort((a, b) => (desc ? -compare(a, b) : compare(a, b)));
  }, [assets, search, sortKey, desc, sbomSummary]);

  const pageCount = Math.max(1, Math.ceil(sorted.length / PAGE_SIZE));
  const current = Math.min(page, pageCount - 1);
  const rows = sorted.slice(current * PAGE_SIZE, current * PAGE_SIZE + PAGE_SIZE);

  // Un premier clic sur une colonne trie du plus « fort » au plus faible pour
  // la criticité et le nombre de composants — l'ordre utile par défaut.
  const toggleSort = (key: SortKey) => {
    if (key === sortKey) {
      setDesc((d) => !d);
    } else {
      setSortKey(key);
      setDesc(key === 'criticality' || key === 'components');
    }
    setPage(0);
  };

  const ariaSortOf = (key: SortKey) =>
    sortKey === key ? (desc ? 'descending' : 'ascending') : 'none';

  const SortButton = ({ label, sortBy }: { label: string; sortBy: SortKey }) => (
    <button
      type="button"
      onClick={() => toggleSort(sortBy)}
      className="inline-flex items-center gap-1 uppercase tracking-wide hover:text-slate-700"
    >
      {label}
      {sortKey === sortBy &&
        (desc ? (
          <ArrowDown size={12} aria-hidden="true" />
        ) : (
          <ArrowUp size={12} aria-hidden="true" />
        ))}
    </button>
  );

  return (
    <div className="space-y-3">
      <div className="relative max-w-sm">
        <Search
          size={14}
          className="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400"
          aria-hidden="true"
        />
        <Input
          aria-label="Rechercher un asset"
          placeholder="Rechercher par identifiant ou nom…"
          value={search}
          onChange={(e) => {
            setSearch(e.target.value);
            setPage(0);
          }}
          className="pl-8"
        />
      </div>

      {rows.length === 0 ? (
        <p className="text-sm text-slate-500">Aucun asset ne correspond à la recherche.</p>
      ) : (
        <>
          <Table>
            <TableHead>
              <TableHeaderCell ariaSort={ariaSortOf('asset_id')}>
                <SortButton label="Identifiant" sortBy="asset_id" />
              </TableHeaderCell>
              <TableHeaderCell ariaSort={ariaSortOf('name')}>
                <SortButton label="Nom" sortBy="name" />
              </TableHeaderCell>
              <TableHeaderCell ariaSort={ariaSortOf('criticality')}>
                <SortButton label="Criticité" sortBy="criticality" />
              </TableHeaderCell>
              <TableHeaderCell ariaSort={ariaSortOf('components')}>
                <SortButton label="SBOM" sortBy="components" />
              </TableHeaderCell>
              <TableHeaderCell>Mis à jour</TableHeaderCell>
              <TableHeaderCell className="text-right">Actions</TableHeaderCell>
            </TableHead>
            <TableBody>
              {rows.map((a) => {
                const sbom = sbomSummary.get(a.asset_id);
                return (
                  <TableRow key={a.id}>
                    <TableCell>
                      <span data-testid="asset-id" className="font-mono text-xs text-slate-900">
                        {a.asset_id}
                      </span>
                    </TableCell>
                    <TableCell>{a.name ?? '—'}</TableCell>
                    <TableCell>
                      <Badge variant={criticalityVariant(a.criticality)}>{a.criticality}</Badge>
                    </TableCell>
                    <TableCell>
                      {sbom ? (
                        <Badge variant="success">
                          {sbom.format} · {sbom.component_count} composants
                        </Badge>
                      ) : (
                        <span className="text-slate-400">—</span>
                      )}
                    </TableCell>
                    <TableCell className="text-xs text-slate-500">
                      {new Date(a.updated_at).toLocaleDateString()}
                    </TableCell>
                    <TableCell className="text-right">
                      <button
                        type="button"
                        aria-label={`Ouvrir le SBOM de ${a.asset_id}`}
                        title="SBOM"
                        onClick={() => onSelect(a.asset_id)}
                        className="rounded-md p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-600"
                      >
                        <Package size={14} />
                      </button>
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>

          {pageCount > 1 && (
            <div className="flex items-center justify-end gap-3 text-xs text-slate-500">
              <span>
                Page {current + 1} / {pageCount}
              </span>
              <button
                type="button"
                aria-label="Page précédente"
                disabled={current === 0}
                onClick={() => setPage(current - 1)}
                className="rounded-md border border-slate-200 px-2 py-1 hover:bg-slate-50 disabled:opacity-40"
              >
                Précédent
              </button>
              <button
                type="button"
                aria-label="Page suivante"
                disabled={current >= pageCount - 1}
                onClick={() => setPage(current + 1)}
                className="rounded-md border border-slate-200 px-2 py-1 hover:bg-slate-50 disabled:opacity-40"
              >
                Suivant
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
