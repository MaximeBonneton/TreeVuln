import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Tabs } from '../Tabs';

const tabs = [
  { id: 'single', label: 'Quick test' },
  { id: 'batch', label: 'Batch campaign' },
];

describe('Tabs', () => {
  it('renders one tab per entry', () => {
    render(<Tabs tabs={tabs} active="single" onChange={vi.fn()} />);
    expect(screen.getAllByRole('tab')).toHaveLength(2);
  });

  it('marks the active tab with aria-selected', () => {
    render(<Tabs tabs={tabs} active="batch" onChange={vi.fn()} />);
    expect(screen.getByRole('tab', { name: 'Batch campaign' })).toHaveAttribute('aria-selected', 'true');
    expect(screen.getByRole('tab', { name: 'Quick test' })).toHaveAttribute('aria-selected', 'false');
  });

  it('calls onChange with the tab id on click', async () => {
    const onChange = vi.fn();
    render(<Tabs tabs={tabs} active="single" onChange={onChange} />);
    await userEvent.click(screen.getByRole('tab', { name: 'Batch campaign' }));
    expect(onChange).toHaveBeenCalledWith('batch');
  });
});
