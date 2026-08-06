// Composants de présentation pour tables de données.
// Usage : <Table><TableHead><TableHeaderCell>…</TableHead><TableBody><TableRow><TableCell>…</Table>
interface SectionProps {
  children: React.ReactNode;
  className?: string;
}

export function Table({ children, className = '' }: SectionProps) {
  return (
    <div className={`overflow-x-auto rounded-card border border-slate-200 bg-white shadow-sm ${className}`}>
      <table className="w-full text-sm">{children}</table>
    </div>
  );
}

export function TableHead({ children, className = '' }: SectionProps) {
  return (
    <thead className={`border-b border-slate-200 bg-slate-50 ${className}`}>
      <tr>{children}</tr>
    </thead>
  );
}

export function TableHeaderCell({
  children,
  className = '',
  ariaSort,
}: SectionProps & { ariaSort?: 'none' | 'ascending' | 'descending' }) {
  return (
    <th
      aria-sort={ariaSort}
      className={`px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500 ${className}`}
    >
      {children}
    </th>
  );
}

export function TableBody({ children, className = '' }: SectionProps) {
  return <tbody className={`divide-y divide-slate-100 ${className}`}>{children}</tbody>;
}

export function TableRow({ children, className = '' }: SectionProps) {
  return <tr className={`hover:bg-slate-50 ${className}`}>{children}</tr>;
}

export function TableCell({ children, className = '' }: SectionProps) {
  return <td className={`px-4 py-3 text-slate-700 ${className}`}>{children}</td>;
}
