import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Tooltip } from '../Tooltip';

describe('Tooltip', () => {
  it('is hidden by default', () => {
    render(<Tooltip content="Regenerate API key"><button>↻</button></Tooltip>);
    expect(screen.queryByRole('tooltip')).not.toBeInTheDocument();
  });

  it('appears on hover and disappears on unhover', async () => {
    render(<Tooltip content="Regenerate API key"><button>↻</button></Tooltip>);
    await userEvent.hover(screen.getByRole('button'));
    expect(screen.getByRole('tooltip')).toHaveTextContent('Regenerate API key');
    await userEvent.unhover(screen.getByRole('button'));
    expect(screen.queryByRole('tooltip')).not.toBeInTheDocument();
  });

  it('appears on keyboard focus', async () => {
    render(<Tooltip content="Regenerate API key"><button>↻</button></Tooltip>);
    await userEvent.tab();
    expect(screen.getByRole('tooltip')).toBeInTheDocument();
  });
});
