import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { Table, TableHead, TableHeaderCell, TableBody, TableRow, TableCell } from '../Table';

describe('Table', () => {
  it('renders a complete accessible table', () => {
    render(
      <Table>
        <TableHead>
          <TableHeaderCell>Asset</TableHeaderCell>
          <TableHeaderCell>Criticality</TableHeaderCell>
        </TableHead>
        <TableBody>
          <TableRow>
            <TableCell>srv-prod-001</TableCell>
            <TableCell>Critical</TableCell>
          </TableRow>
        </TableBody>
      </Table>
    );
    expect(screen.getByRole('table')).toBeInTheDocument();
    expect(screen.getAllByRole('columnheader')).toHaveLength(2);
    expect(screen.getByRole('cell', { name: 'srv-prod-001' })).toBeInTheDocument();
  });

  it('wraps the table in a scroll container', () => {
    const { container } = render(
      <Table>
        <TableBody>
          <TableRow><TableCell>x</TableCell></TableRow>
        </TableBody>
      </Table>
    );
    expect((container.firstChild as HTMLElement).className).toContain('overflow-x-auto');
  });

  it('expose aria-sort sur une colonne triable', () => {
    render(
      <Table>
        <TableHead>
          <TableHeaderCell ariaSort="ascending">Criticité</TableHeaderCell>
        </TableHead>
      </Table>
    );
    expect(screen.getByRole('columnheader')).toHaveAttribute('aria-sort', 'ascending');
  });
});
