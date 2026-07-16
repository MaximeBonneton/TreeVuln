import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ConditionEditor } from '../ConditionEditor';
import type { NodeCondition } from '@/types';

// Couvre le correctif F-6 : les boutons Simple/Compound ne basculent que
// s'ils changent réellement de mode, et le passage composé -> simple avec
// plusieurs critères demande confirmation avant de perdre des données.

function renderEditor(condition: NodeCondition, onReplace = vi.fn()) {
  render(
    <ConditionEditor
      condition={condition}
      index={0}
      total={1}
      onChange={vi.fn()}
      onReplace={onReplace}
      onRemove={vi.fn()}
      onMove={vi.fn()}
    />
  );
  return { onReplace };
}

const simple: NodeCondition = { label: 'A', operator: 'eq', value: 'x' };

describe('ConditionEditor mode toggle (F-6)', () => {
  it('clicking Simple on an already-simple condition does nothing', async () => {
    const { onReplace } = renderEditor(simple);
    await userEvent.click(screen.getByRole('button', { name: 'Simple' }));
    expect(onReplace).not.toHaveBeenCalled();
  });

  it('clicking Compound on a simple condition converts it', async () => {
    const { onReplace } = renderEditor(simple);
    await userEvent.click(screen.getByRole('button', { name: 'Compound' }));
    expect(onReplace).toHaveBeenCalledTimes(1);
    const replacement = onReplace.mock.calls[0][1] as NodeCondition;
    expect(replacement.logic).toBe('AND');
    expect(replacement.criteria).toHaveLength(1);
  });

  it('compound -> simple with one criterion converts without confirmation', async () => {
    const compoundOne: NodeCondition = {
      label: 'A',
      logic: 'AND',
      criteria: [{ operator: 'eq', value: 'x' }],
    };
    const { onReplace } = renderEditor(compoundOne);
    await userEvent.click(screen.getByRole('button', { name: 'Simple' }));
    expect(onReplace).toHaveBeenCalledTimes(1);
  });

  it('compound -> simple with several criteria asks for confirmation first', async () => {
    const compoundMany: NodeCondition = {
      label: 'A',
      logic: 'AND',
      criteria: [
        { operator: 'eq', value: 'x' },
        { operator: 'eq', value: 'y' },
      ],
    };
    const { onReplace } = renderEditor(compoundMany);

    await userEvent.click(screen.getByRole('button', { name: 'Simple' }));
    // Pas de conversion tant que l'utilisateur n'a pas confirmé
    expect(onReplace).not.toHaveBeenCalled();
    expect(screen.getByText('Switch to simple mode')).toBeInTheDocument();

    await userEvent.click(screen.getByRole('button', { name: 'Confirm' }));
    expect(onReplace).toHaveBeenCalledTimes(1);
  });
});
