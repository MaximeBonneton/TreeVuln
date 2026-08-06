import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Dropzone } from '../Dropzone';

function makeFile(name: string) {
  return new File(['cve_id\nCVE-2024-0001'], name, { type: 'text/csv' });
}

describe('Dropzone', () => {
  it('affiche le hint et sélectionne un fichier via l\'input', async () => {
    const onFileSelect = vi.fn();
    render(<Dropzone accept=".csv" file={null} onFileSelect={onFileSelect} hint="CSV avec en-têtes" />);
    expect(screen.getByText('CSV avec en-têtes')).toBeInTheDocument();
    const input = screen.getByTestId('dropzone-input') as HTMLInputElement;
    await userEvent.upload(input, makeFile('vulns.csv'));
    expect(onFileSelect).toHaveBeenCalledWith(expect.objectContaining({ name: 'vulns.csv' }));
  });

  it('accepte un drop avec la bonne extension et rejette les autres', () => {
    const onFileSelect = vi.fn();
    render(<Dropzone accept=".csv" file={null} onFileSelect={onFileSelect} />);
    const zone = screen.getByRole('button', { name: /Déposer un fichier/ });
    fireEvent.drop(zone, { dataTransfer: { files: [makeFile('bad.txt')] } });
    expect(onFileSelect).not.toHaveBeenCalled();
    fireEvent.drop(zone, { dataTransfer: { files: [makeFile('ok.csv')] } });
    expect(onFileSelect).toHaveBeenCalledWith(expect.objectContaining({ name: 'ok.csv' }));
  });

  it('affiche le fichier sélectionné', () => {
    render(<Dropzone accept=".csv" file={makeFile('vulns.csv')} onFileSelect={() => {}} />);
    expect(screen.getByText('vulns.csv')).toBeInTheDocument();
  });
});
