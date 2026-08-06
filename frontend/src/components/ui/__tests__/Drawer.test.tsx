import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Drawer } from '../Drawer';

describe('Drawer', () => {
  it('ne rend rien quand open est false', () => {
    const { container } = render(
      <Drawer open={false} onClose={() => {}} title="Titre">contenu</Drawer>
    );
    expect(container).toBeEmptyDOMElement();
  });

  it('rend le titre, le contenu et le footer quand ouvert', () => {
    render(
      <Drawer open onClose={() => {}} title="Nouveau webhook" footer={<button>Valider</button>}>
        <p>corps du drawer</p>
      </Drawer>
    );
    expect(screen.getByRole('dialog', { name: 'Nouveau webhook' })).toBeInTheDocument();
    expect(screen.getByText('corps du drawer')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Valider' })).toBeInTheDocument();
  });

  it('ferme via le bouton X, la touche Escape et le backdrop', async () => {
    const onClose = vi.fn();
    render(<Drawer open onClose={onClose} title="Titre">contenu</Drawer>);
    await userEvent.click(screen.getByRole('button', { name: 'Fermer' }));
    fireEvent.keyDown(document, { key: 'Escape' });
    fireEvent.mouseDown(screen.getByTestId('drawer-backdrop'));
    expect(onClose).toHaveBeenCalledTimes(3);
  });
});
