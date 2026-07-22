import { describe, expect, it, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { EnisaPanel } from '../EnisaPanel';

vi.mock('@/api/enisa', () => ({
  listEnisaEvents: vi.fn().mockResolvedValue({
    events: [
      {
        id: 1, tree_id: 1, cve_id: 'CVE-2026-0001', status: 'candidate',
        detected_at: '2026-07-22T10:00:00Z', last_detected_at: '2026-07-22T10:00:00Z',
        confirmed_at: null, redetection_count: 0, milestones: {},
      },
      {
        id: 2, tree_id: 1, cve_id: 'CVE-2026-0002', status: 'confirmed',
        detected_at: '2026-07-21T10:00:00Z', last_detected_at: '2026-07-22T09:00:00Z',
        confirmed_at: '2026-07-21T12:00:00Z', redetection_count: 0,
        milestones: {
          early_warning: {
            due_at: '2026-07-22T12:00:00Z', remaining_seconds: 0,
            overdue: true, submitted_at: null,
          },
        },
      },
    ],
    total: 2,
  }),
  getEnisaSummary: vi.fn().mockResolvedValue({
    candidates: 1, confirmed: 1, overdue_milestones: 1,
  }),
}));

describe('EnisaPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('liste les événements avec CVE et statut', async () => {
    render(<EnisaPanel open onClose={vi.fn()} treeId={1} />);
    await waitFor(() => {
      expect(screen.getByText('CVE-2026-0001')).toBeInTheDocument();
      expect(screen.getByText('CVE-2026-0002')).toBeInTheDocument();
    });
  });

  it('signale un jalon en retard', async () => {
    render(<EnisaPanel open onClose={vi.fn()} treeId={1} />);
    await waitFor(() => {
      expect(screen.getByText(/en retard|overdue/i)).toBeInTheDocument();
    });
  });

  it('fermé -> ne rend rien', () => {
    const { container } = render(<EnisaPanel open={false} onClose={vi.fn()} treeId={1} />);
    expect(container.firstChild).toBeNull();
  });
});
